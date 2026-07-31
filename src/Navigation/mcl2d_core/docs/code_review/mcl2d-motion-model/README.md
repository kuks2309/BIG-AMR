# mcl2d 모션모델 — 코드 리뷰 타임라인

대상: `src/Navigation/mcl2d_core`(motion_model·particle_filter) + 소비자 2곳
(`Tools/mcl2d_standalone` 파사드, `src/Navigation/mcl2d_ros2` 노드).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-07-31](2026-07-31.md) | `cc5e049` + 미커밋 작업트리(파일 md5 9종 고정) | REQUEST CHANGES | High 2 — 정지 판정이 twist 에만 의존(오도 예측 생략 위험) · 모드 5 임계 스케일 미정합 |

- 병기본: `src/Navigation/mcl2d_core/docs/code_review/mcl2d-motion-model/`
- 관련: ADR(Architecture Decision Record) `docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md` ·
  원본 대조 `docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md` · 부채 `debt-031`
- staleness: 리뷰 대상이 **미커밋 작업트리**다. 커밋 후에는 해당 커밋 해시로 재고정 필요.
