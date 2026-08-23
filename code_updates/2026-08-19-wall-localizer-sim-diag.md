# 2026-08-19 — wall_localizer 시뮬 평가기에 실패 사유 로깅 추가 + 원인 진단

> 수정 이력의 기록처. 약어: SIL(Software In the Loop)

- 사용자 지시: 2026-08-19 "sil시나리오 실패원인 부터 분석해야지" · "커밋 푸쉬 머지"
- 선행: `code_updates/2026-08-19-wall-localizer-sim.md` (시나리오 결과 — 사유 미기록 상태)

## 코드 변경 — `Tools/wall_localizer_sim/sim_eval.py` (진단 계측만, 측위 코드 무변경)

기존 평가기는 진단 토픽에서 상태(OK/DEGRADED/LOST) **집계만** 하고 사유를 버려서
실패 원인 분석이 불가능했다. `on_diag` 가 스캔별 전체 진단(상태·사유 코드·벽별
matched/잔차/점수·해당 스캔 참값)을 `<시나리오>_diag.jsonl` 로 기록하도록 확장.

## 진단 결과 (동일 시드 재현 — 요약 수치 전 시나리오 기존과 일치, 재현성 확인)

실패 3유형이 **한 뿌리(잡음 토막화 연쇄)** 로 수렴:

1. σ=10mm 대 LOST(S2·S5·S6, 10건)는 전부 `degenerate_normals` — **전방 벽 미대응**
   → 남는 좌·우가 평행 쌍이라 해 거부(거부는 설계 의도). S4 의 LOST 7건은
   `insufficient_matches` — 가용 2면 중 우측 벽 탈락 시 1면 잔존.
2. 탈락 경로: 잡음 봉우리 split → 병합 실패(분할 봉우리 토막은 병합 거리 게이트 밖)
   → 토막이 min_length(0.4m)·겹침비(예측 구간 대비 0.25 — 3m 전방 벽에 가혹) 탈락
   → **1:1 대응이 벽당 토막 1개만 채택**해 나머지 정보 폐기.
3. S7T(σ=20mm 조정판) 최대 오차 48.8mm 는 상태 OK 에서 발생 — 전방 벽이 44점짜리
   **선택 편향 토막**으로만 대응돼 x 축을 단독 결정(front 잔차 0.000 이라 잔차
   게이트로 검출 불가).
4. S7(σ=20mm 기본) 붕괴는 `no_segments` 120 + `insufficient_matches` 179 —
   split_dist(0.03)≈1.5σ 부정합(기존 결론 확정).

## 상태

수정안(벽당 1:N 대응 — matcher/solver/파사드 ~60줄 + 테스트 2케이스) 제시,
**사용자 승인 대기.** 승인·구현·검증 후 `docs/issues_and_fixes/issues_and_fixes.md`
에 [Fix] entry 를 기록한다(issue_fix Step 6).
