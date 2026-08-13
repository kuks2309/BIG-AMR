# 2026-08-14 — `line_follow` 2WS 액션 서버 신설 (영상 라인 추종, mux source 13)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: 2WS(Two Wheel Steering) · 2WD(Two Wheel Drive) · IK(Inverse Kinematics) ·
> PD(Proportional-Derivative) · FSM(Finite State Machine) · mux(multiplexer)

- 사용자 지시: 2026-08-14 "커밋 푸쉬 머지후에 line following motion 을 만들어주세요"
- ADR: `docs/adr/2026-08-14-line-follow-2ws-action.md`
- 선행(인식 계층): `docs/adr/2026-08-13-line-following-ai-port.md` — `/line/error` 생산자
- 인벤토리: `docs/code_review/line-follow/2026-08-14.md`(루트 정본) +
  `src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/code_review/line-follow/2026-08-14.md`
- 루트 집계 인덱스: `docs/sw_structure/function_table.md` 에 모듈 1행 추가

## 무엇을 만들었나

| 파일 | 상태 | 내용 |
| --- | --- | --- |
| `trnav_2ws_interfaces/action/AMRMotionLineFollow.action` | 신규 | Goal 8 / Result 4 / Feedback 8 필드 |
| `trnav_2ws_interfaces/CMakeLists.txt` | 수정 (1줄) | 액션 등재 |
| `…/include/…/line_follow/line_follow_core.hpp` | 신규 (142줄) | 제어 수학·소실 FSM (ROS 무의존) |
| `…/include/…/line_follow/line_follow_action_server.hpp` | 신규 (90줄) | 서버 클래스 선언 |
| `…/src/line_follow/line_follow_action_server.cpp` | 신규 (629줄) | 서버 구현 |
| `…/src/line_follow/line_follow_main.cpp` | 신규 (16줄) | 노드 진입점 `amr_line_follow_node` |
| `…/config/line_follow_params.yaml` | 신규 (58줄) | 기하·게인·임계 |
| `…/launch/line_follow.launch.py` | 신규 (29줄) | `trnav_line_follow_node` 기동 |
| `…/test/line_follow_core_test.cpp` | 신규 (179줄) | gtest 19건 |
| `trnav_2ws_action_server/CMakeLists.txt`·`package.xml` | 수정 | 실행파일·`ai_msgs` 의존·`BUILD_TESTING` gtest |
| `trnav_motion_mux/config/trnav_motion_mux.yaml` | 수정 | `source_13` 블록 + `source_ids` 등재 |

## 왜 원본 제어기를 이식하지 않았나

원본(`kuks2309/TR_3D_Nav_ros2_ws`)의 라인 추종 액션은 **2WD 차동** 기체용이다. 각속도 ω 를
`geometry_msgs/Twist` 로 직접 내고 `cmd_vel_mux` 를 탄다. 이 기체는 **인라인 듀얼스티어 2WS**
이고 mux 가 `trnav_msgs/WheelSetArray`(바퀴별 속도·조향각)를 받는다. 액션 소속도 다르다 —
원본은 단일 프로세스의 8번째 서버, 여기는 액션마다 독립 노드다.

그래서 **가져온 것은 제어 법칙과 소실 FSM 뿐**이고 서버 골격은 `yaw_control` 패턴으로 새로 썼다.
PD 는 ω 공간에서 **조향각 δ 공간**으로 옮겼다(`ω = vx·(tanδ_f − tanδ_r)/L` 이 ω 를 만든다).

부호 유도: `offset` + = 라인이 진행방향 기준 오른쪽 → 진행방향을 오른쪽으로 → 세계좌표 `ω < 0`.
counter-steer 에서 `ω = 2·vx·tanδ_f/L` 이므로 전진(`vx>0`)은 `δ_f < 0`, 후진(`vx<0`)은 `δ_f > 0`.
그래서 조향식에 `−sign(vx)` 가 붙는다 — `yaw_control` 이 후진에서 err 부호를 뒤집는 것과 같은 규약.

## 설계 결정 3가지

1. **방향쌍 슬롯을 만들지 않았다.** `translate`·`turn`·`yaw_control`·`mpc` 는 전진·후진이
   별도 액션이지만, 라인 추종은 `reverse` 를 goal 필드로 받아 한 액션이 둘을 처리한다.
   방향 차이가 `vx` 부호 하나뿐이라 코드를 가를 이유가 없다 — `turn`/`turn_reverse` 가
   「`vx` 부호 3곳을 빼면 같은 코드」라는 중복 비용을 이미 등재해 두었다.
2. **카메라 정합은 검사만 한다.** 액션이 인식 노드의 `direction` 파라미터를 원격 설정하지
   않는다. 대신 수신한 `LineError.camera` 가 진행 방향과 다르면 abort(−11). 뒤를 보며 앞으로
   달리면 조향 부호가 반대라 라인에서 멀어지므로, 조용히 달리느니 기동 실패가 낫다.
3. **게인은 goal 이 아니라 yaml.** `yaw_control` 은 goal 필드로 받지만 라인 추종 게인은 주행
   사이 반복 조정이 전제다. `reloadTuning()` 이 goal 마다 재적재해 `ros2 param set` 으로
   재기동 없이 바꾼다.

## 스모크가 찾아낸 결함 1건 (수정 완료)

goal 사이에 남은 `line_snapshot_` 때문에 **라인 소실 시나리오가 시작 즉시 −11 로 죽었다**
(t=0.0 s). 직전 goal(카메라 불일치 시험)이 남긴 `cam_r` 이름이 캐시에 살아 있었고, 새 goal 의
첫 주기가 그것을 읽었다. `resetLineSnapshot()` 을 `execute()` 진입부에 추가해 이번 goal 동안
도착한 데이터만 쓰게 했다. 재실행 후 −9(t=2.5 s = 소실 1.5 s + coast 1.0 s)로 정상 종료.

## 검증

| 항목 | 결과 |
| --- | --- |
| colcon 빌드 | 2패키지 오류 0, 신규 파일 경고 0 |
| 단위 테스트 | **19 tests, 0 failures** |
| [A] 정상 추종 | status **0**, wheel_cmd 112건, 전륜조향 −3.46~0.00°, 속도 0~+0.087 m/s |
| 조향 부호·크기 | offset +0.05 × kp 1.2 → 3.44° 기대, 실측 **−3.46°** |
| [B] 카메라 불일치 | 전진 goal + `cam_r` → status **−11** |
| [C] 라인 소실 | coast 1 s 초과 → status **−9**, t=2.5 s |
| [D] 후진 추종 | `reverse=true` + `cam_r` → status **0**, 조향 **+0.00~+3.46°**·속도 **−0.087 m/s** |

**미검증**: 실기 주행. 합성 `/line/error` 입력이며 조향축·구동축이 붙지 않았다. 조향 피드백
(`wheel_motor_state`)이 없어 `TransientGuard` gate_blocked 경로와 status −8 은 발화하지 않았고,
측위(`/robot_pose`)가 없어 거리 종료(`max_distance`)와 −4/−5/−6 경로도 미검증이다.
게인은 원본(2WD 차동) 값이라 이 기체에서 재조정이 필요하다.

최종 verdict 는 저자가 찍지 않는다 (`coding.md:89` never-self-approve).
