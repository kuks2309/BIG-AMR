# libMCLoc.so 리버스 엔지니어링 — 인덱스

rbk(Robokit) 3.4.5.20 위치추정 플러그인 `libMCLoc.so`의 심층 리버스 엔지니어링 산출물.
목적: 리버스 엔지니어링을 통한 Seer 기능(위치추정) 재구현 명세 확보.

| 문서 | 내용 |
|---|---|
| [2026-06-24-localization-deep-dive.md](2026-06-24-localization-deep-dive.md) | **마스터 명세** — 아키텍처·자료구조·PF 알고리즘·상태머신·배포값·재구현 로드맵 (5 facet 통합) |
| [tuning_parameters.md](tuning_parameters.md) | 튜닝 파라미터 92개 전수 (loadParam 디스어셈블, 기본/min/max) |

관련: [구조 분석(sw_structure)](../../sw_structure/slam_localization/2026-06-24.md) — 모듈 배선·클래스·시퀀스.

## 한 줄 요약
MCLoc = **2D Monte Carlo Localization 파티클필터 + 점유-bin 기반 적응 표본수**(개발자 명명 `AdaptiveSampleNumber`; KLD-sampling 계열이나 단순 선형 `n=k×2.5`, 정식 KLD 아님 — `KLD`·`AMCL` 문자열 바이너리에 없음) + 반사판/태그/SLAM/3D/특징 다중 백엔드 상태머신. 격자 likelihood field(가우시안 PDF LUT) 우도를 OpenCL+멀티스레드로 병렬 계산. 오픈소스(Open Karto/ANN/Ceres/PCL) 기반이라 재구현 경로 명확.
