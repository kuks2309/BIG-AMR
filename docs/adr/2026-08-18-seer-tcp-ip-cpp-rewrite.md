# ADR 2026-08-18 — `seer_tcp_ip` 를 C++ 로 재구현한다 (언어 결정 회수)

- **Status**: Accepted — 2026-08-18
- 대체: ADR [2026-08-07-seer-api-tcp-hal](2026-08-07-seer-api-tcp-hal.md) §Decision 1 의 `ament_python`,
  [2026-08-18-seer-tcp-ip-api-coverage](2026-08-18-seer-tcp-ip-api-coverage.md) 의 Python 구현
  (결정 내용은 유지, **언어만** 교체)

## Context

### 사실 1 — 언어가 결정 항목으로 올라온 적이 없다

`seer_tcp_ip` 는 `ament_python` 으로 만들어졌는데, 두 ADR 어디에도 **언어를 논한 절이 없다.**
`coding.md` §3 은 「공개 API 신설·변경(**언어 경계·결합 포함**)」을 사전승인 트리거로 두는데,
ADR 은 썼으면서 그 항목만 비웠다. 경위: `docs/claude-mistake/2026-08-18-002`.

### 사실 2 — 저장소 형상은 C++ 가 기본이다

| build_type | 패키지 수 |
|---|---|
| `ament_cmake` | **32** |
| `ament_python` | 12 |

(`find src -name package.xml` 의 `<build_type>` 집계, 2026-08-18.)
`docs/claude_guideline/coding/stack.md` §2「언어·런타임」은 **빈 템플릿**이라 선언이 없었고,
나는 그것을 「자유 선택」으로 읽었다. 실제로는 「미해결 → 문의」다 —
`git_workflow.md` §0 이 협업 모드에 대해 그 원칙을 이미 명문화하고 있다.
빈 칸을 없애기 위해 **`README.md` 에 `언어 표준:` 선언을 신설**했다.

### 사실 3 — 언어 경계가 곧 문제가 된다

Seer 와 말하는 패키지는 현재 전부 `ament_python` 이지만, **모션 스택
`trnav_2ws_action_server` 는 `ament_cmake`** 다. 어제 만든 자산의 핵심이 **제어권(4005)** 인데 —
모션 지령 전 반드시 필요한 그것을 C++ 액션 서버가 쓰려면 경계를 넘어야 한다.
broker 노드(debt-072)를 C++ 로 만들면 `control.py` 는 그대로 버려진다.

### 사실 4 — 16B 헤더 자체 구현이 **아직 하나 더 있다**

`src/MES/csm/csm/seer_client.py:43,45` 가 `SYNC = 0x5A` · `HEADER = struct.Struct(">BBHIH6s")` 로
같은 프로토콜을 독자 구현하고 있다. 2026-08-07 이관 때 라이다 2건만 걷었고 이건 놓쳤다.
**본 ADR 범위 밖**이며 debt 로 등록한다(다른 세션 소유 코드).

## Decision

### 1. `src/Comm/seer_tcp_ip` 를 `ament_cmake` · C++17 순수 라이브러리로 재구현한다

층 구조·포트 정책·편호 커버리지·제어권 세션 설계는 **그대로 옮긴다**. 바뀌는 것은 언어뿐이다.

| Python | C++ |
|---|---|
| `ports.py` | `include/seer_tcp_ip/ports.hpp` |
| `transport.py` | `include/seer_tcp_ip/transport.hpp` + `src/transport.cpp` |
| `api.py` | `include/seer_tcp_ip/api.hpp` + `src/api.cpp` |
| `control.py` | `include/seer_tcp_ip/control.hpp` + `src/control.cpp` |

- **`rclcpp` 무의존** — Python 판의 「ROS 무의존」 성질을 유지한다. 노드가 아니라 라이브러리다.
- 시험은 `mcl2d_core` 관례를 따른다 — **자체 CHECK 하니스**(gtest 미도입, 저장소에 1건뿐).
  ⚠ 기본 빌드타입이 Release(`-DNDEBUG`)라 `assert` 기반 시험은 무조건 통과한다 —
  `mcl2d_core/CMakeLists.txt:22-26` 이 그 함정을 적어 두었다. **자체 매크로**를 쓴다.

### 2. 의존성 — `nlohmann/json` (헤더 온리)

| 항목 | 내용 |
|---|---|
| **License** | MIT (재배포·상용 제약 없음) |
| **취약점** | 헤더 온리라 링크 표면 0. 입력은 로봇 응답 JSON 하나이며 `parse` 를 예외 모드로 쓴다(파싱 실패 = 프로토콜 오류로 승격). |
| **대안** | ① `jsoncpp`(설치돼 있으나 링크 필요·API 장황) ② `yaml-cpp`(저장소가 이미 쓰지만 **쓰기에 부적합** — flow 스타일에서 스칼라를 무인용으로 낼 수 있다) ③ 자체 파서(발명, 기각) |

`nlohmann-json3-dev` 는 이 PC(Personal Computer)에 설치돼 있고, Seer 의 `libNetProtocol.so` 자신도
같은 라이브러리를 쓴다(심볼 `nlohmann::basic_json`).

**의존성은 이것 하나로 끝낸다 — OpenSSL 은 넣지 않는다.**

초안 구현은 `downloadMap(verifyMd5)` 의 md5 대조를 옮기려고 `openssl/md5.h` 를 집었다.
Python 판은 `hashlib` 이 표준 라이브러리라 의존성이 0이었으므로, **이것은 요구사항이 아니라
언어 전환이 만든 비용**이다. 확인한 사실:

| 확인 | 결과 |
|---|---|
| 저장소의 기존 OpenSSL 의존 | `package.xml`·`CMakeLists.txt` 선언 **0건** |
| C++ 소스의 `openssl/` 사용 | **0건**(초안 `api.cpp` 제외) |
| `downloadMap(verifyMd5)` 호출자 | **0건** |

호출자가 없는 편의 인자 하나를 위해 저장소 최초의 시스템 의존성을 들이는 것은 값이 맞지 않는다.
**`downloadMap` 은 원문 바이트만 돌려주고 무결성 대조는 호출자 몫**으로 둔다 — 로봇이 주는 md5 는
`getMapStatus()`(`current_map_md5`)·`getMapMd5()` 로 이미 얻을 수 있고, 실제 소비자
(`seer_pose_publisher/pose_node.py:200-215` 의 맵 게이트)도 **바이트를 해싱하지 않고 값만 비교**한다.
필요해지는 시점에 그 소비자가 자기 방식으로 검증한다.

기각한 대안: ① OpenSSL 정식 등록(호출자 0건에 비해 과함) ② md5 자체 구현 ~150줄
(검증된 라이브러리 대신 발명 — 이 저장소가 경계하는 형태).

### 3. 소비자 3곳을 함께 옮긴다 — 두 벌 공존을 만들지 않는다

| 소비자 | 조치 |
|---|---|
| `seer_lidar_tf`(ament_python 노드) | **C++ 노드로 재작성**(ament_cmake). Seer 사용부는 `get_lasers()` 하나 |
| `seer_read_lidar_install.py`(단독 스크립트) | `seer_tcp_ip` 의 **C++ 실행파일** `read_lidar_install` 로 교체 |
| `Tools/seer_re/seer_param.sh` | python3 대신 그 실행파일 계열 CLI 호출로 교체 |

`Tools/amr_test_gui/gui.py` ↔ ROS2 이식본이 **두 벌 공존한 채 한쪽만 고쳐진** 선례가 있다
(debt-039). 같은 형태를 만들지 않는다 — Python 판은 이 작업에서 **삭제**한다.

## Alternatives (기각)

| 안 | 기각 사유 |
|---|---|
| Python 유지 + 필요할 때 C++ 바인딩 | 경계 관리 비용이 영구적이다. `stack.md` §4 의 결합 체크리스트(소유권·GIL·ABI·마샬링)가 전부 상시 부담이 된다. 지금 소비자가 3곳뿐이라 재작성이 더 싸다. |
| C++ 코어 + pybind11 노출 | 위와 같고, 게다가 **지금 Python 소비자를 남기는 이유가 없다** — 셋 다 C++ 로 옮길 수 있다. |
| 두 구현 병존(점진 이행) | debt-039 의 재현. 한쪽만 고쳐지고 어느 쪽이 정본인지 흐려진다. |
| 그대로 두고 broker 만 C++ | 제어권 세션이 Python 에 있는데 그것을 쓰는 broker 가 C++ 이면 **핵심 로직이 경계 반대편**에 남는다. |

## Consequences

**이득**
- 모션 경로(액션 서버·broker)에서 언어 경계가 사라진다.
- 저장소 형상·README 선언과 일치한다.

**비용**
- Python 자산 ~1,700줄(구현 1,044 + 시험 1,006)을 재작성한다. 돌연변이 57건도 이식 대상이다.
- `seer_lidar_tf` 재작성(207줄) + 단독 스크립트 대체.
- **실기 재검증 필요** — 조회 경로는 다시 돌려야 한다.

**남는 위험 / 미해결**
- 쓰기 API 실기 미검증(debt-111)은 **언어와 무관하게 그대로**다.
- `MES/csm` 의 세 번째 자체 구현(사실 4) — 별도 debt.
- 재작성 중 **동작이 미묘하게 달라질 수 있다.** Python 판의 시험 100건·돌연변이 57건이 계약을
  적어 놓았으므로 그것을 C++ 시험으로 1:1 옮기는 것이 이 작업의 안전장치다.

## Rollback

가역. `git revert` 또는:

1. `git checkout <이 커밋의 부모> -- src/Comm/seer_tcp_ip src/Sensors/Lidar/2D` 로 Python 판 복원.
2. `Tools/seer_re/seer_param.sh` 복원.
3. `README.md` 의 `언어 표준:` 선언은 남겨도 무해하다(사실 진술).
4. `colcon build --packages-select seer_tcp_ip seer_lidar_tf` 재실행.

영속 상태·스키마·펌웨어 변경 없음. 로봇에 쓰기 동작 없음.
