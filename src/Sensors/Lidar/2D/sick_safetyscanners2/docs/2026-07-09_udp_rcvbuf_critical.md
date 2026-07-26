# 🔴 중요 — SICK UDP 수신 버퍼 오버플로우 → partial frame → 도킹 제어 오염 (2026-07-09 확정)

> **⚠ 최종 정정 (2026-07-09 21:3x)**: "반쪽 스캔"의 실제 근본 원인은 **타 로봇 /scan_merged 의 무선랜
> 유입**으로 최종 확정 (기하 정지 검정 85mm vs 1106mm — 워크스페이스 experiments/2026-07-09_dock_misdetect_analysis/
> README 참조). 아래 UDP 버퍼 오버플로우 (드랍 559/608 실측) 는 **실재하는 별개 위험**이며 증설 설정은
> 예방 조치로 유지. **DDS 격리 필수**: 본 스택은 `config/cyclonedds.xml` (lo 전용) 을 전 노드에
> `CYCLONEDDS_URI` 로 강제 적용해야 함 — 미적용 노드는 기본 설정(전 인터페이스+멀티캐스트)으로 떠서
> 동일 도메인 타 로봇의 동명 토픽을 수신한다 (검증: `ss -ulpn` 에 IPv4 와일드카드 DDS 소켓 0 개).

> 본 문서는 `experiments/2026-07-09_dock_misdetect_analysis/README.md` (워크스페이스 루트) 의
> **패키지 측 이중화 기록**입니다 (사용자 지시 2026-07-09: "1계층은 매우 중요하므로 라이다 패키지에도
> 중요 문서로 기록 이중화"). 라이다 스택 재설치·이식·새 머신 세팅 시 반드시 함께 적용할 것.

## 증상 (FAILURES #27~#29, 2026-07-09)

- 도킹 접근 중 `/scan_merged` 의 일부 프레임(부하 시 ~8.6%)에서 **한쪽 라이다 기여가 통째로 소실**
  (유효점 1333 → 692, dock 근접 영역 240점 → 9점).
- 파장: dock ROI 점 0개 → perception 고정창 폴백(배경 1.209m) + 카메라 yaw 잔류가 FUSED 로 위장 발행
  → 도착 지점에서 +150mm/s 돌진·전후진 왕복 이상 기동.

## 원인 (소켓 단위 실측 확정)

| 소켓 | 프로세스 | 수신버퍼(rb) | 누적 드랍(d) |
|------|----------|--------------|--------------|
| 0.0.0.0:6060 | sick front | 212992 (208KB, 커널 기본) | 559 |
| 0.0.0.0:6061 | sick rear | 212992 (208KB, 커널 기본) | 608 |
| 기타 DDS 소켓 | — | — | 0 |

- `ss -ulpmn` 실측. 드라이버는 SO_RCVBUF 미설정 (소스 grep 0건) → 커널 기본 208KB 사용.
- 34Hz 고밀도 스트림 + 시스템 부하 (rosbag record·GUI·perception·분석 작업) → 수신 스레드 잠깐 지연
  → 208KB 오버플로우 → UDP 조각 유실 → **드라이버가 부분 조립 프레임(유효점 급감)을 그대로 발행**.
- 무혐의 확인: NIC(enp1s0) 에러 0 (케이블 아님) / merger 코드 (한쪽 empty 시 전체 기각 — 반쪽 생성 불가)
  / 유휴·CPU 단독 부하 라이브 계측 저유효 프레임 0.

## 적용된 대책 (2026-07-09, 시스템 설정 — 재부팅 영구)

`/etc/sysctl.d/99-lidar-udp.conf`:

```
net.core.rmem_max = 8388608
net.core.rmem_default = 2097152
```

- **주의: 기존 소켓엔 미적용 — sick 드라이버 재시작 후 유효** (rb 2097152 확인 필요).
- 새 머신/재설치 시 이 파일부터 복원할 것.

## 재발 점검 명령

```bash
# 소켓 버퍼·드랍 확인 (rb=2097152 이어야 정상, d 증가 = 재발)
sudo ss -ulpmn | grep -A1 -E ':606[01]'
# 커널 UDP 통계 (receive buffer errors 증가 여부)
netstat -su | grep -i "receive buffer"
# 병합 스캔 프레임 건전성 라이브 계측 (90초)
python3 experiments/2026-07-09_dock_misdetect_analysis/live_scan_validity.py
```

## 남은 계층 (2026-07-09 구조안 — 워크스페이스 기록 참조)

- 2계층: perception FUSED 정직성 (ROI 실패 폴백 FUSED 금지 + Hough invalid 시 CAMERA 강등, FAILURES #8)
- 3계층: GUI 비FUSED δh 홀드 / 4계층: rosbag 에 /scan_front·/scan_rear 추가 감시
