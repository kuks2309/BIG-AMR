# 2026-09-02 — wall_localizer → feature_localizer 전면 개명

결정·매핑·경계는 docs/adr/2026-09-02-feature-localizer-rename.md 가 정본.
요지: 실운용 기준면이 벽이 아닌 임의 직선 특징점(2026-08-28 실기 티치 σ 0.5 mm)
이라 이름을 실체에 맞춤. 패키지 2종·노드·토픽(/feature_pose)·파라미터
(feature_names·features.*)·코어 심볼(Feature*)·티치 도구/자산·SIL·dock 적응층
(featurePoseToDockObs)·UI 스택을 일괄 개명(46파일 치환 + git mv, 잔존 식별자
0건). LGIT 이식 코어(dock_core)·golden 과 과거 문서 표기는 불변. 검증:
colcon build(up-to dock_ros) + 단위시험 + py_compile. 로봇 워크스페이스는
pull + 일괄 재빌드 필요(부분 pull 금지).
