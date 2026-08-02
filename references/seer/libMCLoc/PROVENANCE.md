# PROVENANCE — Seer libMCLoc 리버스 엔지니어링(Reverse Engineering) 산출물

보관 규약: [docs/claude_guideline/external_reference/handling.md](../../../docs/claude_guideline/external_reference/handling.md) §1
(루트 `references/<vendor>/<product>/`). 2026-07-31 보관.

## 출처

| 항목 | 값 |
| --- | --- |
| 원본 위치 | `amap-1:/home/amap/Project/Seer_Analysis/docs/reverse_engineering/libMCLoc/` |
| 전송 방법 | amap-1 → 이 장비(`ford-catl-orin-nx`, 100.92.214.74) `rsync`, 2026-07-31 16:40 KST |
| 전송 사유 | 이 장비에서 amap-1 로의 SSH 가 tailnet ACL(Access Control List) 로 차단되어 직접 열람 불가 |
| 분석 대상 | `usr/local/SeerRobotics/rbk/plugins/libMCLoc.so` (172MB, ELF64, not stripped) |
| 대상 버전 | rbk(Robokit) **3.4.5.20** (DWARF(Debugging With Attributed Record Formats) `DW_AT_comp_dir` = `/root/workspace/3.4.5.20/plugins/MCLoc/`) |
| 분석 일자 | 2026-06-24 (심층 분석) · 2026-07-10 (A1 추가 분석, 12에이전트 교차검증) |

## 파일

| 파일 | 내용 | md5 |
| --- | --- | --- |
| `README.md` | 인덱스 · 한 줄 요약 | `59078420bf10b81da09231be9e24256a` |
| `2026-06-24-localization-deep-dive.md` | 마스터 명세 — 아키텍처·자료구조·PF(Particle Filter) 알고리즘·상태머신·배포값·§6.5/§6.6 백로그 해소 | `39fd3cec434282c161e51a8ecaefa9e1` |
| `tuning_parameters.md` | `MCLoc::loadFromConfigFile()` 의 `loadParam` 92개 전수(기본/min/max) | `bda493330ad73c4e20faa037503663d7` |
| `mcl_motion.asm` | **1차 산출물** — `objdump -d --start-address=0x33cb70 --stop-address=0x33f2c0` (모션모델 전 구간: `doParticleMoveAction`·`doExtraMove`·`supplyControlVar`·`setDefaultParams`·`setExtraMoveParams`). 2026-07-31 이 세션이 원본 바이너리에서 직접 생성 | — |
| `donormal_full.asm` | **1차 산출물** — `objdump -d --start-address=0x3ca440 --stop-address=0x3d3240` (`MCLoc::DoNormalUpdateAction` 전체). 업데이트 모드 6개 결정 트리의 근거 | — |
| `loadconfig.asm` | **1차 산출물** — `objdump -d --start-address=0x1ea7c0 --stop-address=0x1f3500` (`MCLoc::loadFromConfigFile`). 파라미터 이름 ↔ 멤버 오프셋 대응의 근거 | — |

## 1차 source 와의 관계 (중요)

**본 폴더의 3개 문서는 1차 source 가 아니라 분석 산출물(2차 자료)이다.**

- 1차 source = `libMCLoc.so` 바이너리 자체 + `robot.param`(SQLite) + `robot.model`. **이 저장소에 없다** (63G 원본 하드는 amap-1 에 연결, 읽기 전용 사용).
- 따라서 본 문서를 근거로 한 주장의 기본 검증 등급은 **ⓦ**(다른 분석 보고, 이 세션이 바이너리 직접 미확인)이다.
  문서 자체가 `[실측 확정]`으로 표기한 항목도, 이 저장소 안에서 재현할 수단(바이너리)이 없으므로 ⓦ 를 넘지 못한다.
- 문서 자신이 §7 에서 한계를 명시한다: 우도식·노이즈 std 등 별도 컴파일단위 산술 세부, `addExternalParticles` 인자 의미,
  전이의 정확한 인과 순서, 메모리 오프셋은 **추론**이다.

## 취급 주의

- 벤더(Seer Robotics) 상용 바이너리의 분석 산출물이다. **원본 바이너리·`robot.param`·맵 자산은 본 폴더에 포함하지 않는다.**
- 외부 공개·재배포 전 라이선스 검토 필요(handling.md §5).

## 파생물

- 대조 분석: [docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md](../../../docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md)
- 재구현: [src/Navigation/](../../../src/Navigation/) (mcl2d_core · mcl2d_map · mcl2d_ros2), [Tools/mcl2d_standalone/](../../../Tools/mcl2d_standalone/)
