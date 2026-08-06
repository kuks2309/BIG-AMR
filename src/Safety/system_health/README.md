# system_health — AMR 본체 PC 자원 감시 (Phase 1)

Jetson Orin NX 의 온도·CPU·메모리·디스크·팬 상태를 주기적으로 표본화해 JSONL 로 남긴다.
**관측 전용이다 — 어떤 하드웨어도 제어하지 않는다.**

설계 결정과 근거: [`docs/adr/2026-07-28-system-health-monitor.md`](../../../docs/adr/2026-07-28-system-health-monitor.md)
구조(함수표·전역변수표·시퀀스): [`docs/sw_structure/system-health/2026-07-28.md`](docs/sw_structure/system-health/2026-07-28.md)

## 왜 ROS 밖에 있나

ROS 가 죽었거나 부팅에 실패한 순간이 자원 로그를 가장 보고 싶은 시점이다. ROS 노드 안에 넣으면
정확히 그때 같이 죽는다. 그래서 Phase 1 모듈(`sysfs`·`ringlog`·`thresholds`·`sampler`)은
`rclpy` 를 import 하지 않으며, 그 불변식은 `test/test_no_rclpy_import.py` 가 정적·동적 양쪽으로
검사한다. (Phase 2 의 `/diagnostics` 브리지만 `rclpy` 에 의존할 예정이다.)

## 빠른 사용

```bash
cd src/Safety/system_health

# 1회 표본을 stdout 으로 (CPU 사용률을 위해 1초 기준선을 먼저 잡는다)
python3 -m system_health.sampler --once

# 상주 실행 — 5초 주기, JSONL 링버퍼로 기록
python3 -m system_health.sampler --interval 5 --out-dir ../../../Log/health

# 임계값 덮어쓰기
echo '{"temp_warn_c": 70.0}' > th.json
python3 -m system_health.sampler --once --thresholds th.json
```

`--out-dir` 을 생략하면 stdout 으로만 낸다(systemd 아래에서는 journald 가 받는다).

## systemd 상주

유닛은 **저장소에 있을 뿐 자동 설치되지 않는다.** 명시적으로 실행할 때만 설치된다.
유닛은 둘이고 **서로 의존하지 않는다** — 대시보드가 죽어도 기록은 계속되고, 샘플러가 죽어도
지금까지의 기록은 볼 수 있어야 하기 때문이다.

| 유닛 | 역할 | 노출 |
| --- | --- | --- |
| `amr-health-sampler.service` | 수집(5초 주기) | 없음 |
| `amr-health-webview.service` | 대시보드 | **127.0.0.1 전용** |

```bash
./install_service.sh                    # dry-run — 무엇을 할지 보여주기만 한다
./install_service.sh --apply            # 둘 다 설치·기동
./install_service.sh --apply webview    # 하나만 (sampler|webview|both)
./install_service.sh --status           # 현재 상태
./install_service.sh --remove [대상]    # 되돌리기(로그·임계값 보존)
journalctl -u amr-health-sampler -f
```

**대시보드는 로컬 전용이다**(2026-07-31 사용자 결정). 인증이 없으므로 루프백에만 바인드하고,
`IPAddressAllow=localhost` + `IPAddressDeny=any` 로 **커널(cgroup v2 BPF) 수준에서도** 막는다 —
`--bind` 인자가 실수로 바뀌어도 외부로 열리지 않는다. 다른 PC 에서 볼 때는 SSH 터널을 쓴다:

```bash
ssh -L 8770:127.0.0.1:8770 nvidia@<이 장비>   # 그 뒤 http://127.0.0.1:8770/
```

⚠ **수동 실행 인스턴스를 남겨두지 말 것.** 포트가 겹치면 서비스가 `Address already in use` 로
재시작 루프에 빠지는데, 그 사이에도 수동 인스턴스가 응답하므로 **동작하는 것처럼 보인다**.
`./install_service.sh --status` 로 `active` 인지 확인하고, `ss -tlnp | grep 8770` 의 PID 가
`systemctl show amr-health-webview -p MainPID` 와 같은지 대조한다.
(2026-07-31 실제로 발생 — `--bind 0.0.0.0` 수동 인스턴스가 34 시간 떠 있어 서비스를 막았고,
그 동안 대시보드가 외부에 노출돼 있었다.)

유닛은 `install/` 이 아니라 **소스 트리**를 `PYTHONPATH` 로 가리킨다 — `colcon build` 가
`install/` 을 비우는 순간 감시기가 죽으면 안 되기 때문이다. `Nice=10` + `IOSchedulingClass=idle`
로 관측이 대상을 방해하지 않게 한다.

## 수집 항목

| 항목 | 소스 | 비고 |
| --- | --- | --- |
| 온도 9존 | `thermal_zone*/temp` | cpu·gpu·cv0~2·soc0~2·tj |
| 냉각장치 단계 | `cooling_device*/cur_state` | 0 이 아니면 **실제로 개입 중** |
| CPU 사용률(전체·코어별) | `/proc/stat` 차분 | 첫 표본에는 없음(누적값 차분이라) |
| CPU 주파수 | `scaling_cur_freq` | 최대 미달 = 저감 확증 |
| 메모리·스왑 | `/proc/meminfo` | `used = total − available` |
| 디스크 | `statvfs` | `f_bavail` 기준(root 예약분 제외) |
| **GPU 사용률·주파수** | `gpu.0/load` ÷10, devfreq | Jetson 을 쓰는 이유. sysfs 는 **천분율**(2026-07-28 tegrastats 대조 확정) |
| **전원 레일 전압·전류·전력** | INA3221 hwmon | VDD_IN·VDD_CPU_GPU_CV·VDD_SOC. **라벨 있는 채널만** — 라벨 없는 `curr4` 는 shunt 파생값이지 레일이 아니다 |
| **스왑 활동량** | `/proc/vmstat` pswpin/out 차분 | 사용량이 아니라 **지금 쓰고 있는지**가 위험 신호 |
| 팬 | `pwm-fan/hwmon/*/pwm1` | **읽기 전용.** `rpm` 노드는 본 HW 에 없음 |
| 부하·가동시간 | `getloadavg`, `/proc/uptime` | 재시작 감지 |
| 프로세스 수·상위 RSS | `/proc/*/stat` | 기본 12주기마다(무거우므로) |
| 팬 데몬 생존 | 위 순회의 이름 집합 | `nvfancontrol` 이 죽으면 팬이 멈춘 채 고정된다 |
| **선언 프로세스 생존·재시작** | `/proc/*/stat` comm·PID | Phase 3a. **선언이 없으면 판정 안 함** |
| **CAN 인터페이스** | `/sys/class/net/*` (`type==280`) | Phase 3a. 인터페이스가 없으면 항목 자체가 없다 |
| **DDS 세그먼트 수** | `/dev/shm` | Phase 3a. **기록만** — 정상 개수를 모른다 |

## 임계값

**우리 기준이다.** 커널 trip 값이나 `nvfancontrol` 설정을 따르지 않는다.

| 항목 | WARN | ERROR |
| --- | --- | --- |
| 최고 존 온도 | 75 °C ⚠잠정 | 85 °C ⚠잠정 |
| CPU 사용률 | 85 % ⚠잠정 | 95 % ⚠잠정 |
| 가용 메모리 | < 2,000 MB | < 1,000 MB |
| 스왑 **활동** | > 64 pages/s | > 512 pages/s |
| 디스크 여유 | < 10 GB | < 6 GB |
| GPU 사용률 | 기본 **비활성** | 기본 **비활성** |
| 입력 전류 | 기본 **비활성** | 기본 **비활성** |
| 팬 데몬 | — | 미동작 |
| **선언 프로세스 소실** | — | 없으면 ERROR |
| **선언 프로세스 재시작** | PID 변경 | — |
| **CAN down** | — | down 이면 ERROR |
| **CAN 에러 증가율** | 기본 **비활성** | 기본 **비활성** |
| 로그 기록 | — | 실패 |

**⚠잠정** 표시는 부하 램프 시험 전 잠정치라는 뜻이다(`thresholds.PROVISIONAL_KEYS`). 지어낸 값을
확정처럼 쓰지 않기 위해 코드에 명시해 두었다. 램프 시험 후 확정할 것.

### 값 바꾸기 — 사용자가 정해 파일로 고정한다

정본은 [`config/system_health/thresholds.json`](../../../config/system_health/thresholds.json) 이다.

```bash
# 현재 값을 편집 가능한 JSON 으로 저장(없으면 install_service.sh --apply 가 자동 생성)
python3 -m system_health.sampler --write-thresholds ../../../config/system_health/thresholds.json

# 파일을 편집한 뒤 상주 서비스에 반영
sudo systemctl restart amr-health-sampler
```

파일에는 `_provisional` 목록이 함께 적혀 있어 **어느 항목이 아직 근거 미확정인지 파일만 보고**
알 수 있다. `_` 로 시작하는 키는 다시 읽을 때 주석으로 무시되므로 설명을 남겨도 깨지지 않는다.
그 외 오타 키는 `KeyError` 로 거부한다 — 값을 바꿨다고 믿는데 실제로는 안 바뀐 상태가 가장
위험하기 때문이다.

`install_service.sh --apply` 는 파일이 **없을 때만** 만든다. 재설치해도 고쳐둔 값은 유지된다.

디스크 하한은 `dataset_collector` 의 `MIN_FREE_GB_DEFAULT = 5.0` 보다 **높다** — 감시기가 먼저
경고하고, 그래도 차면 수집기가 저장을 멈추는 순서를 만들기 위해서다.

## 로그

`<out-dir>/health-YYYY-MM-DD.jsonl`, 일자 회전. 총량 512 MB + 보존 14일 상한을 **스스로 강제**해
감시 로그가 디스크를 채우는 일을 막는다(상한 초과 시 가장 오래된 파일부터 삭제, 쓰는 중인 최신
파일은 절대 삭제하지 않음).

기록 실패는 삼키지 않는다 — stderr 로 즉시 올리고 표본 전문을 덤프하며, 다음 표본의
`log_write_failed` 를 통해 ERROR 로 승격한다. 복구되면 복구 메시지를 낸다.
(한계: JSONL 안의 `log_write_failed` 플래그는 **한 주기 지연**된다. 현재 주기의 쓰기 실패는
써보기 전에는 알 수 없기 때문이다. 즉시성이 필요한 쪽은 stderr/journald 를 보면 된다.)

실측(본 장비, 2026-07-29 · 16 h 시험 운전): 표본당 약 1.3 KB → 5초 주기에서 하루 약 22 MB.

## 관측 부하 (실측)

관측이 대상을 바꾸면 안 된다는 원칙은 `Tools/usb_cam_bench/soak_monitor.py` 에서 이어받았다.

| 조건 | 표본당 CPU | 단일 코어 점유율 | RSS |
| --- | --- | --- | --- |
| 기본(5초 주기, 12주기마다 `/proc` 순회) | 20 ms | 0.45 % | 12 MB |
| 최악(1초 주기, 매 주기 순회) | 36 ms | 3.51 % | 12 MB |

8코어 기준으로 환산하면 기본 설정은 약 0.06 % 다. DDS participant 는 **0개**이며 이미지 토픽을
구독하지 않는다.

## 테스트

```bash
python3 -m pytest test/ -q      # 183 PASS (2026-08-01)
```

## 하지 않는 것

- **개입하지 않는다.** 온도가 높든 팬이 멈췄든 기록·경보만 한다. 자동 감속·안전정지는 별도 ADR 대상.
- **시스템 설정을 바꾸지 않는다.** `nvfancontrol`·`nvpmodel`·커널 thermal 을 읽지도 따르지도 않고,
  쓰지도 않는다.
- **ROS 그래프를 건드리지 않는다.** `ros2 topic hz` 같은 서브프로세스 호출은 매번 새 DDS
  participant 를 만들어 전체 노드에 discovery 트래픽을 유발하므로 금지다. Phase 3 의 토픽 감시도
  이 방법을 쓰지 않는다.

## SW(Software) 이상유무 감시 (Phase 3a)

**선언하지 않으면 아무것도 감시하지 않는다.** 운영 시나리오마다 띄우는 launch 가 다르므로
감시기가 "무엇이 정상인지" 를 스스로 정하지 않는다
(ADR [2026-08-01](../../../docs/adr/2026-08-01-system-health-phase3-sw-watchdog.md) §Decision 2).

설정 파일에 살아 있어야 할 프로세스를 적는다:

```json
"expected_processes": ["nvfancontrol", "python3"]
```

- 선언한 이름이 없으면 → `process_missing` **ERROR**
- 선언한 이름의 PID 가 바뀌면 → `process_restarted` **WARN**
  생존 검사만으로는 죽었다 즉시 살아난 crash-loop 를 못 잡는다. PID 변화가 유일한 단서다.

⚠ 이름은 `/proc/<pid>/stat` 의 `comm` 이라 **15자에서 잘린다**(커널 제약). 긴 실행파일명은
잘린 이름으로 선언해야 한다. 현재 PID 목록이 `process_watch.pids` 에 함께 기록되므로
그 값을 보고 실제 이름을 확인할 수 있다.

**CAN 은 인터페이스가 생기면 자동으로 감시된다** — 이름이 아니라 `type == 280`(`ARPHRD_CAN`)
으로 찾으므로 `can0` 이 아니어도 잡힌다. 없으면 항목 자체를 만들지 않는다(CAN 을 안 쓰는 운영도
정상이다). 에러는 **누계가 아니라 증가율**로 판정한다 — 누계 기준은 한 번 오르면 계속 경보한다.

**아직 못 하는 것**: "노드는 살아 있는데 발행이 멈춘" 상태는 토픽 구독이 필요해 Phase 3a 범위
밖이다. Phase 3b(ROS 브리지)에서만 가능하다.

## 다음 단계

- **Phase 2** — ROS `/diagnostics` 브리지(같은 패키지, `rclpy` 는 그 모듈만).
- **Phase 3b** — 토픽 최신성(헤더 타임스탬프 노후도) — 구독이 필요하므로 브리지 쪽.
- **후속 실험** — 팬 커브 램프 시험(온도 임계 확정), JPEG 장당 크기 실측(디스크 소모율).


## 결과 보기

### 웹 대시보드 (권장)

```bash
python3 -m system_health.webview --log-dir ../../../Log/health          # http://127.0.0.1:8770
python3 -m system_health.webview --log-dir ../../../Log/health --bind 0.0.0.0   # 같은 망에서
```

판정 배너 · 수치 타일 · 추이 차트(온도·CPU·GPU·입력전류·메모리·스왑활동) · 경보표 · 전원 레일표 ·
존별 온도 · 최근 표본표. 5초 자동 갱신, 다크모드 대응.

**읽기 전용이다** — 로그만 읽고 아무것도 제어하지 않으며 POST 를 받지 않는다(테스트로 고정).
**인증이 없으므로** 기본 바인드는 `127.0.0.1` 이고, 외부 노출은 `--bind` 로 명시해야 한다.

화면 갱신 경로(`/api/latest`·`/api/history`)는 로그 **꼬리만** 읽는다. 전체를 파싱하면 로그가
쌓일수록 느려지고 메모리가 분다 — 15.3 MB 로그 실측: 꼬리읽기 36 ms vs 전체파싱 1.03 s.

### 텍스트 보고서

```bash
python3 -m system_health.report ../../../Log/health --interval 5
python3 -m system_health.report ../../../Log/health --interval 5 --since 2026-07-29T00:00
```

표본 결손 · 주기 지터 · 판정 분포 · 경보 집계 · 일자 회전 · 자원 추이 · 로그 성장률을 낸다.
**판정은 하지 않는다** — 수치와 근거만 내고 합격 여부는 사람이 정한다.

`--since` 는 평가 구간을 자른다. 한 폴더에 여러 실행이 누적되면 실행 사이 공백이 결손으로
집계되기 때문이다(실제로 수집률이 23.7 % 로 보인 적이 있고, 구간을 자르면 99.9 % 였다).

## 시험 운전 결과 (2026-07-28 17:47 ~ 07-29 09:47, 16 h)

| 항목 | 결과 |
| --- | --- |
| 자정 파일 회전 | **통과** — 07-28 23:59:58 → 07-29 00:00:03, 결손 0 |
| 프로세스 생존 | 16 h 무중단 |
| 샘플러 RSS | 12.0 → 12.1 MB (증가 없음) |
| 주기 지터 | 평균 5.010 s · 표준편차 0.013 s · 0.5 s 초과 지연 0건 |
| 감시기 CPU | 단일코어 0.20 % (8코어 환산 0.025 %) |
| 로그 성장 | 표본당 약 1.3 KB → 하루 약 22 MB |

시험 운전이 찾아낸 결함 3건은 모두 수정했다 — 첫 표본 CPU% 오탐, 스왑 판정 기준(사용량 →
활동량), 대시보드 전체 파싱.
