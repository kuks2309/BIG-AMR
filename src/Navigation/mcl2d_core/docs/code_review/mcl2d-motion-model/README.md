# mcl2d 모션모델 — 코드 리뷰 타임라인

대상: `src/Navigation/mcl2d_core`(motion_model·particle_filter) + 소비자 2곳
(`Tools/mcl2d_standalone` 파사드, `src/Navigation/mcl2d_ros2` 노드).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-07-31](2026-07-31.md) | `cc5e049` + 미커밋 작업트리(파일 md5 9종 고정) | REQUEST CHANGES | High 2 — 정지 판정이 twist 에만 의존(오도 예측 생략 위험) · 모드 5 임계 스케일 미정합 |

**후속 조치 (2026-07-31, 리뷰 직후 · 브랜치 `session/5466b21a`)** — `H1`·`M1`·`M2`·`M4`·`L1` 반영:
정지 판정을 **pose 증분 1차 근거**로 교체(twist 는 dt 부재 시 폴백, 전부 0 인 twist 는 미채움으로 간주) ·
산포 모드 판정에 **누적 기준점**(원본 `accumu` 대응) 도입 · 노드 파라미터 단일 소유 ·
증분 중복 계산 제거 · 조기반환 경로의 `prev_stamp_` 일관 갱신. PF 액션 분리 회귀 테스트 1건 추가(`M3` 부분 해소).
**재리뷰는 미실시** — `H2`(모드 5 임계 스케일 → `debt-031`)와 `M3`(파사드 stopped 경로 테스트) 잔존.
다음 리뷰는 후속 커밋 기준 delta 로 수행할 것.

- 병기본: `src/Navigation/mcl2d_core/docs/code_review/mcl2d-motion-model/`
- 관련: ADR(Architecture Decision Record) `docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md` ·
  원본 대조 `docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md` · 부채 `debt-031`
- staleness: 위 리뷰는 **커밋 `782698a` 직전 작업트리** 기준이다. 후속 수정이 그 뒤에 들어갔으므로
  현재 HEAD 는 리뷰보다 앞선다 — **재리뷰 필요(미리뷰 1커밋)**.
