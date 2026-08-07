# Seer 원본의 경로 제어 방법 — 조사 (2026-08-08)

> 목적: 우리 2WS 스택으로 경로 제어를 대체하기 전에, **Seer 가 같은 기체를 어떻게 몰고 있는지**
> 를 확정한다. 추정하지 않고 ① 벤더 원문 ② 실기 조회 ③ 맵 원본 세 곳만 근거로 쓴다.
>
> 조사 대상 기체: `model Foil_A082` · `vehicle_id Foil_A082` (실기 조회 2026-08-08 07:53)
> 조회 경로: 상태 포트 **19204 읽기 전용** (`csm.seer_client`, `_ALLOWED_PORTS` 강제)

## 1. 세 층으로 나뉜다

Seer 의 「경로 제어」는 한 덩어리가 아니라 세 층이다.

| 층 | 무엇 | 어디에 정의되나 |
| --- | --- | --- |
| ① **작업 지시** | 「LM1 로 가라」 | TASK API 19206 (`3050`·`3051`·`3052`) |
| ② **경로 기하** | 어느 선을 따라가나 | 맵(`.smap`)의 `advancedCurveList` |
| ③ **추종 제어** | 그 선을 어떻게 따라가나 | `MoveFactory` 플러그인 파라미터 |

우리 2WS 스택이 대체하려는 것은 **②③** 이다(①은 상위 미션 계층).

## 2. ① 작업 지시 API — ⚠ 저장소 요약 문서에 번호 오류가 있었다

벤더 원문 `References/Seer-Driver/github_sdk/robotkit-netprotocol-l-1.2.1.txt:2851-2859` (v1.2.1):

| API | 이름 | 설명 |
| --- | --- | --- |
| 3050 | `robot_task_gopoint_req` | **자유 내비게이션** — 좌표 또는 사이트로 스스로 경로 계획 |
| 3051 | `robot_task_gotarget_req` | **고정 경로 내비게이션** — 맵에 등록된 경로를 따라간다 |
| 3052 | `robot_task_patrol_req` | 순찰(경로 목록 반복) |
| **3055** | `robot_task_translate_req` | **평동** — 고정 속도로 직선 고정 거리 |
| **3056** | `robot_task_turn_req` | **전동** — 고정 각속도로 고정 각도 |

> ❌ **정정** — 우리 요약 문서 `References/Seer-Driver/robokit_tcp_api.md:146-147` 은
> `3052 = translate`, `3053 = turn` 으로 적고 있었다. **둘 다 틀렸다.**
> 실제로 `3052` 는 **순찰**이고 `3053` 은 정의 자체가 없다.
> **`3052` 를 「평동」인 줄 알고 보내면 순찰이 시작된다** — 위험한 오기라 원문 대조로 정정했다.

### 3055/3056 의 결정적 성질 — **오도메트리 개루프다**

두 원시 기동 모두 `mode` 필드를 갖는다(원문 `:3192-3246`, `:3248-3300`):

```
mode 0 = 里程모드(오도메트리 기반)   ← 기본값
mode 1 = 自定位모드(자기측위 기반)   ← 원문: "目前不可用"(현재 사용 불가)
```

원문이 덧붙인 한계:
- 里程모드는 **정밀 측위가 필요 없으나 거리·각도가 커질수록 오차가 커진다**
- 3055(평동)와 3056(전동)은 **동시 수행 불가**

⇒ **Seer 의 translate/turn 원시 기동은 측위 폐루프가 아니다.** 측위 기반 모드는 벤더가
「현재 사용 불가」라고 명시한다. 측위 폐루프는 ①의 `3050`/`3051`(내비게이션) 경로에만 있다.

## 3. ② 경로 기하 — 맵이 곧 경로다

현재 맵 `260709_test`(md5 `a20cbe5cb35fe90bde5685174220ffd5`, 2026-08-08 다운로드·검증)의
`advancedCurveList` 는 **직선 6개**뿐이다.

```
LM1(−15.927, 2.412) ── LM2(−15.927, 15.572) ── LM3(−11.712, 15.572)
   │
LM4(−11.988, 2.412)
```

| 경로 | 속성 |
| --- | --- |
| LM1↔LM2 · LM2↔LM3 | `direction 0` · `movestyle 0` · `holdDir 0` |
| LM1↔LM4 | `direction 0` · `movestyle 0` (holdDir 없음 — Seer 는 0 인 필드를 생략한다) |

즉 **경로 자체는 순수 기하(선분) + 3개 속성**이고, 속도·가속·추종 게인은 경로에 없다.
벤더 원문도 그렇게 안내한다 — `3050`/`3051` 의 `max_speed` 등에 대해
**「이 필드들은 권장하지 않는다. 지도의 경로·구역 속성이나 로봇 파라미터로 제어하는 것이 낫다」**
(`:3019-3040`).

⚠ `.smap` 은 `StraightPath` 외에 곡선 클래스도 가질 수 있으나 **이 맵에는 직선뿐**이다.
곡선 경로의 속성 집합은 이번 조사로 확인하지 못했다.

## 4. ③ 추종 제어 — **LQR** 이다

실기 조회 `1400 {"plugin":"MoveFactory"}` 결과 — **파라미터 304개**, 그중 **42개가
기본값과 다르다**(이 기체 튜닝). 전체 덤프를 근거로 보존했다:
`docs/seer/2026-08-08-movefactory-params.json`


```
LQRMode   기본 False → **True**      "Use lqr mode to follow"
```

**이 기체는 LQR(Linear Quadratic Regulator) 모드로 경로를 추종한다.** 기본값에서 켜진 값이므로
누군가 이 기체에 맞춰 **의도적으로 바꾼 설정**이다.

### 차대별 LQR/PID 파라미터가 따로 있다

| 접두 | 대상 차대 | 파라미터 |
| --- | --- | --- |
| `S_` | 単舵轮(조향륜 1개) | `S_maxQ 10.0` — "steering wheel vehicle LQR 의 Q" |
| **`BiSteer_`** | **双舵轮(조향륜 2개) = 우리 기체 구성** | `BiSteer_maxQx 1.0` — LQR 의 x 가중 · `vKp 1.0`/`vKd 0.1` · `wKp 1.0`/`wKd 0.1` |
| `Omni_` | 전방향 | `Omni_maxQx/maxQy/maxQt` 각 1.0 |
| `DualDiff_` | 2륜 차동 모듈 2개 | `steerKp1/2 10.0` · `steerKd1/2 1.0` · `MinSteerAngle1/2 0.5°` |

즉 구조는 **LQR(경로 추종) + 속도/각속도 PID(내부 루프)** 다.

⚠ **미확인** — 이 기체에 실제로 어느 차대 계열이 활성인지 직접 알려주는 API 를 찾지 못했다.
`BiSteer` 로 보는 근거는 **본 저장소가 별도로 확정한 기하**(inline dual-steer, 조향 2 + 구동 2)
이지 Seer 가 그렇게 보고한 것이 아니다. 차대 선택은 `model_md5`
(`b3a954cb524a605dea279d53ecd10528`)가 가리키는 모델 파일 안에 있을 것으로 보이나 조회하지 않았다.

### 이 기체에서 기본값과 다르게 조정된 값 (발췌)

| 파라미터 | 기본 → 현재 | 뜻 |
| --- | --- | --- |
| `LQRMode` | False → **True** | LQR 추종 사용 |
| `SteerSpeed` | 1.0 → **180.0 °/s** | 조향 속도 |
| `MaxSpeed` | 0.5 → **1.0 m/s** | 최대 속도 |
| `MaxAcc` / `MaxDec` | 0.5 / 0.15 → **1.0 / 1.0 m/s²** | 가·감속 |
| `MaxRot` | 60 → **30 °/s** | 최대 회전 속도(**낮췄다**) |
| `MaxRotAcc` / `MaxRotDec` | 30 → **120 / 90 °/s²** | 회전 가·감속 |
| `SpinKp/Ki/Kd` | 0.6 / 0.01 / 1.0 → **1.0 / 0.0 / 10.0** | 제자리 회전 PID (I 항 제거, D 10배) |
| `MotionPlanAheadDist` | 2.0 → **0.0** | 모션 계획 선행거리 |
| `OutPathError` | True → **False** | 경로 이탈 알람 **끔** |
| `ManualBlock` | True → **False** | 수동 모드 정지 기능 **끔** |
| `EmergencyStopDist` | 0.0 → **0.2 m** | 비상정지 거리 |

⚠ LQR 의 Q 가중(`BiSteer_maxQx`·`S_maxQ`)은 **전부 기본값**이다 — 튜닝은 속도·가속·조향속도·
스핀 PID 에 집중됐고 LQR 가중은 손대지 않았다.

## 5. 우리 2WS 스택과의 대조

| | Seer 원본 | 우리 2WS 스택 |
| --- | --- | --- |
| 경로 추종 | **LQR** + v/ω PID | **Pure Pursuit / MPC** + dual bicycle → IK |
| 자세 입력 | Seer 내부 측위(MCLoc) | `/robot_pose` ← Seer `1004` 중계(10 Hz) |
| 직선/회전 원시기동 | `3055`/`3056` — **오도메트리 개루프**(측위 모드 사용불가) | `translate_*`·`turn` — **측위 폐루프**(CTE·헤딩 오차 피드백) |
| 경로 정의 | 맵의 `advancedCurveList` | 액션 goal 의 좌표·`nav_msgs/Path` |
| 속도·가속 한계 | `MoveFactory` 전역 파라미터 | 액션 goal 필드 + params yaml |
| 조향 속도 | `SteerSpeed 180 °/s` | translator `steer_profile_velocity 30000` |

**주목할 대조 2가지**

1. **원시 기동의 폐루프 여부가 반대다.** Seer 의 `3055/3056` 은 오도메트리 개루프이고 측위
   모드는 벤더가 「사용 불가」라 적었다. 우리 `translate_*`/`turn` 은 측위 폐루프다. 즉 우리 쪽이
   **원리적으로는 더 정확할 수 있으나**, 그만큼 `/robot_pose` 품질·지연에 직접 노출된다.
2. **조향 속도 수치가 내 종전 추정과 크게 다르다.** 나는 `steer_profile_velocity 30000` 이
   0.1 rpm 단위라 가정해 **57.1 °/s** 를 유도했었다(그 단위 근거는 저장소·`References/` 어디에도
   없어 이미 철회했다 — `docs/adr/2026-08-06-turn-spin-removal-and-sim-plant-dynamics.md`).
   Seer 자신의 설정은 **180 °/s** 다. **두 값은 3배 이상 다르다.**
   ⚠ 다만 `SteerSpeed` 가 「지령 한계」인지 「달성 가능 슬루」인지는 문서에 없다 — 실측 전까지
   어느 쪽도 확정하지 않는다.

## 6. 이번 조사로 확인하지 못한 것

- 이 기체에 활성인 **차대 계열**(BiSteer 인지)을 Seer 가 보고하게 하는 방법
- LQR 의 상태·입력 정의(어떤 오차를 상태로 쓰는지) — 파라미터 이름과 설명뿐, 수식은 비공개
- 곡선 경로 클래스의 속성 집합(이 맵엔 직선뿐)
- `SteerSpeed 180 °/s` 가 실제 달성치인지
- Push API(19301) 구독 설정 — 여전히 미열람

## 부록 — 조회 방법 (읽기 전용, 재현용)

```bash
python3 - <<'PY'
import sys, json; sys.path.insert(0, "src/MES/csm")
from csm.seer_client import SeerStatusClient
with SeerStatusClient("192.168.44.82", timeout=8.0) as c:
    print(json.dumps(c.request(1400, {"plugin": "MoveFactory"}), ensure_ascii=False, indent=1))
PY
```

맵: `python3 Tools/seer_map/download_map.py <저장폴더>` (md5 자동 검증)
