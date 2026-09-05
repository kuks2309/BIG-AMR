# pgv_ros2 — 코드 변경 이력

## 2026-09-05 — 기동 시 방향 결정 자동 전송 + error 5 자동 복구 (세션 67ed5a48)

- **무엇을**: `pgv_driver_node` 에 파라미터 3개 신설 — `startup_direction`(기본 3=직진, −1=자동 전송 안 함),
  `auto_recover_direction`(기본 true), `direction_retry_period_s`(기본 2.0). 시리얼 개방 직후·**폴링 시작 전에**
  방향 텔레그램을 보내고, 폴링 중 `error_code 5` 를 관측하면 마지막 적용 방향을 재전송한다.
  기동 전송과 `pgv/set_direction` 서비스가 공용 `applyDirection()` 을 쓴다(두 벌 분기 방지).
  `pgv_protocol.hpp` 에 `kErrNoDirection = 5` 상수 추가(Table 5.4).
- **왜**: 이 장치는 전원 인가 후 방향 결정이 없으면 `error code 5` 로 고정되어 위치를 일절 판독하지 않는다
  (매뉴얼 §4.1). 드라이버는 그 명령을 서비스로만 제공해, 재부팅·센서 전원 재인가 때마다 사람이 손으로
  호출하기 전까지 **조용히 계측 불능**이었다. 통신은 20 Hz 정상이라 무응답 경고에도 걸리지 않는다.
  2026-09-05 실기에서 이 상태로 20 cm 사방 태그 탐색을 헛돌렸다(사용자 지적으로 발견).
- **검증(실기, 판다 무관 / /dev/pgv)**:
  | 시험 | 결과 |
  |---|---|
  | `direction 0` 전송으로 오류 재현 | 121 표본 전부 `error=true, error_code=5` |
  | 기본 파라미터 기동 | 로그 `기동 방향 결정: 요청 3 → 적용 3` |
  | 자동 복구 | 잔여 오류 프레임 1건 후 `error code 5 … 방향 3 재전송, 적용 3` |
  | 결과 | `error=false, error_code=0`, 20.0 Hz |
  `colcon build --packages-select pgv_driver` 성공.
- **주의**: 공유 작업트리 사본에는 다른 세션의 미커밋 각도·프레임 보정(`angle_offset_deg`·`frame_rotation_deg`)이
  있다. 실행 중인 드라이버가 그 사본이라 같은 변경을 그쪽에도 적용했고, 그 세션의 코드는 건드리지 않았다.
  본 커밋은 main 기준 워크트리 기준이라 그 보정 파라미터를 포함하지 않는다.
