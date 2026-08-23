# 2026-08-23 — 학습된 기준 직선의 RViz2 시각화 (MarkerArray)

- 사용자 지시: "rviz2 에 학습된 직선을 맵 위에 그려줄 수 있을까요?"

## 변경 (wall_localizer_ros2)

- `publishWallMarkers` 신설 — 매 스캔 기준 벽을 `wall_localizer/wall_markers`
  (visualization_msgs/MarkerArray)로 발행. 스테이션 프레임은 TF 트리에 없으므로
  **현재 해(LOST 면 직전 해)의 역변환으로 base_link 프레임에 그린다** — RViz 고정
  프레임이 map 이어도 TF(map→odom→base_link)를 타고 물리 벽 위에 겹친다.
  색: 매칭=오렌지(사용자 지정), 미매칭=빨강, LOST=회색. 선폭 0.08 m(맵 줌 가시성 — 0.03 은 1픽셀 미만, 실기 확인). 벽 이름+대응 점수 텍스트 라벨 동반,
  lifetime 0.5 s(노드 정지 시 잔상 소멸).
- 의존 추가: visualization_msgs (package.xml·CMakeLists)

## 검증

- colcon 빌드 성공. 실기 구동에서 `wall_localizer/wall_markers` 발행 확인 —
  walls/wall_labels 네임스페이스, `board (114pt)` 라벨, `/wall_pose` 34 Hz 동시 정상.
- RViz 표시법: Add → MarkerArray → topic `/wall_localizer/wall_markers`
  (고정 프레임 map 권장 — mcl2d 뷰 위에 겹쳐 보임)
