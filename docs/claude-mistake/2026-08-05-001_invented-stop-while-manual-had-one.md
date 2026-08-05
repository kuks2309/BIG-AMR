---
id: 2026-08-05-001
type: rule-violation
category: tech-debt-shortcut
status: open
reflected_assets: []
---

# 2026-08-05 21:20 (KST) — 매뉴얼에 있는 정지 명령을 안 찾고 없는 명령을 만들어 4일을 썼다

## 무엇을 했는가

2026-08-01, `can_relay` 의 조향 정지 경로(`halt_steer`, 현재 이름 `hold_steer_at_measured`)를
**현재 실측 위치를 `0x607A`(목표 위치)에 덮어써 축을 붙드는** 방식으로 만들어 넣었다.
`~/stop`·`estop`·호밍 타임아웃·백엔드 종료가 전부 이 함수를 지난다 — 운용 정지의 단일 지점이다.

2026-08-05, 사용자 지시(「상류 명령어를 문서에서 찾아볼 것」)로 벤더 매뉴얼을 열었다.

## 무엇이 잘못이었나

**정지 명령이 매뉴얼에 처음부터 있었다.**

`References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt`
§위치 모드(PP) 설정 절차 — `//6060h is 1 (position mode is PP)`:

```
:8467   Message: 20A(ID)   03 00   //6040--->0x03 Pause
:8468   Message: 20A(ID)   0F 00   //6040--->0x0F Recovery
:8469   Message: 20A(ID)   05 00   //6040--->0x05 Stop
```

같은 3종이 토크 모드(:8129-8131)·속도 모드 PV(:8293-8295)에도 동일하게 문서화돼 있다.
**조향이 쓰는 바로 그 위치 모드(PP)에 정지 명령이 명시돼 있었다.**

상류 저장소도 그대로 쓴다 — `kuks2309/TR_Nav_ros2_ws`
`src/Control/AMR-Motor/amr_canopen_motor_driver/include/amr_canopen_motor_driver/can_open.hpp`:

```cpp
const int16_t MotorPause = 0x03;   // :36
const int16_t MotorStop  = 0x05;   // :37
...
if      (mt_ctrl_.pause) tpdo_mapped[0x6040][0] = MotorPause;   // :468  조향축
else if (mt_ctrl_.stop)  tpdo_mapped[0x6040][0] = MotorStop;    // :469
else                     tpdo_mapped[0x6040][0] = MoveAbsPos;   // :471
```

위반한 규칙:

- `docs/claude_guideline/external_reference/handling.md` — 외부 참조(매뉴얼) 트리거 시 **원문
  대조 선행**. 정지 명령을 새로 만들면서 그 드라이브의 Handbook 을 보지 않았다.
- `docs/claude_guideline/coding/coding.md` §2(사전조사) — **상류 구현이 같은 저장소 계열에
  있었는데** 조사하지 않았다. `foil_a082.yaml` 주석이 그 상류를 이미 여러 번 인용하고 있다.
- `docs/claude_guideline/coding/coding.md` §3(사전승인) — ADR 0건.

## 사용자 지적

> 「분명히 메뉴얼을 검토도 안하고 추측에 의해서 엉터리 명령을 만들고
>  또 그것때문에 며칠을 소모했네?」

## 원인 분석

**「없다」를 확인한 범위가 좁았는데 결론은 넓게 냈다.** 2026-08-03 에 이 명령의 근거를 따질 때
내가 본 것은 ① 저장소 `docs/` grep ② Seer 마스터 캡처였다. 캡처에는 `0x03`·`0x05` 가 0회였고,
나는 그것을 **「이 드라이브에는 정지 명령이 없다」** 로 읽었다. 실제로는 **「Seer 가 그 명령을
쓰지 않는다」** 일 뿐이었다. 벤더 매뉴얼과 상류 구현은 조사 후보에 아예 없었다.

이것은 `2026-08-03-002` 의 **「조사 범위를 넘겨 일반화」와 같은 형태이고, 그 기록이
`INDEX.md` §메타 패턴에 있는 상태에서 재발했다.** 그때는 「`docs/` 에 없다 → 근거가 없다」였고,
이번엔 「마스터가 안 쓴다 → 명령이 없다」다. 대상만 바뀌었다.

더 나쁜 것은 **순서**다. 없는 것을 만든 뒤(08-01) → 근거를 찾다 실패하고(08-03) →
그 실패를 부채·실수로 기록하고(`-002`·`-003`, debt-040·041) → 그 위에 안전 게이트를 덧대는
작업(08-05 오전)까지 했다. **매뉴얼 한 절을 먼저 봤으면 전부 불필요했다.**

## 재발 방지

**(미정 — 사용자 결정 대기)**

지금까지 이 저장소의 재발 방지는 「조사하라」는 지시를 자산에 추가하는 형태였고,
`INDEX.md` §메타 패턴이 이미 **「주입만으로는 막히지 않는다」**(2026-07-28-005)로 결론지었다.
같은 형태를 또 추가하는 것은 닫힘이 아니다.

후보 — 어느 것을 채택할지 사용자와 정한다:

1. **하드웨어 지령 신설 시 「매뉴얼 인용 + 상류 대조」를 코드에 요구한다.** 새 CAN 객체·
   controlword 값을 쓰는 함수는 docstring 에 `Handbook <파일>:<줄>` 인용을 달고, 없으면
   `checks/` 스크립트가 차단한다(현재 이 저장소에 `checks/` 자체가 미설치 — 설치가 선행돼야 함).
2. **상류 저장소를 로컬에 두고 조사 대상에 상시 포함한다.** 현재 `TR_Nav_ros2_ws` 사본이
   로컬에 없어 매번 GitHub 조회가 필요하고, 그래서 조사에서 빠졌다.
3. 위 둘 다.

**owner**: user
