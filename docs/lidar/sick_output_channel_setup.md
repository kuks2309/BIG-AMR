# SICK 안전 스캐너 출력 채널 설정 — 타 AMR 이설 절차

> **한 줄**: Seer 와 라이다를 공유할 때는 **센서의 UDP 출력 채널을 분리**한다.
> Seer 는 저장 구성의 채널(보통 0)을 쓰고, 우리(PC)는 **저장 구성에서 비어 있는 채널**을 쓴다.
>
> **⚠ 채널 번호를 이 문서에서 복사하지 마라.** 기체마다 다를 수 있다. **반드시 판독 후 고른다.**

작성 계기: 2026-08-07 이 저장소 기체(Foil_A082)에서 우리 드라이버가 채널 0 을 점유해
**Seer 의 라이다가 죽었다.** 전체 경위는
[issues_and_fixes.md](../issues_and_fixes/issues_and_fixes.md) 2026-08-07 항목 참조.

---

## 1. 왜 "설정 복사"가 아니라 "조사 먼저"인가

우리 ROS2 드라이버(`sick_safetyscanners2`)는 기동할 때마다 CoLa 2 `changeSensorSettings()` 로
**센서 쪽 출력 채널의 목적지를 덮어쓴다**(`SickSafetyscanners.cpp:145`). 채널 하나는 목적지를
하나만 기억하므로, 이미 누가 쓰는 채널을 지정하면 **그 수신자를 끊는다.**

끊긴 쪽은 스스로 복구하지 못한다. 실측으로 확인한 성질 3가지:

| 성질 | 근거 |
| --- | --- |
| 우리 노드를 종료해도 센서 설정은 **그대로 남는다** | 노드 0건 상태에서 스캐너가 계속 젯슨으로 204.2 pkt/s 송신 [실측 2026-08-07] |
| Seer 는 설정을 **쓰지 않고 듣기만** 한다 → 재시작해도 못 되찾는다 | `5004 robot_core_restart_req` 후에도 목적지 불변 [실측] |
| 저장 구성은 **전원 재인가**로 복귀한다 | "This configuration is not permanent, i.e. the previously saved configuration will be active again after restarting the device." [8022708/1W29, §6.3.2.2, page 62] |

그리고 **가용 채널 수는 기체마다 다르다** — "The number of available data output channels depends
on the device variant" [8022708/1W29, page 9]. 그래서 조사 없이 번호를 정하면 안 된다.

## 2. 이설 절차

### 0단계 — 준비

PC 를 라이다망에 붙이고 주소를 **영속화**한다. 매번 `ip addr add` 하는 방식은 재부팅에 날아간다.

```bash
# 예: eth1 을 라이다망에 물린 경우 (주소는 기체 대역에 맞춰 바꾼다)
sudo nmcli connection modify <프로파일> \
  +ipv4.addresses 192.168.192.10/24 \
  +ipv4.routes "192.168.192.100/32 mt=1 src=192.168.192.10" \
  +ipv4.routes "192.168.192.101/32 mt=1 src=192.168.192.10"
sudo nmcli connection up <프로파일>
```

`/32` 라우트에 `src=` 를 주는 이유: tailscale 등이 같은 대역에 `/24` 라우트를 올려 두면
라이다행 트래픽이 그쪽으로 새고, 소스 주소도 엉뚱하게 잡힌다. 자세한 함정은
[seer_network_access.md](../network/seer_network_access.md) 참조.

### 1단계 — 센서 찾기

기체마다 센서 주소가 다르므로 이 저장소의 `.100/.101` 을 가정하지 않는다.

```bash
python3 Tools/sick_channel_audit/read_output_channels.py --scan 192.168.192
```

CoLa 2 포트(tcp/2122)가 열린 호스트를 훑어 그대로 판독까지 이어간다.

### 2단계 — 저장 구성 판독 → 쓸 채널 선택 ★핵심★

```bash
python3 Tools/sick_channel_audit/read_output_channels.py <센서IP> [센서IP …]
```

출력의 **저장(saved, Index 177)** 표를 본다.

- **●(활성) 채널** = Safety Designer 로 누군가(대개 Seer)에게 배정된 채널. **절대 쓰지 않는다.**
- **○(비활성) 채널** 중 **가장 낮은 번호**를 우리 채널로 고른다.
- 활성(Index 178) 표는 "지금 실제로 도는 값"이라 우리 런타임 설정이 섞여 있다. **선택 근거로 쓰지 않는다.**

**동시에 반드시 적어 둘 것** — 저장 구성의 **●채널 수신 주소:포트**. 이것이 사고 시 원복값이다.

> **가드가 대신 막아 준다** — 2026-08-08 부터 `sick_safetyscanners2_launch.py` 는 노드 기동 **전에**
> `channel_guard.py` 를 호출해 저장 구성을 읽고, 쓰려는 채널이 이미 배정돼 있으면 **런치를 중단**한다.
> 그래도 2단계는 건너뛰지 마라 — 가드는 "쓰면 안 되는 채널"을 막을 뿐 **어느 채널을 써야 하는지는
> 알려주지 않는다.** 그리고 `--dry-run` 없이 사고가 난 뒤에 아는 것보다 미리 아는 편이 싸다.

### 3단계 — 런치에 반영

[sick_safetyscanners2_launch.py](../../src/Sensors/Lidar/2D/sick_safetyscanners2/launch/sick_safetyscanners2_launch.py)
에서 센서별로 4개 값만 기체에 맞춘다.

| 파라미터 | 의미 | 기체별 |
| --- | --- | --- |
| `sensor_ip` | 센서 주소 | **바뀜** (1단계 결과) |
| `host_ip` | PC 주소 | **바뀜** (0단계에서 정한 값) |
| `channel` | 출력 채널 번호 | **바뀜** (2단계에서 고른 빈 채널) |
| `host_udp_port` | PC 수신 포트 | 우리 쪽 포트라 충돌 대상 아님. 센서마다 다르게만 주면 됨 |

```bash
colcon build --packages-select sick_safetyscanners2
```

### 4단계 — 검증 (양쪽 동시 수신)

**한쪽만 확인하고 끝내지 않는다.** 우리가 받는 것과 Seer 가 받는 것을 **같은 시각에** 본다.

```bash
# ① 우리 쪽
ros2 topic hz /scan_front ; ros2 topic hz /scan_rear

# ② Seer 쪽 — 빔 배열 해시가 계속 바뀌어야 한다 (고정 = 얼어붙음)
#    Seer API 1009(robot_status_laser) 폴링. 알람 1050 도 함께 본다.
```

합격 기준:

| 항목 | 기준 |
| --- | --- |
| 우리 `/scan_*` | 센서 스캔 주기와 일치 (본 기체 34 Hz) |
| Seer 빔 프레임 | **연속 갱신** (해시가 매번 바뀜) |
| Seer 알람 `1050` | `52103 timeout receive laser data …` **없음** |
| 판독 재확인 | 활성 구성에서 ●채널이 Seer·우리 **둘 다** |

### 5단계 — 기록

기체별 실측값을 남긴다. 아래 표를 복사해 채운다.

```
기체명            :
라이다망 대역     :
PC 주소           :
센서 A (전방) IP  :        저장 ●채널:      → 수신자:          우리 채널:
센서 B (후방) IP  :        저장 ●채널:      → 수신자:          우리 채널:
검증일 / 결과     :
```

## 3. 사고 시 원복 — 채널을 잘못 덮어썼을 때

2단계에서 적어 둔 **원래 수신 주소**로 드라이버를 한 번 띄우면 된다. 전원 재인가 불필요.

```bash
ros2 run sick_safetyscanners2 sick_safetyscanners2_node --ros-args \
  -p sensor_ip:=<센서IP> -p channel:=<빼앗은 채널> \
  -p host_ip:=<원래 수신 IP> -p host_udp_port:=<원래 포트>
```

원래 값을 적어 두지 않았다면 **센서 전원 재인가**로 저장 구성을 복귀시킨다
(로봇 전원을 내렸다 올리면 된다). ⚠ 로봇 기동 시 **조향축 재호밍 스윙**이 있으니 주변을 비운다.

## 4. 하면 안 되는 것

- ❌ 저장 구성에서 **●인 채널을 쓰는 것** — 그 수신자가 죽는다.
- ❌ 채널 번호를 다른 기체에서 **복사**하는 것 — 배정이 다를 수 있다.
- ❌ `use_persistent_config:=true` 로 플래시에 쓰는 것 — 전원 재인가 원복 경로가 사라진다.
  (현재 런치는 `False`. 그대로 둔다.)
- ❌ 우리 쪽 수신 Hz 만 보고 "됐다"고 판정하는 것 — Seer 가 죽어도 우리는 정상으로 보인다.

## 5. 안전 관련 — 확인 완료

데이터 출력은 **애초에 안전 기능이 아니다.** 채널을 늘리는 것은 안전 출력(OSSD, Output Signal
Switching Device)과 무관하다.

> DANGER — "Data output may only be used for general monitoring and control tasks.
> → Do not use data output for safety-related applications."
> [Data output via UDP and TCP/IP 8022708/1W29, §2.1 page 6 · §4 page 9]

> "This data is used in particular for providing navigation support for AGVs (automated guided
> vehicles). This data is **not intended for use in safety-related applications**."
> [nanoScan3 I/O Operating Instructions 8024596/1W27, page 94]

채널 번호 범위는 **0…3**(최대 4채널)이며 채널별 설정은 독립이다
[8022708/1W29, Table 73 §6.3.2.2 page 62 · 8024596/1W27 page 94].

## 6. 1차 source

⚠ **`References/` 는 `.gitignore` 대상이다**(`.gitignore:12`). 즉 이 저장소를 clone 한 타 장비에는
**PDF 가 없다.** 아래 공식 URL 로 같은 자리에 다시 받는다(이설 0단계에서 함께 수행할 것).

```bash
mkdir -p References/sick/nanoscan3 && cd References/sick/nanoscan3
curl -sSL -A "Mozilla/5.0" -o technical_information_data_output_udp_tcpip_en_im0083701.pdf \
  https://www.sick.com/media/docs/1/01/701/technical_information_microscan3_outdoorscan3_nanoscan3_data_output_via_udp_and_tcp_ip_en_im0083701.pdf
curl -sSL -A "Mozilla/5.0" -o operating_instructions_nanoscan3_io_en_im0087137.pdf \
  https://www.sick.com/media/docs/7/37/137/operating_instructions_nanoscan3_i_o_en_im0087137.pdf
file *.pdf                                   # PDF 매직바이트 확인 (차단 페이지가 아닌지)
for f in *.pdf; do pdftotext -layout "$f" "${f%.pdf}.txt"; done
```

인용에 쓴 문서·판본(페이지 번호는 이 판본 기준):

| 문서 | 판본 | 로컬 경로 |
| --- | --- | --- |
| microScan3 / outdoorScan3 / nanoScan3 — Data output via UDP and TCP/IP | `8022708/1W29/2026-05-26` | `References/sick/nanoscan3/technical_information_data_output_udp_tcpip_en_im0083701.pdf` |
| nanoScan3 I/O Operating Instructions | `8024596/1W27/2026-05-26` | `References/sick/nanoscan3/operating_instructions_nanoscan3_io_en_im0087137.pdf` |

⚠ SICK 문서는 개정된다(표지에 "SUBJECT TO CHANGE WITHOUT NOTICE"). 받은 판본이 위와 다르면
**페이지 번호가 어긋날 수 있으니** 인용 문구를 검색해 위치를 다시 확인한다.

## 7. 이 저장소 기체 실측값 (Foil_A082) — 참고용, 복사 금지

센서 `NANS3-CAAZ30AN1P02`(nanoScan3), 펌웨어 `R01.66`. 판독 2026-08-07.

| 센서 | 저장(177) 채널 0 | 저장 채널 1·2·3 | 우리 채널 | 우리 수신 |
| --- | --- | --- | --- | --- |
| `192.168.192.100` 전방 | ● `192.168.192.5:6060` (Seer) | ○ 전부 비활성 | **1** | `192.168.192.10:6060` |
| `192.168.192.101` 후방 | ● `192.168.192.5:6061` (Seer) | ○ 전부 비활성 | **1** | `192.168.192.10:6061` |

검증 2026-08-07 22:0x — 우리 `/scan_front` 34.02 · `/scan_rear` 34.03 · `/scan_merged` 37.90 ·
`/odom` 34.01 Hz, 동시각 Seer 빔 갱신 3/3 · confidence 0.658 · 알람 없음. **양쪽 동시 수신 확정.**

## 8. 도구 사용 시 알아 둘 함정 (실측)

- CoLa 2 세션 개설의 `ClientID` 는 **정확히 4바이트**여야 한다. 문서는 "bytestream" 이라고만 적어
  길이를 명시하지 않는데, 실기는 5바이트 ASCII(American Standard Code for Information Interchange)
  에 `0x000E FLEX_OUT_OF_BOUNDS`, 생략 시 `0x0008 BUFFER_UNDERFLOW` 로 거부했다.
- **저장(177)과 활성(178)의 채널 stride 가 다르다** — 저장 24바이트(Table 63), 활성은 파생값이
  붙어 **48바이트**(Table 66). 24 로 통일해 읽으면 활성 구성이 채널 8개로 잘못 쪼개진다.
  도구는 나머지 바이트가 남으면 예외를 던져 이 오독을 막는다.
