# ADR 2026-07-28 — 시스템 자원 감시기 Phase 1 (`src/Safety/system_health`)

Status: Accepted (사용자 지시 sess:9988218d 2026-07-28: "안정성을 위해서 pc온도 램 상태 cpu상태 등의 모니터링이 필요합니다 … 향후 sw이상유무까지 점검", "phase 1번 진행")

선택지 승인 (같은 세션):
- 배치 = `src/Safety/system_health` (사용자: "폴더는 …/src/Safety 이 좋겠죠?")
- 구성 = 비-ROS 상주 샘플러(systemd) + 얇은 ROS 브리지 2단 (사용자: "<- 동의")
- 온도 임계값 = **우리 프로그램이 자체 기준을 갖는다. 기존 NVIDIA Orin thermal 설정은 무시**
  (사용자: "온도 설정은 새로 작성한 프로그램에서 할 것이고 기존 nvidia orin 설정은 무시할 것")
- 범위 = Phase 1(자원 샘플러)만. 카메라 파이프라인 개선은 **향후 분석 후 별건**
  (사용자: "<- 향후 결정 분석후 개선할 내용임")

---

## Context (배경)

### 왜 필요한가

AMR(Autonomous Mobile Robot, 자율주행 이동로봇) 본체 PC 는 Jetson Orin NX 16GB 단일 노드에서
카메라 6대 + 모션 스택 + CAN(Controller Area Network) 릴레이를 동시에 돌린다. 현재 어떤 상주
자원 감시도 없어, 장애가 나도 **그 시점의 온도·메모리·디스크 상태를 사후에 알 방법이 없다.**

### 실측 기준선 (2026-07-28, 본 세션에서 직접 측정)

| 항목 | 실측값 | 출처 |
| --- | --- | --- |
| 플랫폼 | Jetson Orin NX 16GB (`NX150_2024-12-23`), JetPack R36.3.0 | `/etc/nv_tegra_release`, `/proc/device-tree/model` |
| 전력 모드 | MAXN + `jetson-clocks.service` (oneshot, RemainAfterExit) | `nvpmodel -q`, `systemctl cat jetson-clocks` |
| RAM | 15,657 MB 중 6,705 MB 사용, `lfb 5x4MB` | `free -m`, `tegrastats` 1회 |
| Swap | 18,068 MB 중 0 MB | `free -m` |
| 디스크 | `/dev/nvme0n1p1` 116 G 중 73 G(67%) 사용, 여유 37 G | `df -h /` |
| 온도 | cpu 51.8 / gpu 49.4 / tj 51.8 / soc0~2 48~50 °C | `thermal_zone*/temp` |
| 전력 | VDD_IN 12.3 W | `tegrastats` |
| 팬 | `pwm1 = 1` (거의 정지) | `/sys/devices/platform/pwm-fan/hwmon/hwmon*/pwm1` |
| 팬 제어 주체 | **userspace `nvfancontrol.service`** (active·enabled, POLLING_INTERVAL 2, FAN_DEFAULT_PROFILE quiet) | `systemctl is-active`, `/etc/nvfancontrol.conf` |
| 가용 수단 | `tegrastats`, `nvidia-smi`, `psutil 5.9.0`, thermal zone 9개 | `which`, import |

### 커널 thermal 설정 — 본 ADR 의 결정 근거가 **아니다**

사용자 결정에 따라 커널·`nvfancontrol` 설정은 **읽지도 따르지도 않고**, 우리 임계값을 따로 둔다.
아래는 "우리 임계값의 상한이 어디인가"를 알기 위한 참고일 뿐이다(2026-07-28 실측):

| zone0 (`cpu-thermal`) trip | 온도 | type | 실제로 바인딩된 cooling device |
| --- | --- | --- | --- |
| `trip_point_2` | 70 °C (hyst 8) | passive | `hot-surface-alert` 만 |
| `trip_point_0` | 99 °C | passive | `cpufreq-cpu0`, `cpufreq-cpu4`, `cpu-throttle-alert`, `devfreq-gpu` |
| `trip_point_1` | 104.5 °C | critical | 커널 셧다운 |

⚠ 세션 중 "70 °C 부터 커널이 클럭을 깎는다"고 서술했다가 **cdev 바인딩 실측으로 반증되어 정정**했다
(주파수 저감은 99 °C). 이 값들은 참고 상한일 뿐이며, 운영 임계값은 §Decision 4 에서 우리가 정한다.

### 관측 부하 제약 (기존 자산이 이미 세운 원칙)

`Tools/usb_cam_bench/soak_monitor.py:9-12` 는 *"구독자를 새로 만들지 않는다 — 관측 자체가 DDS
(Data Distribution Service) 부하를 더해 시험 대상을 바꾸면 안 되기 때문"* 이라고 근거까지 남기고
로그 tail 방식을 택했다. 본 감시기도 같은 규율을 승계한다.

### 디스크 방어 선례

`src/AI/dataset_collector/dataset_collector/sampling.py:21` `MIN_FREE_GB_DEFAULT = 5.0` 이 이미
디스크 하한 방어를 구현하고 테스트까지 갖췄다. **본 감시기는 그 값을 재정의하지 않고 그보다
높은 하한에서 먼저 경고**해, 두 방어가 순서대로 걸리게 한다.

---

## Decision (결정)

### 1. 배치 — 단일 ament_python 패키지 `src/Safety/system_health`

Phase 1(비-ROS 샘플러)과 Phase 2(ROS 브리지)를 **한 패키지**에 둔다. 한 기능을 `Tools/` 와 `src/`
두 트리로 쪼개면 유지보수가 갈라지고, `src/Safety/` 는 현재 비어 있어 이 용도의 예약 슬롯으로 맞다.

> 세션 초반에 Phase 1 을 `Tools/` 로 제안했다가 철회했다. 저장소 규약(`Tools/`=비-ROS)과
> 어긋나 보이지만, **ROS 독립성은 파일 위치가 아니라 import 경계로 지킨다**(§2).

### 2. ROS 독립성은 **import 불변식**으로 강제한다

- `sysfs.py` · `ringlog.py` · `thresholds.py` · `sampler.py` 는 **`rclpy` 를 import 하지 않는다.**
- 이 불변식은 문서 약속이 아니라 **단위 테스트로 검사**한다(`test_no_rclpy_import.py`).
- 근거: ROS 가 죽었거나 부팅에 실패한 순간이 자원 로그를 가장 보고 싶은 시점인데, 노드 안에
  넣으면 정확히 그때 같이 죽는다.

### 3. 수집은 **sysfs/procfs 직독**, DDS participant 0개

- `tegrastats` 출력 파싱에 의존하지 않는다 — JetPack 버전마다 필드가 바뀌는 문자열이라 파서가
  조용히 깨진다. `tegrastats` 는 사람이 하는 교차검증용 1회 스냅샷으로만 쓴다.
- `ros2 topic hz` / `ros2 node list` 등 **서브프로세스 호출 금지** — 호출마다 새 DDS participant 를
  만들어 전체 노드에 discovery 트래픽을 유발한다. Phase 3 의 토픽 감시도 이 방법을 쓰지 않는다.
- 이미지 토픽 구독 금지(썸네일 포함). 감시기는 이미지를 다루지 않는다.

### 4. 임계값은 **우리 값**, 기본값은 `잠정(provisional)` 로 명시

커널 trip 값을 운영 임계로 쓰지 않는다. 99 °C 는 이미 성능이 무너진 뒤이고 셧다운(104.5 °C)이
5.5 °C 앞이라 경보로 너무 늦다. 70 °C 는 표면온도 경보 지점일 뿐 실리콘 여유와 무관하다.

Phase 1 기본값 (전부 CLI/JSON 으로 덮어쓰기 가능):

| 항목 | WARN | ERROR | 근거 |
| --- | --- | --- | --- |
| 최고 존 온도 | 75 °C | 85 °C | 현재 정상 51.8 °C 대비 +23/+33, 셧다운 104.5 °C 대비 충분한 선행 여유. **잠정** |
| CPU 사용률(전체) | 85 % | 95 % | 현재 27~41 %. **잠정** |
| 가용 메모리 | < 2,000 MB | < 1,000 MB | 현재 가용 8,797 MB |
| Swap 사용 | > 256 MB | > 2,048 MB | 현재 0 MB. swap 진입 = 실시간성 붕괴 조기경보 |
| 디스크 여유 | < 10 GB | < 6 GB | `dataset_collector` 하한 5 GB **보다 먼저** 걸리도록 |
| 팬 | — | `nvfancontrol` 미동작 | 팬 정지는 온도 상승의 *원인*이라 온도만으로는 인과를 못 가림 |

**온도·CPU 기본값은 램프 시험 전 잠정치다.** 코드·문서 양쪽에 `잠정` 으로 표기하고, 후속
과제(§Consequences)의 램프 시험 결과로 확정한다. 지어낸 값을 확정처럼 쓰지 않는다.

**사용자가 값을 정해 파일로 고정한다** (2026-07-28 사용자 지시 sess:9988218d: "2번은 사용자가
정해서 설정 저장하도록"). 임계값은 우리가 정하는 값이므로 코드 상수로 묻어두지 않는다:

- 정본 경로: `config/system_health/thresholds.json` (JSON, 사람이 편집)
- `--write-thresholds <path>` 로 현재 값을 그 형식으로 저장한다. 파일에는 값과 함께
  `_provisional` 목록을 적어 **어느 항목이 근거 미확정인지 파일만 보고 알 수 있게** 한다.
- `_` 로 시작하는 키는 다시 읽을 때 주석으로 무시한다(`COMMENT_KEY_PREFIX`) — JSON 에 주석
  문법이 없어서, 설명을 남기면서도 왕복 가능하게 하려면 이 관례가 필요하다. 그 외 미지의
  키는 여전히 `KeyError` 로 거부한다(오타를 삼키면 사용자가 값을 바꿨다고 믿는데 안 바뀐다).
- `install_service.sh --apply` 는 파일이 **없을 때만** 기본값으로 생성한다 — 재설치가 사용자가
  고쳐 둔 값을 되돌리면 안 된다. 변경 반영은 `systemctl restart amr-health-sampler`.

### 5. 팬은 **읽기만** 한다 (설정하지 않음)

`nvfancontrol` 설정을 바꾸지 않는다. `pwm1` + `nvfancontrol` 프로세스 생존만 기록한다.
목적은 "온도가 올랐다"와 "팬이 멈춰서 올랐다"를 구분하는 것이다.

> 실측 제약: 본 하드웨어의 `pwm-fan` hwmon 에는 `pwm1` 만 있고 **`rpm` 노드가 없다**
> (`ls /sys/devices/platform/pwm-fan/hwmon/hwmon*/` → device, name, of_node, power, pwm1,
> subsystem, uevent). 따라서 RPM(Revolutions Per Minute) 기반 팬 고착 판정은 **Phase 1 에서 불가**
> 하며, `pwm1` 과 온도 추세로만 간접 판단한다. 이 한계를 코드 주석과 산출 스키마에 명시한다.

### 6. 로그는 **자기 용량 상한을 스스로 강제**하는 링버퍼

- 형식: JSONL(JSON Lines), 파일명 `health-YYYY-MM-DD.jsonl` (일자 회전).
- 상한: 총량 기본 512 MB + 보존 기본 14일. 초과 시 **가장 오래된 파일부터 삭제**.
- **쓰기 실패를 예외로 삼키지 않는다** — 연속 실패를 카운트해 stderr(journald)로 올린다.
  감시기가 살아 있는 것처럼 보이면서 아무것도 기록하지 않는 상태가 최악이다.

### 7. systemd 유닛은 **소스 트리에서 직접 실행**

`colcon build` 산출물(`install/`)이 아니라 소스 경로를 `PYTHONPATH` 로 지정해 실행한다.
근거: `colcon build --cmake-clean-cache` 등으로 `install/` 이 비워지는 순간 감시기가 죽으면
안 된다. 선례 `can0-setup.service` 와 같은 `/etc/systemd/system/` 배치를 따른다.

유닛 파일은 저장소에 두고(`systemd/amr-health-sampler.service`), 설치는 사용자가 명시적으로
`install_service.sh` 를 실행할 때만 한다 — **본 작업은 유닛을 자동 설치하지 않는다.**

### 8. 동시성 — 신호 핸들러 1개, lock 없음

`domains/concurrency-coding.md` 활성(신호 핸들러). 공유 가변 상태는 정지 플래그 하나뿐이며
**writer 는 SIGTERM/SIGINT 핸들러 단독, reader 는 메인 루프 단독**이다. 단일 writer + 원자적
bool 대입이므로 lock 을 두지 않는다. 이 writer 는 전역변수표 "누가 바꾸나" 칸에 기록한다.

### 9. 의존성 — 표준 라이브러리만

`psutil` 이 설치돼 있으나 쓰지 않는다. 새 의존성 0. 근거: 감시기는 다른 것이 다 깨져도 떠야
하므로 의존 표면을 최소로 유지한다.

---

## Consequences (결과)

### 얻는 것

- ROS·colcon·DDS 와 무관하게 부팅 직후부터 자원 곡선이 쌓인다.
- 장애 시점의 온도·메모리·디스크·팬 상태가 사후 분석 가능한 형태로 남는다.
- Phase 2(ROS `/diagnostics` 브리지)·Phase 3(SW 워치독)이 같은 패키지에 증분으로 얹힌다.
  `/diagnostics` 는 이미 저장소 관례다 —
  `src/Actuators/motor_control/motor_control/driver_node.py:359-375`,
  `src/Sensors/Lidar/2D/sick_safetyscanners2/README.md:141`.

### 치르는 비용 / 남는 위험

- **임계값 기본치가 잠정이다.** 램프 시험 전까지 오탐/미탐 가능. `잠정` 표기로 관리.
- **팬 고착을 직접 판정할 수 없다** (RPM 노드 부재, §Decision 5). `pwm1` + 온도 추세 간접 판단만.
- **CPU 임계가 순간값 기준**이다. 짧은 스파이크에 오탐할 수 있다 — 지속시간 기반 판정은 미구현.
- systemd 유닛이 저장소 절대경로에 의존한다(로봇 1대 전제). 다중 대수 배포 시 템플릿화 필요.
- **개입은 하지 않는다.** Phase 1~3 전부 read-only 관측이며, 자동 감속·안전정지는 별도 ADR 대상.
  근거: 검증 안 된 지령으로 실장비를 손상시킨 이력(`docs/claude-mistake/2026-07-27-002`).

### 후속 과제 (본 ADR 범위 밖 — 별도 착수)

1. **팬 커브 램프 시험** — 부하를 단계적으로 올리며 온도·`pwm1` 동시 기록 → 온도 임계 확정.
2. **JPEG 장당 크기 실측** — `dataset_collector` 기본값(1 s 간격 × 6대)의 실제 디스크 소모율 산출.
3. Phase 2 — ROS `/diagnostics` 브리지.
4. Phase 3 — SW 이상유무 워치독(노드 생존·토픽 최신성·CAN 에러 카운터).
5. 카메라 파이프라인 개선(raw 를 DDS 에 태우지 않기) — 사용자 지시로 **향후 분석 후 별건**.

---

## Rollback (되돌림 계획)

본 변경은 **가역**이다. 되돌리는 절차:

1. **systemd 유닛** — 본 작업은 유닛을 설치하지 않으므로 기본 상태에서 되돌릴 것이 없다.
   사용자가 `install_service.sh` 로 설치한 경우에만:
   ```bash
   sudo systemctl disable --now amr-health-sampler.service
   sudo rm /etc/systemd/system/amr-health-sampler.service
   sudo systemctl daemon-reload
   ```
2. **패키지** — `rm -rf src/Safety/system_health` (다른 패키지가 import 하지 않으므로 파급 0).
3. **로그** — `rm -rf <out-dir>` (감시기 산출물 전용, 다른 자산 없음).
4. **시스템 설정** — 본 변경은 `nvfancontrol`·`nvpmodel`·커널 thermal·CAN 설정을 **일절 수정하지
   않는다**. 따라서 되돌릴 시스템 상태 변경이 없다(읽기 전용).

비가역 요소 없음 — 영속 스키마·펌웨어·외부 상태 변경 0.

---

## 관련 문서

- 코드 SOP: `docs/claude_guideline/coding/coding.md` (Full scope 적용)
- 적용 도메인: `domains/concurrency-coding.md`(신호 핸들러), `domains/ros2-coding.md`(`package.xml`)
- 면제 도메인: `embedded`(ISR·레지스터 접근 없음), `memory`(수동 메모리 없음), `numeric`(해당 없음)
- 함수표·전역변수표: `docs/sw_structure/system-health/2026-07-28.md` (루트 정본)
  + `src/Safety/system_health/docs/sw_structure/system-health/2026-07-28.md` (패키지 병기)
