# amap-2 → Ford-CATL-orin-nx 이식 가이드 (CAN relay 도킹 킷)

> 작성 2026-07-25. amap-2 필드 PC를 **NVIDIA Jetson Orin NX**(`Ford-CATL-orin-nx`, tailscale `100.92.214.74`, 계정 `nvidia`)로 교체·이식.
> 새 세션에서 이 문서만 보고 이식을 완료할 수 있도록 정리.

## 0. 대상 환경 진단 (2026-07-25 실측)
| 항목 | 값 |
|---|---|
| 접속 | `ssh nvidia@100.92.214.74` (tailscale, 재인증 불요 확인) |
| 아키텍처 | **aarch64** / Ubuntu 22.04 (Tegra) |
| Python | 3.10.12 |
| 판다 USB | **미연결**(하드웨어 이설 필요) |
| `usb1`(libusb1) | **미설치** |
| `python-can` | 미설치(벤치용, 현장 선택) |
| panda udev | **없음**(추가 필요) |
| ⚠ 시계 | RTC/NTP 미동기(1970 epoch) — 로그 타임스탬프·인증서 주의, 필요시 시간 동기 |

## 1. 이식 대상 (소스 = amap-2 킷)
`amap-2:~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit/`
- `panda/`(순수 python lib, aarch64 OK) · `panda.bin.signed`(STM32 펌웨어, 아키텍처 무관 — 그대로 사용)
- `flash_panda.py` · `docking_drive.py`
- `amap2_canhealth.py` · `amap2_canhealth_watchdog.py` · `amap2_monitor.py`
- `seer_gate_bench.py` · `docking_scenario_bench.py`
- `PINMAP.md` · `RUNBOOK.md` · `HANDOFF-amap2.md`
> 본 저장소 `Tools/docking_field_kit/` 와 동기 — 여기서 복사해도 됨.

## 2. 이식 절차

### 2-1. 킷 복사 (amap-2 → orin-nx, 또는 로컬 → orin-nx)
```bash
# 예: 로컬 PC 경유(양쪽 tailscale). orin-nx에 Project 폴더 존재 확인됨.
ssh nvidia@100.92.214.74 'mkdir -p ~/Project/CAN-Relay/docking_field_kit'
# scp -r <킷경로>/* nvidia@100.92.214.74:~/Project/CAN-Relay/docking_field_kit/
```
(scp -r 로 panda/·*.py·*.signed·*.md 전부. __pycache__ 는 제외 무방.)

### 2-2. 의존성 설치 (aarch64)
```bash
ssh nvidia@100.92.214.74
sudo apt update && sudo apt install -y libusb-1.0-0        # 시스템 libusb
pip3 install --user libusb1                                # python usb1
# (PCAN 벤치도 쓸 경우) pip3 install --user python-can
```

### 2-3. udev 규칙 (⚠ bootstub 포함 — amap-2 교훈)
```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="bbaa", MODE="0666"' | sudo tee /etc/udev/rules.d/12-panda-all.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```
> **반드시 vendor 전체(idProduct 지정 X)** — `ddcc`(앱)만 주면 bootstub(`ddee`) 플래시가 권한거부로 실패한다(amap-2에서 겪은 함정).

### 2-4. 판다 하드웨어 이설
- 판다(#2, `1e003e...`, 우리 펌웨어)를 amap-2에서 빼서 **orin-nx USB**에 연결.
- 12V 전원·CAN 배선 유지. **⚠ 종단: Seer 끝 120Ω 필수(60Ω)** — 이게 이번 CAN 단절오류의 근본원인이었음(아래 §4).

### 2-5. 검증
```bash
cd ~/Project/CAN-Relay/docking_field_kit
lsusb | grep bbaa                       # 판다 인식(bbaa:ddcc)
python3 flash_panda.py                  # ⛔ 기대 버전 정정: 아래 경고 참조 (DEV-26524538-DEBUG 는 구버전)
python3 amap2_canhealth.py 12           # per-bus 에러 0 확인(종단·신호 정상)
# 재발 감시: setsid nohup python3 amap2_canhealth_watchdog.py >~/docking_reliability/wd.log 2>&1 </dev/null &
```

> ## ⛔ [2026-07-27 정정 — 기대 펌웨어 버전 / 동봉 바이너리]
> - `DEV-26524538-DEBUG` 는 **구버전**이다. 기대 버전 = **현행 빌드**이며 그 버전 문자열은
>   `Tools/Can_Relay/panda-firmware/board/obj/version`(현재 `DEV-d98bc1a5-DEBUG`)에 있다.
>   이 문자열은 빌드 시점 git HEAD 로 생성되므로 재빌드 시 바뀐다(`board/SConscript:89-92`)
>   — **문자열을 외우지 말고 그때의 `obj/version` 을 읽어 대조할 것.**
> - 현행 빌드에만 있는 것: 부팅 기본 **250 kbps**(`board/drivers/can_common.h:174-176`
>   `can_speed = 2500U`) + heartbeat 상실 시 릴레이 **fail-open**(`board/main.c:257-258`
>   `set_intercept_relay(false); pc_authority = false;`).
>   근거: `docs/verified_facts/2026-07-27.md` §A-1(수정 후 재검증),
>   `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md` Decision 1·2.
> - **킷 동봉 `panda.bin.signed` 는 2026-07-23 자 구버전**(md5 `d4188e02…` ≠ 현행 `174e136c…`,
>   2026-07-27 확인) — **플래시 금지.** 이 체크리스트를 원문대로 따르면 정상 펌웨어를 "버전 불일치"로
>   판정해 구버전으로 되돌리게 되고, 부팅 기본값이 500 kbps 로 돌아가 **250 kbps 버스를 파괴한다**
>   (verified_facts §A-1).
> - 재플래시가 필요하면 `Tools/Can_Relay/panda-firmware/board/obj/panda.bin.signed` 를 쓸 것.
>   바이너리·상수는 변경하지 않았다(경고만 추가).

## 3. 펌웨어 소스 (참고)
펌웨어는 **amap-1**의 `~/T-Robotics/CAN_Relay/panda/`(브랜치 `can-relay-docking`, upstream commaai/panda 26524538 기반). can_health(0xc3) 포함. 재빌드 필요 시 amap-1에서 `scons -j4 board/` → `board/obj/panda.bin.signed`.

## 4. 반드시 유지할 하드웨어 교훈 (2026-07-24)
- **CAN 종단 = 버스 양 끝 각 120Ω → 60Ω.** 판다는 온보드 종단 없음. **Seer 끝(DB9 2·7번)에 120Ω** 반드시. (누락 시 under-termination 반사 → Seer CAN 버스에러 다발 — ~~실제 사고 원인.~~)
  > **[2026-07-27 조건 보강]** 종단 누락 자체는 실측 근거가 있다
  > (`docs/issues_and_fixes/issues_and_fixes.md:82` — Seer 끝 DB9 2·7 실측 **51.6kΩ 개방**).
  > 다만 **"실제 사고 원인" 이라는 배타적 단정은 유지되지 않는다**: 같은 문서 `:86` 는
  > "그 후로도 간헐 재발하던 Seer CAN 알람의 원인은 **종단이 아니라 판다 부팅 기본 비트레이트
  > 500 kbps** 였다" 로 종결했고, `docs/verified_facts/2026-07-27.md` §A-1 은 비트레이트만
  > 250 으로 정합한 **단일 변수 개입**으로 52106·52111·54022 가 전량 소멸했음을 실증한다.
  > 같은 킷의 `RUNBOOK.md:36-38`(§2 종단 항목) 도 "잔류 오류의 정체는 판다 부팅 비트레이트" 라고 적어 이 문장과
  > 어긋난다.
  > ⇒ **정정: "2026-07-24 시점 진단(종단 개방 실측)" 으로 범위를 한정한다. 이후 같은 증상의
  > 잔류·간헐 재발분은 비트레이트가 원인으로 실증됐고, 두 요인의 기여 분리는 미판정이다.**
  > **종단 60Ω 요구 자체는 그대로 유지한다**(양단 120Ω 필수).
- 클론 핀맵: CAN0 H=pin4/L=pin5, CAN2 **H=pin23**(pin22 死핀)/L=pin24, 12V=pin12·14, GND=pin1·26.
- 도킹(intercept) 시 판다가 세그먼트 안쪽 끝 → 종단 스위칭 별도 설계 필요(상시장착 시 passthrough 과종단).

## 5. 검증 기준(이식 완료 판정)
- [ ] `lsusb`에 bbaa:ddcc, `flash_panda.py` 버전 ~~DEV-26524538-DEBUG~~ → **현행 빌드 `Tools/Can_Relay/panda-firmware/board/obj/version` 과 일치**(2026-07-27 정정 — §2-5 경고 참조. 킷 동봉 `panda.bin.signed`(2026-07-23)로 재플래시 금지)
- [ ] `amap2_canhealth.py` = per-bus 에러 0 (라이브 트래픽 하)
- [ ] 워치독 상주 + 종단 60Ω 실측
- [ ] (실 로봇 연결 시) Seer 알람 로그 무재발

---

## 6. 새 세션 시작 프롬프트 (복붙용)
```
CATL-Ford CAN 릴레이 도킹 킷을 amap-2 PC에서 새 PC Ford-CATL-orin-nx(Jetson Orin NX, ssh nvidia@100.92.214.74, aarch64/Ubuntu22.04/py3.10)로 이식합니다.

먼저 Tools/docking_field_kit/MIGRATION-orin-nx.md 를 읽어줘. 대상 환경은 이미 진단됨: 판다 미연결, usb1/python-can 미설치, panda udev 없음, ~/Project 존재, 시계 1970(RTC미동기).

이식 절차(문서 §2):
1) 킷 복사(amap-2 또는 본 저장소 Tools/docking_field_kit → orin-nx ~/Project/CAN-Relay/docking_field_kit)
2) 의존성: libusb-1.0-0(apt) + libusb1(pip)
3) udev: idVendor==bbaa 전체 0666 (⚠ bootstub ddee 포함 — 안 하면 플래시 권한거부)
4) 판다 하드웨어 이설 + 배선(⚠ Seer끝 120Ω 종단 필수, 60Ω)
5) 검증: lsusb bbaa → flash_panda.py 버전확인 → amap2_canhealth.py per-bus 에러0 → 워치독 상주

각 단계 실행·검증 결과를 보고하고, 실 로봇/실모터 연결·구동 전에는 확인받고 진행해. git 협업 모드 solo. 펌웨어 소스는 amap-1 ~/T-Robotics/CAN_Relay/panda (브랜치 can-relay-docking).
```
```
