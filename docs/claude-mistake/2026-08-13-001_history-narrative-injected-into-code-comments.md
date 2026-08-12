---
date: 2026-08-13
id: 2026-08-13-001
type: rule-violation
severity: medium
reflected_assets:
  - docs/debt/registry.md
  - src/Control/Motion_Control/2WS/trnav_2ws_kinematics/docs/trnav_qd_kinematics_code_updates.md
  - src/Control/Motion_Control/2WS/trnav_2ws_core/docs/amr_motion_core_code_updates.md
  - src/Control/Motion_Control/2WS/trnav_2ws_motion/docs/trnav_motion_qd_code_updates.md
  - src/Control/Motion_Control/2WS/trnav_2ws_interfaces/docs/amr_interfaces_code_updates.md
  - src/Control/Motion_Control/2WS/trnav_2ws_action_server/docs/amr_motion_action_server_code_updates.md
---

# 잘못된 주석을 고치면서 「무엇을 고쳤는지」를 주석 안에 적었다 — 감사 1라운드를 자초했다

## 사용자 지적

> 「기능만 넣기 이력은 넣지마시길」
>
> 「코드의 주석은 이력을 넣지 않습니다. 대신 code update 문서에서 만드는 것이
>  주석으로 인한 오류를 줄일 수 있습니다.」
>
> 「지금까지 잘못된 주석으로 2~3배의 부채를 키웠습니다.」

## 무슨 일이 있었나

2WS 모션 스택의 잘못된 주석을 감사·정정하는 작업이었다. 1·2라운드에서 111건을 고쳐
커밋(`6fb9663`)했는데, 그 정정문 상당수가 **코드가 지금 무엇을 하는지가 아니라
내가 무엇을 고쳤는지**를 적고 있었다.

실제로 심은 문구들:

| 파일 | 내가 넣은 것 |
| --- | --- |
| `launch/sil_mpc.launch.py` | `종전 문구 "TF2 map->base_link not available" 는 2026-08-10 교체됐고, 지금은 QD 스택 액션 서버들만 그 문구를 낸다` |
| `launch/mpc.launch.py` | `⚠ 근거로 적혀 있던 docs/plan/… 는 이 저장소에 없다(디렉터리 자체가 부재, git 이력에도 0건)` |
| `qd_crab_inverse_kinematics.cpp` | `그 불일치는 실재했고(2026-08-08 확인) 헤더를 구현 기준으로 정정해 해소했다` |
| `qd_crab_inverse_kinematics.cpp` | `종전 「motor saturate」 표기는 클램프 90° 전제였다 — 2026-08-06 결정으로 …` |
| `trnav_2ws_core/package.xml` | `… is not present in this repository … In-repo trace of both decisions: docs/…code_updates.md` |
| `mpc_reverse_action_server.hpp` | `… docs/abstraction/motion_source_id_contract.md 는 이 저장소에 없다(2026-08-09 확인)` |

## 비용

3라운드 라인 단위 재독(16,174줄, 36 에이전트)에서 **69건을 고쳤는데 그중 22건이
1·2라운드가 심은 이력 서술**이었다 — 3라운드 작업의 **약 1/3 이 자초한 것**이다.

더 나쁜 것은 **그 이력 자체가 이미 틀려 있었다**는 점이다. `2026-08-06 결정으로` 라고
적었으나 `foil_a082.yaml` 의 클램프 115° 변경 커밋은 `e0064d5 2026-08-05` 다.
**주석을 낡음에서 구하려고 넣은 문장이 그 자리에서 새로운 낡음이 됐다.**

## 왜 그랬나 (판단 실패의 형태)

지식 공백이 아니었다. 「주석은 현재 동작을 적는 곳」은 알고 있었다.
**감사 근거를 남기려는 의도가 그 원칙을 이겼다** — 「이 정정이 근거 있다는 것을
읽는 사람이 알아야 한다」는 생각으로 근거를 주석에 실었고, 그 결과:

- 주석이 **두 개의 시제**를 갖게 됐다(현재 동작 + 과거 변경). 뒤엣것은 반드시 낡는다.
- 「… 는 이 저장소에 없다」 같은 **부재 서술**을 남겨, 그 파일이 나중에 생기면 즉시 거짓이 된다.
- 이력이 갈 곳(`docs/*_code_updates.md`)이 **이미 있었고 같은 커밋에서 내가 쓰고 있었는데도**
  같은 내용을 주석에 중복해서 넣었다.

사용자 지적의 핵심은 이 마지막 줄이다 — **분리가 곧 예방책**이다.
이력이 한 곳(code_updates)에만 있으면 낡아도 한 곳만 낡고, 주석은 코드와만 대조하면 된다.

## 재발 방지

**등록된 부채**

- `debt-071`(지능) — 본 건. 상환 전략은 「가장 먼저 볼 것」 고정:
  **주석을 쓰기 전 「이 문장이 1년 뒤에도 참인가」를 묻는다.** 참이 아니면
  (날짜·「종전」·「정정했다」·「…에 없다」·조사 결과 보고) 주석이 아니라 `code_updates` 소관이다.
  부재 사실은 **서술하지 않고 인용을 삭제**한다.
- `debt-070`(이해) — 이번 감사가 드러낸 상위 문제. 2WS 주석 180건이 코드와 어긋나 있었고
  (≈90줄당 1건) **빌드·테스트가 이를 전혀 검출하지 못한다**(67 tests PASS 상태에서 살아 있었다).
  상환 계획은 주석↔코드 재도출 검사기 신설.

**이번에 실제로 한 조치**

- 심었던 이력 서술 22건 전량 제거, 기능 서술로 환원. 잔존 스캔
  (`종전|정정해|해소했|교체됐|이 저장소에 없다|확인\)|not present in this repository|In-repo trace`) **0건**.
- 이력은 5개 패키지 `docs/*_code_updates.md` 로 이관(정정 내역·기각 사례·검증 근거 포함).
- 코드 무변경 증명 유지: 변경 파일을 언어별 파서로 대조 — 차이 0건.
  `colcon build` 6패키지 PASS · `colcon test` 67 tests / 0 failures.

## 남는 위험 (정직 선언)

`debt-070` 의 검사기는 **아직 없다.** 지금 막은 것은 이번 스택의 이번 180건뿐이며,
검사기가 설치되기 전까지 이 부채는 **수동 준수로만** 지켜진다.

형제 QD(Quad-Drive) 스택(`src/Control/Motion_Control/QD/**`)에도 같은 종류의 잔재가 있으나
**본 저장소에서 감사하지 않는다** — LGIT 에서 검증한 뒤 이식할 예정이기 때문이다(2026-08-13 사용자 확인).
통제점은 감사가 아니라 **이식 시점**이다: 이식본이 검사기를 통과하기 전에는 머지하지 않는다.

⚠ 이 감사에서 내가 쓴 프레이밍 하나를 정정한다 — **2WS 는 QD 의 「사본」이 아니다.**
QD 에서 이식해 왔지만 **전 기동이 실기검사를 마친 독립본**이다(2026-08-13 사용자 확인).
따라서 「QD 형제가 그렇게 적고 있다」는 2WS 주석의 근거가 될 수 없다. 3라운드 기각 판정 중
그 논거에 기댄 것이 있었고(`trnav_2ws_kinematics/package.xml` 의 `src/Control/Kinematics/` 언급 —
그 경로를 주장하는 살아 있는 텍스트 5곳이 **전부 QD 파일**이었다) 재판정해 제거했다.
