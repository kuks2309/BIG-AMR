# 2026-08-14 — `line_follow` SIL 폐루프 신설 (가상 라인 센서 + sil 런치)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: SIL(Software In the Loop) · ASAN(Address Sanitizer) · TF(Transform) ·
> mux(multiplexer) · PD(Proportional-Derivative)

- 사용자 지시: 2026-08-14 "SIL부터"
- 인벤토리: `docs/code_review/sim-line-sensor/2026-08-14.md`(루트 정본) + 패키지 병기
- 신설: `src/Sim/line_sim_sensor/` · `trnav_2ws_action_server/launch/sil_line_follow.launch.py`

## 왜 필요했나 — 종전 시험은 폐루프가 아니었다

`line_follow` 를 만들 때 돌린 것은 SIL 이 아니라 **스모크**였다. 합성 `/line/error` 를
고정값으로 주입했으므로 「오차를 넣으면 조향 부호가 맞게 나오는가」까지만 확인됐고,
**「그 조향이 오차를 줄이는가」는 한 번도 확인되지 않았다.** 다른 액션 10개는 모두
`sil_*.launch.py` 가 있는데 `line_follow` 만 없었다.

라인 추종은 영상 폐루프라, 로봇이 조향한 결과가 다음 측정에 되먹임돼야 수렴을 볼 수 있다.
기존 SIL 플랜트(`translate_sim_odom`)는 wheel 지령 → 자세·IMU·조향 피드백까지 만들어 주지만
**라인 오차를 만들어 주지는 않는다.** 그 한 조각이 `line_sim_sensor` 다.

## 무엇을 만들었나

| 파일 | 상태 | 내용 |
| --- | --- | --- |
| `line_sim_sensor/line_geometry.py` (104줄) | 신규 | 맵 라인 + 자세 → 카메라 오차 역산 (ROS 무의존) |
| `line_sim_sensor/sensor_node.py` (126줄) | 신규 | TF map→base_link 구독 → `/line/error` 발행 |
| `config/line_sim_params.yaml` | 신규 | 라인 배치·화각·발행률 |
| `test/test_line_geometry.py` (16건) | 신규 | 부호 규약·구간·후진·정렬 |
| `sil_line_follow.launch.py` | 신규 | 폐루프 기동 — 플랜트·mux(13)·supervisor·pose 어댑터·가상 센서·안전 더미·액션 |

핵심 결정 3가지:

1. **실제 인식 노드와 같은 메시지 타입**(`ai_msgs/LineError`)을 쓴다. 제어기는 이 값이
   모사인지 실측인지 구분하지 못해야 SIL 이 의미를 갖는다.
2. **발행률을 실측에 맞춘다** — 25 Hz(실카메라 24.4 Hz). 제어는 50 Hz 라 측정율이 절반인
   조건이 그대로 재현돼야 미분항 처리(새 측정에서만 갱신)가 시험된다.
3. **인식 성능은 모사하지 않는다** — 검출 실패·오검출·신뢰도 변동·렌즈 왜곡이 없다.
   기하만 맞다. 이 SIL 은 제어 수렴성 도구이지 인식 시험이 아니다(문서에 명시).

기본 라인은 로봇 왼쪽 10 cm 에 나란한 10 m 직선이다 — 오차 0 에서 출발하면 수렴을 볼 수
없으므로 초기 횡오차를 만들고, 라인 끝에서 소실 → coast → abort(−9) 경로까지 이어진다.

## 기동 크래시 — 원인 확정(코드 결함 아님)

SIL 첫 기동에서 **`amr_line_follow_node` 만 즉시 힙 손상으로 죽었다**(`malloc.c:2617`
assertion, SIGABRT). 좁힌 근거와 결론:

| 관측 | 함의 |
| --- | --- |
| 백트레이스가 `LocalizationMonitor` 생성자 | 손상은 그 **앞**에서 발생(다음 malloc 에서 터짐) |
| `yaw_control`·`spin`·`turn` 은 정상 기동 | 공용 코드(베이스·core) 자체 문제 아님 |
| ASAN 빌드 60 s 무크래시·위반 보고 0 | 코드의 경계 위반이 아님 |
| **`build/`·`install/` 삭제 후 클린 재빌드 → 재현 안 됨** | **오브젝트 파일 불일치 확정** |

다른 세션이 `trnav_2ws_core` 에 `velocity_ramp.hpp` 를 추가했고, 그 변경 **이전 헤더로
컴파일된 객체**가 증분 빌드에 섞였다. ASAN 빌드가 크래시를 없앤 것도 전 TU 재컴파일이기
때문이지 계측 효과가 아니었다.

⚠ 공유 워킹트리에서 타 세션이 core 헤더를 바꾸면 증분 빌드가 조용히 깨질 수 있다.
`trnav_2ws_core` 계열이 바뀐 뒤에는 의존 패키지를 **클린 재빌드**해야 한다.

## 라인 배치 기준계 — 시작 자세 기준으로 정정

첫 폐루프 실행에서 `detected=false` 가 계속 나왔다. 원인은 **플랜트 초기 자세가 맵 원점이
아니라 시나리오 웨이포인트(4.952, −2.327)** 이기 때문이다(`sim_params.yaml:21-22`).
라인을 맵 절대좌표에 놓으니 2.4 m 밖이라 미검출이 정상 동작이었다.

`line_frame` 파라미터(기본 `"start"`)와 순수 함수 `anchor_line` 을 추가해 **로봇 시작 자세
기준**으로 라인을 놓는다 — 「출발 지점 왼쪽 10 cm 에 나란한 10 m 직선」이라는 서술이 플랜트
설정과 무관하게 성립한다. `"map"` 으로 두면 절대좌표 해석을 유지한다.

시험 6건을 더했다. 그중 하나에서 **내 기댓값이 틀렸다** — 라인을 왼쪽에 놓고 `offset > 0` 을
단언했는데 규약상 왼쪽은 음수다. 코드가 옳고 단언이 틀려 단언을 고쳤다.

## 검증 — 폐루프 수렴 확인

| 항목 | 결과 |
| --- | --- |
| `line_sim_sensor` 빌드 | 오류 0 |
| 기하 단위테스트 | **22 passed** (부호 규약·구간·후진·정렬·앵커링) |
| SIL 스택 기동 | 7개 노드 정상(액션 노드 포함) |
| mux 소스 | `id=13 name=line_follow` 등록·활성 |
| 라인 확정 | 시작 자세 (4.952, −2.327, 0.0°) → 맵 (4.952, −2.227) heading 0.0° |
| **폐루프 주행** | **status 0** · 거리 **8.004 m** · 평균 \|offset\| **0.0087** · 41.0 s · 오차 표본 1,035건 전부 검출 |
| **수렴 궤적** | −0.1667 → −0.0340(4 s) → −0.0039(7.6 s) → −0.0000(17.9 s 이후 유지) |
| 진동 | **부호 반전 0회** — 오버슛 없이 단조 수렴 |

**이것이 종전에 확인되지 않았던 것이다.** 스모크는 「오차를 넣으면 조향 부호가 맞게 나오는가」
까지였고, 「그 조향이 오차를 줄이는가」는 여기서 처음 관측됐다.

## 미검증 (실기 전 남은 것)

- **곡선·급커브 라인** — 현재 시험은 직선뿐이다. `line_heading_deg` 로 각을 준 라인과 곡선
  지원은 별건
- **동특성** — 즉응 플랜트라 조향 지연이 없어 `TransientGuard` 의 `gate_blocked` 와
  `status −8` 경로가 발화하지 않았다. `steer_rate:=57.1 drive_decel:=0.0833` 재실행 필요
- **후진(`reverse`) SIL** 미실행
- CCG 리뷰의 단독 지적 치명 2건 미수정(특히 인식 런치가 `line_seg_params.yaml` 미적재)

최종 verdict 는 저자가 찍지 않는다 (`coding.md:89` never-self-approve).
