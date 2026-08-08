# Seer AMR 네트워크 접근 가이드 (Big-AMR)

> 이 PC(Big-AMR 온보드 컴퓨터)에서 Seer AMR 컨트롤러에 접속하는 방법.
> **실측 확인 기준일: 2026-07-25** (`ping`/포트/ARP/서브넷 스윕으로 검증).

## 결론 요약

- **Seer 접근은 무선(WiFi, `wlan0`) 전용.** ~~Seer 설정이 WiFi 로 되어 있어 유선으로는 잡히지 않는다.~~
  - **2026-07-27 정정(원인 단정 → 관측 서술):** 관측된 사실은 "**이 PC 의 유선 세그먼트(eth0/eth1)에서 Seer 가 ARP 응답하지 않는다**"(2026-07-25 관측)까지다.
    Seer 컨트롤러 자체의 네트워크 설정은 **미확인** — 본 문서 어디에도 Seer 측 설정 화면·설정파일 인용이 없고(`:4` 는 `ping`/포트/ARP/서브넷 스윕만 열거),
    같은 문서 `:69`(향후 조치) 가 "Seer 유선 IP/대역을 **확인** →" 이라고 적어 유선 설정이 아직 확인되지 않았음을 스스로 인정한다.
    판정에 필요한 것: Seer(Roboshop/컨트롤러) 네트워크 설정 화면 또는 설정파일 원문.
- Seer 컨트롤러: **`192.168.44.82`**, MAC `64:d6:9a:bf:4d:4d`, `wlan0` 에서만 ARP 응답.
- 이 PC `wlan0`: `192.168.44.30/24`, 게이트웨이 `192.168.44.1` — 같은 44 서브넷 직결.

## Seer API 포트 (Roboshop / SDK)

| 포트 | 용도 |
|------|------|
| 19204 | Status API (상태 조회) |
| 19205 | Control API (제어) |
| 19206 | Navigation API (내비게이션) |
| 19207 | Configuration API (설정) |
| 19301 | Push data (실시간 푸시 스트림) |

## 접근 확인 절차 (복붙용)

```bash
# 1) 도달성 (무선)
ping -c3 192.168.44.82

# 2) 라우팅이 wlan0 로 가는지 (정상: dev wlan0 src 192.168.44.30)
ip route get 192.168.44.82

# 3) Seer API 포트 열림 확인
for p in 19204 19205 19206 19207 19301; do
  timeout 2 bash -c "echo > /dev/tcp/192.168.44.82/$p" 2>/dev/null \
    && echo "port $p: OPEN" || echo "port $p: closed"
done
```

정상 상태: `ping` 0% loss(무선 ~5~30ms), `ip route get` 이 `dev wlan0 src 192.168.44.30`, 포트 5개 전부 OPEN.

## ⚠️ 함정 — eth0 에 44 대역 IP 를 붙이지 말 것

유선 포트(eth0)에 `192.168.44.30/24` 를 추가하면 `wlan0` 와 **중복 IP** 가 되어, 커널이 `192.168.44.82` 트래픽을 eth0(물리적으로 Seer 망에 연결 안 됨, ARP FAILED)로 보낸다 → **무선 Seer 접근까지 끊긴다** (`Destination Host Unreachable`).

**증상**: 기본 `ping` 은 `Destination Host Unreachable`, `ping -I wlan0` 만 성공.

**복구**:
```bash
sudo ip addr del 192.168.44.30/24 dev eth0
# → 라우팅이 wlan0 로 복귀, ping·API 포트 정상화
```

"유선으로 44 맞추면 된다"는 오해였다 — eth0 는 Seer 망에 물려 있지 않다.

## 유선 포트 현황 (참고)

| 포트 | 대역 | 물린 장비 | Seer 도달 |
|------|------|-----------|:---:|
| `wlan0` | 192.168.44.30/24 | 44 대역(게이트웨이 44.1, Seer 44.82 등) | ✅ 유일 경로 |
| `eth1` | 192.168.192.10 (⚠ 조건부, 아래 주석) / 192.168.1.102 | SICK 라이다 2대(`192.168.192.100/101`, MOXA 경유) — 라이다 전용 | ❌ (ARP 실패) |
| `eth0` | 150.150.50.50/24 | 없음(이웃 0, 죽은 링크) | ❌ (ARP 실패) |

> **⚠ 2026-07-27 조건 병기 — `192.168.192.10` 은 "현황"이 아니라 비영속 수동 추가 주소다.**
> - 이 주소는 손으로 붙였다 뗀 것이며 재부팅 시 소멸한다. 원문:
>   `docs/user_instructions/session_log.md:225` (2026-07-25 14:14) — `sudo ip addr add 192.168.192.10/24 dev eth1`,
>   `sudo ip route add 192.168.192.101/32 dev eth1` (주석: "tailscale /24보다 우선").
> - **2026-07-27 현재 미설정**: `ip -br addr` → `eth1 UP 192.168.1.102/24` (192.168.192.10 없음).
> - 또한 `ip route` → `192.168.192.0/24 dev tailscale0` — 라이다 대역이 eth1 이 아니라 **tailscale0 가 선점**한다.
> - 라이다 드라이버는 이 주소를 요구한다: `src/Sensors/Lidar/2D/sick_safetyscanners2/launch/sick_safetyscanners2_launch.py:15,43` → `"host_ip": "192.168.192.10"`.
> - **따라서 라이다 사용 전 매번 `ip addr add 192.168.192.10/24 dev eth1` + 센서별 `/32` 라우트 강제가 필요하다.**
>   (주소 값 자체는 변경하지 않았다 — 조건만 명시.)
>
> **✅ 2026-08-07 해소 — 「매번 필요」는 더 이상 성립하지 않는다** (위 원문 무변경, 이력 보존)
> NetworkManager 프로파일 `lidar-eth1` 에 주소와 `/32` 라우트가 **영속 기입**됐다. 실측:
> ```
> ipv4.addresses : 192.168.1.102/24, 192.168.192.10/24
> ipv4.routes    : { ip = 192.168.192.100/32, mt = 1 src=192.168.192.10 };
>                  { ip = 192.168.192.101/32, mt = 1 src=192.168.192.10 }
> ipv4.method    : manual        connection.autoconnect : yes
> ```
> `src=` 를 준 것이 핵심이다 — 이것이 없으면 위 §에 적힌 대로 소스 주소가 `192.168.1.102` 로
> 잡히는 불안정이 재현된다. 재부팅 후에도 유지되므로 **수동 `ip addr add` 는 불필요**하다.
> 타 장비 이설 시의 설정 명령은 [docs/lidar/sick_output_channel_setup.md §2-0단계](../lidar/sick_output_channel_setup.md) 참조.

- eth1(MOXA) 세그먼트에는 라이다뿐, Seer 없음. `192.168.192.0/24`·`192.168.1.0/24` 스윕에서 Seer 미검출.
  - **⚠ 2026-07-27 조건 누락 지적 — 위 음성(negative) 결과 중 `192.168.192.0/24` 부분은 eth1 세그먼트에 대한 근거로 쓸 수 없다(미확정).**
    이 결과가 eth1 의 근거가 되려면 스윕 패킷이 실제로 eth1 로 나갔어야 하는데, 그 조건이 문서에 없다.
    2026-07-27 실측 `ip route` → `192.168.192.0/24 dev tailscale0` 이므로 **기본 상태에서 이 대역 스윕은 eth1 이 아니라 tailscale0 로 나간다.**
    실제로 `docs/user_instructions/session_log.md:225` 는 라이다에 닿기 위해 `/32` 라우트를 "tailscale /24보다 우선"으로 강제해야 했고,
    같은 로그의 `ip route get 192.168.192.101` 출력이 `dev eth1 src 192.168.1.102`(src 가 `192.168.192.10` 이 아님)로 나와 인터페이스/소스 선택이 불안정했음을 보여준다.
    스윕 시점의 라우팅 상태·원시 출력은 본 문서에 인용되어 있지 않다.
    **재판정에 필요한 측정**: (1) `ip route get <대상>` 으로 `dev eth1` 확인 → (2) `arp-scan -I eth1 192.168.192.0/24` 원문 첨부.
    (`192.168.1.0/24` 스윕은 `192.168.1.0/24 dev eth1 … src 192.168.1.102` 경로가 상시 존재하므로 별도 조건 없이 유효.)
  - **❌ 2026-08-07 재판정 완료 — 「eth1 세그먼트에 Seer 없음」은 반증됐다.** (위 원문 무변경, 이력 보존)
    2026-07-27 감사가 요구한 측정을 그대로 수행했다: `ping -c1 -W1 **-I eth1** 192.168.192.1~254`
    전수 후 `ip neigh show **dev eth1**`(인터페이스 한정 조회 — tailscale 경유 가능성 배제).
    결과 이웃 6개 중:

    | 주소 | MAC | 정체 |
    | --- | --- | --- |
    | `192.168.192.5` | `e0:27:6c:a8:b3:a9` | **Seer eth0** |
    | `192.168.192.100` / `.101` | `00:06:77:…` | SICK 스캐너 전·후방 |
    | `.4` / `.7` / `.12` | 미상 | 관리 포트 전무(tcp 22·23·80·443·8080 닫힘) |

    MAC 동일성 근거: Seer API `1000`(robot_status_info) 의 `network_controllers` 가
    `eth0 serial e0:27:6c:a8:b3:a9` 를 보고한다 — `192.168.192.5` 의 MAC 과 일치한다.
    **독립 확증**: 스캐너 저장 구성(CoLa 2 Index 177) 의 채널 0 수신 주소가
    전방 `192.168.192.5:6060` · 후방 `192.168.192.5:6061` 이다. 즉 **Seer 는 이 세그먼트에서
    라이다 데이터를 수신하는 당사자**다(판독: `Tools/sick_channel_audit/read_output_channels.py`).
    ⚠ 단 「Seer **API** 가 이 대역으로 열려 있다」는 뜻은 아니다 — `192.168.192.5` 는 ping 에는
    응답하나 `19204`·`19205`·`19207`·`19208` 이 모두 닫혀 있다(2026-08-07 실측). Seer API 접근은
    여전히 무선(`192.168.44.82`)이 경로다. 이 문서 §결론요약의 "무선이 유일 경로"는 **API 에 한해**
    유효하고, 「세그먼트에 Seer 가 없다」는 서술만 폐기한다.
- 라이다 유선 구성 상세는 별도 문서/메모리 참조(SICK 2D lidar 네트워크).

## 유선으로 Seer 를 붙이려면 (향후)

현재 구성에선 무선이 정답. 유선이 필요하면 둘 중 하나:
1. Seer 설정을 다시 유선(MOXA 쪽)으로 전환.
2. Seer 유선 IP/대역을 확인 → 해당 유선 포트를 그 대역에 맞추고, MOXA 가 그 대역을 브릿지하는지(ARP 응답) 확인.

## amap-server (분석 장비) 접근

Seer 리버스 엔지니어링(Reverse Engineering) 자산이 있는 별도 PC. **tailscale 경유**로 접속한다.

> **2026-08-06 정정**: tailscale 호스트명이 `amap-1` → **`amap-server`** 로 바뀌었다(IP 동일).
> 별개 장비 `amap-2`(`100.104.34.12`)와 혼동하지 말 것 — 63G 원본은 `amap-server` 에 있고
> `amap-2` 는 자주 offline 이다. 아래 device 표기도 실측으로 정정했다(`/dev/sda2` → `/dev/sdb2`).

| 항목 | 값 |
|------|-----|
| 호스트 | **`amap-server`** (tailscale IP `100.116.195.65`, 호스트명 `aMAP`) — 구 이름 `amap-1` |
| **계정** | **`amap` 만 허용** — `nvidia`·`kuksauto`·`ubuntu` 는 `tailscale: tailnet policy does not permit …` 즉시 거부 |
| 원본 하드(63G) | **`/dev/sdb2`**(59.1G ext4) → `/media/amap/6ab6980d-f090-4387-8753-a2251e75651d` (Seer AMR 루트파일시스템 전체 사본). 2026-08-06 `lsblk` 실측 |
| (참고) 다른 Seer 이미지 | `/dev/sda3`(LVM 40.4G) → `/mnt/seer_128g_root` 도 마운트돼 있다 — 63G 사본과 별개이므로 경로를 섞지 말 것 |
| rbk 자산 | `<하드>/usr/local/SeerRobotics/rbk/plugins/libMCLoc.so`, `<하드>/usr/local/etc/.SeerRobotics/rbk/resources/params/robot.param`(SQLite) |
| 도구 | `objdump`·`nm`·`readelf`·`python3` 있음. **`sqlite3` CLI 없음** → `python3 -c "import sqlite3"` 사용 |

```bash
ssh -o ConnectTimeout=60 amap@amap-server 'whoami'     # ← 타임아웃을 넉넉히
```

> **⚠ 함정 1 — 첫 접속이 느리다. 타임아웃 15초로는 실패한다.**
> `timeout 15 ssh amap@amap-server` 는 `Terminated`(exit 143)로 끝난다. 이는 **내가 건 타임아웃**이지
> 서버의 거부가 아니다. 같은 시도를 60초로 늘리면 정상 접속된다(2026-07-31 실측).
> 거부(`policy does not permit`)와 타임아웃(`Terminated`)을 같은 결론으로 묶지 말 것 —
> 실제로 그렇게 오독해 "접근 차단" 을 5턴 확정 보고한 사건이 있다:
> [docs/claude-mistake/2026-07-31-001](../claude-mistake/2026-07-31-001_ssh-denial-inferred-from-timeout.md).

> **⚠ 함정 2 — Tailscale SSH 가 주기적으로 브라우저 재인증(check)을 요구한다** (2026-08-06 실측).
> 비대화형 ssh 는 아래처럼 URL 만 출력하고 대기하다 끊긴다 — 이것도 **거부가 아니다**:
> ```
> # Tailscale SSH requires an additional check.
> # To authenticate, visit: https://login.tailscale.com/a/xxxxxxxx
> ```
> 해소: 사용자가 터미널에서 `ssh amap@amap-server` 를 한 번 실행해 그 URL 을 브라우저로 승인하면,
> 이후 일정 시간 동안 자동(비대화형) 조회가 정상 접속된다.

**원본 하드 취급**: 읽기 전용으로만 쓴다(사용자 지시 2026-07-31). 현재 `rw` 로 마운트돼 있으므로
쓰기 명령을 내지 않는 것으로 지킨다. SQLite 파일은 원본을 직접 열지 말고 `/tmp` 로 사본을 뜬 뒤
`file:…?mode=ro` URI 로 조회한다(저널 파일 생성 방지).

---

**변경 이력**
- 2026-07-25: 최초 작성 — Seer 무선 전용 접근 확인, eth0 중복 IP 함정 및 복구법 기록.
- 2026-07-27: 근거-강도 감사 정정(값 변경 없음, 서술·조건만 정정).
  ① `:8` "Seer 설정이 WiFi 로 되어 있어" 원인 단정 → "이 PC 유선 세그먼트에서 ARP 무응답" 관측 서술로 완화(Seer 측 설정 미확인).
  ② 유선 포트 표의 `eth1 192.168.192.10` 은 비영속 수동 추가 주소이며 2026-07-27 현재 미설정임을 병기(`ip -br addr` 실측, session_log.md:225 원문).
  ③ `192.168.192.0/24` 스윕 음성 결과는 라우팅이 `dev tailscale0` 이므로 eth1 근거로 미확정 — 재판정 측정 절차 명시.
- 2026-08-06: §amap-1 → **§amap-server 개칭**(tailscale 호스트명 변경, IP 동일). 실측 정정 — 63G 원본 device `/dev/sda2` → **`/dev/sdb2`**(59.1G ext4, lsblk), 별개 `/mnt/seer_128g_root` 병기, **함정 2(Tailscale SSH 브라우저 재인증)** 신설.
- 2026-07-31: §amap-1(분석 장비) 접근 신설 — 계정 `amap` 전용·타임아웃 함정(15s 실패/60s 성공)·63G 원본 하드 경로·읽기 전용 취급 규칙.
