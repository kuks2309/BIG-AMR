# PROVENANCE — Seer libOdoCalculator 리버스 엔지니어링(Reverse Engineering) 산출물

보관 규약: [docs/claude_guideline/external_reference/handling.md](../../../docs/claude_guideline/external_reference/handling.md) §1
(루트 `References/<vendor>/<product>/`). 자매 폴더 `../libMCLoc/` 과 같은 형식.

## 출처

| 항목 | 값 |
| --- | --- |
| 원본 위치 | `amap-server:/media/amap/6ab6980d-.../usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so` |
| 원본 하드 | 63G SATA (Seer 실기 사본, **읽기 전용으로만** 접근) |
| 대상 버전 | rbk(Robokit) **3.4.5.20** — DWARF 경로 `/root/workspace/3.4.5.20/plugins/OdoCalculator/` |
| 채취 도구 | [`Tools/seer_re/fetch_odocalculator.sh`](../../../Tools/seer_re/fetch_odocalculator.sh) |
| 아키텍처 | ELF64 x86-64, **not stripped**, `.debug_info` 생존 |

## 파일

| 파일 | 내용 | 상태 |
| --- | --- | --- |
| `caldpose.asm` | `MultiSteersOdometer::CaldPose()` `0x14f300`~`0x14fe80` — 휠 변위·조향각 → (dx, dy, dyaw) | **미채취** |
| `calodocoef.asm` | `MultiSteersOdometer::CalOdoCoef()` `0x14c9f0`~`0x14d690` — 계수행렬 사전 역행렬 | **미채취** |
| `calspeed.asm` | `MultiSteersOdometer::CalSpeed()` `0x14d690`~`0x14f300` — 속도 산출(`vel_rotate` 의 출처) | **미채취** |
| `calpose_abstract.asm` | `AbstractOdometer::CalPose()` `0x15d490`~ — 자세 누적(end-point 회전) | **미채취** |
| `layouts.txt` | `gdb ptype /o` 클래스 레이아웃 5종 | **미채취** |

**미채취 사유**: 원본 장비 `amap-server` 가 오프라인이다(2026-08-23 확인, tailscale
`offline, last seen 55m ago`). 장비 복귀 후 위 채취 도구를 실행하면 이 표의 상태가 채워진다.

## 이 폴더가 있는 이유

앞선 조사에서 `CaldPose` 역어셈블을 임시 디렉터리(`/tmp/.../scratchpad`)에 두었다가
세션 공백 동안 통째로 잃었다. **분석 결론은 문서에 남았으나 근거 원자료가 사라졌다** —
[docs/comparison/seer-odom-production_vs_big-amr_2026-08-07.md](../../../docs/comparison/seer-odom-production_vs_big-amr_2026-08-07.md) §9
의 서술을 뒷받침할 원본이 없는 상태다. 자매 `libMCLoc` 은 `.asm` 을 여기 보존해 그런 일이 없다.

## 1차 source 와의 관계 (중요)

**본 폴더의 `.asm` 은 1차 source 가 아니라 채취물이다.** 1차는 원본 하드의 `.so` 이며,
값·동작을 인용할 때는 그 파일과 주소를 함께 적는다. 재채취로 재현 가능해야 한다 —
그것이 이 폴더의 존재 이유다.

## git 추적

`References/` 는 `.gitignore` 대상이라 `git add -f` 로 명시 추가한다(자매 `libMCLoc` 과 동일).
