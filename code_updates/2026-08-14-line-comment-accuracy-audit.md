# 2026-08-14 — 라인 추종 스택 주석 정확성 감사·정정 (인식 + 제어)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: QoS(Quality of Service) · IK(Inverse Kinematics) · QD(Quad Diagonal)

- 사용자 지시: 2026-08-14 "주석 다시 한번 확인할까? 정확히 되어있는지?"
- 대상: `src/AI/line_vision/**` · `src/Control/Motion_Control/2WS/trnav_2ws_action_server/**/line_follow/**`
- 방법: `Tools/comment_check/check_comments.py`(기계 4종 + `history` 옵트인) 전수 + 도구가
  **미검증이라고 선언한 서술·부호 규약**을 사람 판정으로 대조

## 무엇을 고쳤나 — 5건

| # | 파일 | 잘못된 주석 | 정정 |
| --- | --- | --- | --- |
| 1 | `line_follow.launch.py:9` | `line_vision/line_seg.launch.py` — 해석 불가한 패키지 상대경로 | `src/AI/line_vision/launch/line_seg.launch.py` |
| 2 | `line_seg.launch.py:11` | `yolo_detector/detect.launch.py` — 동일 | `src/AI/yolo_detector/launch/detect.launch.py` |
| 3 | `centerline.py:3-4` | 타 저장소 경로를 저장소 내부처럼 인용 | 저장소명 명시 + `comment-check: ignore` (한 줄로 합침 — 마커는 **그 줄만** 억제한다) |
| 4 | `line_follow_params.yaml` | 「기하가 빠지면 QD 대각 기본값으로 풀린다(2026-08-08 실증)」 | **거짓** — 베이스 기본값은 이미 인라인 값이다. 왜 여기 두는지(구동점 명시)로 교체 |
| 5 | `line_follow_action_server.cpp` `validateGoal` | 「둘 다 0 이면 cancel 외에는 멈출 조건이 없다」 | **거짓** — 전역 시한이 `-3` 으로 끊는다. 「성공으로 끝날 조건이 없다」로 교체 |

부수 정정 2건: `max_timeout_sec_` 를 「yaw_control 과 같은 기본값」 묶음에서 분리(60 vs 120,
근거 명기) · `platform: "QD_DIAGONAL"` 이 배치 기하가 아니라 **바퀴 배열 순서** 값임을 명시.

## 왜 4·5 가 중요한가

둘 다 **기계 검사를 통과한** 주석이다. 인용 좌표도 수치도 아니고 서술이라 재도출할 문법 단서가
없다. 검사기 README 가 스스로 「서술·해석·부호 규약·동작 설명은 검증되지 않는다」고 적어 둔
바로 그 구간이며, 실제로 이번에 나온 두 건이 그 구간에 있었다.

4 는 **없는 위험을 경고**한다 — 읽는 사람이 실재하지 않는 함정을 피하려 불필요한 조치를 하게
된다. 5 는 **있는 안전장치를 없다고** 말한다. 방향이 반대인 두 형태의 거짓이다.

## 정확함을 재확인한 것 (변경 없음)

- **부호 규약**: `ω = 2·vx·tanδ/L` → 전진 `δ<0` / 후진 `δ>0`. 코드의 `-dir *(…)` 와 일치하고
  스모크 실측(`−3.46°` / `+3.46°`)이 뒷받침한다
- **QoS**: 「발행 RELIABLE depth 10 ↔ 같은 프로파일로 구독」 — `line_seg_node` 의
  `create_publisher(..., 10)` 기본값과 서버의 `QoS(10).reliable()` 대조 확인
- **외부 인용**: `kuks2309/Welding_Robot_Ros2_ws` 원본을 실제 조회 —
  `fit_seam_centerline`(`:15`) · `cv::fitLine(DIST_L2, 0, 0.01, 0.01)`(`:69`) ·
  `kEps = 1e-6`(`:12`) 전부 주석대로다
- `0.44 rad ≈ 25°` · 경로장 적산 · coast/두절 분기 · `motion_source_id_{13}` 예약 회피

## 검증

| 항목 | 결과 |
| --- | --- |
| `check_comments.py` 기본 4종 | 16파일 **불일치 0** (정정 전 3건) |
| `check_comments.py --checks history` | 13파일 **불일치 0** — 이력형 주석 없음 |
| 표 앵커 재동기 | 주석 증감으로 줄이 밀린 인벤토리 2건(`ai-line-vision`·`line-follow`)의 위치 컬럼을 실제 줄로 맞춤(루트 정본 + 패키지 병기 양쪽) |
| 재빌드·회귀 | `line_vision`·`trnav_2ws_action_server` 오류 0 · gtest **19** · pytest **17** 전부 통과 |

함수·전역변수의 추가·삭제·시그니처 변경은 **없다**(주석 전용 수정). 표는 위치 컬럼만 갱신했다.
