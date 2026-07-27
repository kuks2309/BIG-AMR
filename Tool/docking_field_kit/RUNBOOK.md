# 현장 도킹 릴레이 런북 (amap-2) — 2026-07-21 현장용

> 대상: amap-2 + 판다(#2, `1e003e...`, 우리 펌웨어 플래시됨) + 실 Seer + 실 모터.
> 목적: 노드이동(Seer 구동) ↔ 도킹(PC 구동, Seer 속임) ↔ 반환.
> ⚠ 실로봇. 안전구역·E-STOP 상비. 저속부터.

## 0. 킷 위치
`~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit/`
- `flash_panda.py` — 펌웨어 플래시(필요 시)  · `panda.bin.signed` — 펌웨어
- `seer_gate_bench.py` · `docking_scenario_bench.py` — 벤치 검증(PCAN)
- `docking_drive.py` — 실 도킹 드라이버(PC→모터)
- `PINMAP.md` — ⚠ 핀맵(CAN2_H=pin23!)  · `reliability_24h.py` — 내구시험

## 1. 사전 준비 (1회)
```bash
pip3 install --user python-can libusb1      # 이미 있으면 생략
# udev (비루트 USB) — 이미 설정돼 있을 수 있음
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="bbaa", MODE="0666"' | sudo tee /etc/udev/rules.d/11-panda.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## 2. 배선 (⚠ PINMAP.md 준수 — CAN2_H=pin23, CAN0_L=pin5)
```
Seer  → 26핀 CAN0: H=pin4,  L=pin5      ← L은 pin5 권장(pin6도 같은 넷). pin5=릴레이 passthrough 브릿지 지점
모터  → 26핀 CAN2: H=pin23, L=pin24     ← H는 pin23! pin22(死핀) 아님
전원  → 12VIN=pin12/14, GND=pin1/26 에 +12V
```
- 종단: **2026-07-24 해결 완료(Seer 끝 DB9 2–7 에 120Ω 추가 → 전체 60Ω)**. 상시 점검 항목 아님 —
  CAN 오류가 보여도 종단을 원인 후보로 올리지 말 것(2026-07-27 확인: 잔류 오류의 정체는 판다 부팅
  비트레이트 500 kbps 였고 펌웨어에서 250 kbps 로 정정됨). 배선을 새로 손댔을 때만 재측정.
- **pin5 주의**: CAN0_L이며 릴레이 passthrough(fail-safe)의 L 브릿지 지점(pin5↔pin24). Seer L은 pin5에 연결 권장.

## 3. 펌웨어 확인/플래시
```bash
cd ~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit
python3 flash_panda.py         # 버전 DEV-26524538-DEBUG 확인 (이미 맞으면 재플래시 불필요)
# 부트스텁 갇힘 시: python3 flash_panda.py --recover
```

## 4. 도킹 전 게이트 검증 (선택 — PCAN 있으면)
```bash
# can0/can1 250k up 후:
python3 seer_gate_bench.py          # 게이트 T1~T6 (기대 6/6)
python3 docking_scenario_bench.py   # 속임수 시나리오 (기대 6/6)
```
※ 벤치는 PCAN 필요. 실 Seer/모터만 있으면 5단계로.

## 5. 실 도킹 절차 (docking_drive.py)
```bash
python3 docking_drive.py
```
대화형 명령:
| 명령 | 동작 |
| --- | --- |
| `take` | 주도권 PC 취득 (intercept+게이트, Seer 속임 시작) |
| `enable` | 모터 enable (구동 0x86, 조향 0x3F) |
| `f [mmps]` | 전진 (기본 50 mm/s, 저속) |
| `b [mmps]` | 후진 |
| `steer [deg]` | 조향각 (홈 기준) |
| `home` | 조향 홈 + 정지 |
| `s` / `stop` | **즉시 정지 (E-STOP)** |
| `release` | 주도권 Seer 반환 (passthrough) |
| `q` | 종료 (자동 release) |

**권장 순서**: `take` → `enable` → 저속 `f 30`으로 방향 확인 → 도킹 동작 → `stop` → `release`.

## 6. 안전·주의
- **저속부터**(기본 50mm/s, 첫 확인은 30). 방향(전/후·조향)이 예상과 다르면 즉시 `stop`.
- **heartbeat 자동**: docking_drive.py가 죽거나 USB 끊기면 판다가 ~5초 후 fail-safe passthrough(릴레이 OFF) 복귀 → Seer 직결.
- **release 필수**: 도킹 끝나면 반드시 `release`로 Seer에 반환해야 Seer가 다음 노드로 이동.
- **모터 호밍**: 전원 재인가 후 모터 자체 호밍 완료 뒤 enable할 것(호밍 전 명령 시 조향 잠김처럼 보임).
- 조향 부호·노드매핑은 저속 실차 확인 후 신뢰(DirectDriver 실측 기준 이식).

## 7. 문제 시
| 증상 | 확인 |
| --- | --- |
| CAN2/모터 불통 | **핀맵! CAN2_H=pin23** (pin22 死핀) — PINMAP.md |
| 모터 무응답 | 12V 인가? **판다 비트레이트 250 kbps?**(부팅 기본값 — 2026-07-27 펌웨어로 정정) 호밍 완료? *(종단은 2026-07-24 종결 — 후보 아님)* |
| Seer가 "calibrating" 루프 | 게이트 지연 — 벤치 지연 확인. (커널 게이트라 통상 μs) |
| 판다 인식 안 됨 | udev 규칙, USB 재연결, `flash_panda.py --recover` |
| 전진=크랩 | 조향 controlword 매사이클 재전송 확인(드라이버 내장) |
