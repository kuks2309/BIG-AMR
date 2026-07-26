# Seer AMR 네트워크 접근 가이드 (Big-AMR)

> 이 PC(Big-AMR 온보드 컴퓨터)에서 Seer AMR 컨트롤러에 접속하는 방법.
> **실측 확인 기준일: 2026-07-25** (`ping`/포트/ARP/서브넷 스윕으로 검증).

## 결론 요약

- **Seer 접근은 무선(WiFi, `wlan0`) 전용.** Seer 설정이 WiFi 로 되어 있어 유선으로는 잡히지 않는다.
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
| `eth1` | 192.168.192.10 / 192.168.1.102 | SICK 라이다 2대(`192.168.192.100/101`, MOXA 경유) — 라이다 전용 | ❌ (ARP 실패) |
| `eth0` | 150.150.50.50/24 | 없음(이웃 0, 죽은 링크) | ❌ (ARP 실패) |

- eth1(MOXA) 세그먼트에는 라이다뿐, Seer 없음. `192.168.192.0/24`·`192.168.1.0/24` 스윕에서 Seer 미검출.
- 라이다 유선 구성 상세는 별도 문서/메모리 참조(SICK 2D lidar 네트워크).

## 유선으로 Seer 를 붙이려면 (향후)

현재 구성에선 무선이 정답. 유선이 필요하면 둘 중 하나:
1. Seer 설정을 다시 유선(MOXA 쪽)으로 전환.
2. Seer 유선 IP/대역을 확인 → 해당 유선 포트를 그 대역에 맞추고, MOXA 가 그 대역을 브릿지하는지(ARP 응답) 확인.

---

**변경 이력**
- 2026-07-25: 최초 작성 — Seer 무선 전용 접근 확인, eth0 중복 IP 함정 및 복구법 기록.
