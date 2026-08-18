# seer-slam-mapping — 코드 리뷰 타임라인

Seer legacy 지도생성(SLAM 매핑) 원본 파이프라인 + `slam_karto_core` 이식 대상 리뷰.

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-08](2026-08-08.md) | 원본 rbk 3.4.5.20 (`libSlaMapping.so` md5 `a925b68b…`) / 이식대상 `8ffd07d` (sha256 고정) | REQUEST CHANGES | High 4 (assert 컴파일아웃 퇴행 · 정보행렬 무가드 · `slam_karto_ros2` 빈 껍데기 · 라이선스 LGPL-3.0 오기) |

## 2026-08-09 — 원본 직접 구동 오라클 대조 (본문 §3차 정정)

원본 `libSlaMapping.so` 를 `dlopen` 으로 직접 구동해 실 로그로 대조했다. **정적 분석이 못 잡은 이식본 결함 4건**을 잡았고
(그중 2건은 리뷰 findings 를 반영하며 우리가 만들어 넣은 것), 2차 역어셈블 판정 1건이 반증됐다.

| 항목 | 결과 |
| --- | --- |
| 스캔 채택 판정 · 점군 개수 | **완전 일치** (213/213 · 81,948) |
| 포즈 위치차 | max **0.024 m** · mean **0.0090 m** |
| 포즈 방위차 | max **0.0036 rad**(0.21°) · mean **0.00099 rad** |

설계: [`../../adr/2026-08-09-seer-karto-oracle-harness.md`](../../adr/2026-08-09-seer-karto-oracle-harness.md) ·
도구: `Tools/seer_rawmap/replay/`

## 산출물

| 파일 | 내용 |
| --- | --- |
| `2026-08-08.md` | 리뷰 본문 (Core 인벤토리 5항목 + ros2/concurrency 도메인 + severity 평가) |
| `2026-08-08-flow.drawio` | 흐름도 ① 원본 rbk 파이프라인 (박스 25 · 화살표 26, dangling 0) |
| `2026-08-08-flow-port.drawio` | 흐름도 ② 이식본 `slam_karto_core` (박스 16 · 화살표 18, dangling 0) |

## 패키지 병기

이식 완료 후 `src/Navigation/slam_karto_core/docs/code_review/seer-slam-mapping/` 에 동일 내용을 병기한다.
리뷰 시점에는 대상 패키지가 본 저장소에 없어 루트 정본만 존재했다
(`ls src/Navigation/` → `mcl2d_core mcl2d_map mcl2d_ros2 seer_pose_publisher icp_odometry_bringup docs README.md`).

## 관련 문서

- 인접 리뷰: [`../mcl2d-localization-chain/2026-08-07.md`](../mcl2d-localization-chain/2026-08-07.md) — 위치추정 체인.
  `map→odom` TF 소유권(H1)이 본 리뷰의 TF 충돌 Info 항목 근거.
- 회수 자산: `References/seer/slam_mapping/{proto,rawmaps,maps}` (`.gitignore:12` 로 미추적)
