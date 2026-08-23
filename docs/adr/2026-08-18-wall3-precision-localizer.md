# ADR 2026-08-18 — 벽 3면 라이다 정밀 측위 (wall_localizer)

- **Status**: Accepted — 2026-08-19 (승인 경위: 사용자 지시 "먼저 측위 개발 부터" +
  "References/Bluebotics 참조" — BlueBotics 매뉴얼 원문 대조를 반영해 착수.
  구현 완료: 코어 ctest 3/3 + 변이 검증 + SIL 스모크 PASS — **실기 미검증**.
  이력: `code_updates/2026-08-19-wall-localizer.md`)

## Context

- 세션 목적: 라이다 정밀 위치 추종. 사용자 확정 범위(2026-08-18 문답):
  1. **스테이션 국소 정밀 위치** — 도킹·정차 지점 앞에서 벽 3면(직선) 기준의 상대 자세
     (x·y·yaw)를 라이다로 추정한다. BlueBotics ANT 가 쓰는 자연 특징(벽) 방식.
  2. 기준 벽 3면은 **수동 YAML 입력**으로 정의한다(티치 캡처는 후보로 남김).
  3. 제어(추종) 결합은 **다음 단계** — LGIT AMR 의 docking_action 을 참조해 별도 진행.
     이번 ADR 은 측위(perception/estimation)만 다룬다.
- 기존 자산 실측:
  - 저장소에 라이다 직선(벽) 추출 코드 없음(2026-08-18 grep 전수 — line 히트는 전부
    카메라 line-follow·MES 라인).
  - 스캔 체인: SICK 전·후 `/scan_front`·`/scan_rear` → `dual_laser_merger` → `/scan_merged`.
  - 2WS 액션 서버들은 `trnav_2ws_core::LocalizationMonitor` 가 `pose_topic`
    (`geometry_msgs/PoseStamped`, 기본 `/robot_pose`, 실기 발행자 미정 = debt-068) 하나를
    구독한다 — 본 측위 노드의 출력을 그대로 소비 가능.
  - 전역 측위(mcl2d)는 파티클 필터라 cm 급 — 스테이션 mm 급 요구와 별개 층.
- Navigation 도메인의 기존 배치 관례: 순수 코어(`mcl2d_core`, colcon 무시·자체 ctest) +
  ROS2 어댑터(`mcl2d_ros2`) 분리. 본 설계도 같은 관례를 따른다.

## Decision

신규 2디렉토리를 `src/Navigation/` 에 만든다.

### 1. `wall_localizer_core/` — 순수 C++17 (ROS 의존 0, colcon 무시, 자체 CMake+ctest)

파이프라인 (매 스캔):

1. **전처리** — LaserScan(거리 배열) → 라이다 프레임 2D 점군. 거리 게이트
   `[range_min, range_max]` + 각도 섹터 게이트.
2. **직선 추출** — **split-and-merge** (재귀 분할: 점-직선 최대 수직거리 임계,
   병합: 공선 판정, 최소 점수·최소 길이 게이트). 결정론적·난수 없음 — RANSAC 기각
   (재현성·저장소의 결정론 문화 부합, 점군 수백 점 규모에서 성능 충분).
3. **벽 대응** — 기준 벽 3면을 현재 자세 추정(최초에는 `initial_pose`, 이후 직전 해)으로
   라이다 프레임에 투영 → 추출 선분과 각도차·수직거리차·구간 겹침 게이트로 1:1 최적 대응.
   직선의 π 모호성은 **법선을 관측자(라이다 원점) 쪽으로 정향**해 제거 — 측정 선분은
   원점을 향하게, 기준 벽은 로봇 예상 위치를 향하게.
4. **자세 해석** — 대응 쌍으로 SE(2) 최소자승:
   yaw = 각도 잔차의 가중 원형 평균(가중 = 선분 점수), 이후 병진은
   `n_i · t = Δd_i` 의 2×2 정규방정식. **가관측성 검사** — Σnnᵀ 최소 고유값이 임계
   미만(벽이 사실상 전부 평행)이면 해를 내지 않고 실패 사유 반환.
   대응 벽 ≥ 2(비평행)이면 해석 가능, 3이면 과잉결정으로 잔차 검증력 확보.
5. **품질 판정** — 벽별 점-직선 RMS 잔차·매칭 점수·각도 다양성 → `OK / DEGRADED / LOST`.
   직전 해 대비 점프 게이트. 실패 시 자세를 **발행하지 않는다**(쓰레기 자세 출력 금지 —
   소비자 LocalizationMonitor 의 TIMEOUT/JUMP 감시가 자연 작동).

### 2. `wall_localizer_ros2/` — ROS2 Humble 어댑터 패키지

- 구독: `scan` (`sensor_msgs/LaserScan`, SensorDataQoS/best-effort, 리맵으로 지정 —
  스테이션 벽이 전방이면 `/scan_front`, 필요 시 `/scan_merged`).
- 라이다 외부 파라미터: 첫 스캔의 `frame_id` → `base_link` TF 를 1회 lookup 해 캐시
  (정적 TF 는 `seer_lidar_tf` 가 발행). TF 부재 시 파라미터 `laser_pose_in_base` 폴백.
- 파라미터(YAML): 기준 벽 = **스테이션 프레임 끝점 2개** `walls.<name>: [x1,y1,x2,y2]` (m)
  + `wall_names: [...]` + `initial_pose: [x,y,yaw]` + 추출·대응·품질 게이트 임계.
  전부 `declare_parameter` 명시.
- 발행: `/wall_pose` (`geometry_msgs/PoseStamped`, `frame_id = station_frame` 파라미터,
  **base_link 의 스테이션 프레임 자세** = T_station←base) — 유효 해일 때만.
  `/wall_localizer/diagnostics` (`diagnostic_msgs/DiagnosticArray`) — 벽별 잔차·매칭
  상태·실패 사유 매 스캔.
- 신설 커스텀 인터페이스(.msg) **없음** — 표준 메시지만 사용(공개표면 최소).

### 좌표·단위 규약 (numeric 도메인 §1·§2 고정)

- 내부 단위 **m·rad 단일**, 변환은 경계(파라미터 입출력)에서 1회.
- 프레임 3개: `station`(기준 벽 정의·출력 자세) · `base_link` · 라이다 프레임(스캔 입력).
- 변환 표기·방향: `T_a_b` = "b 프레임의 점을 a 프레임으로" (`p_a = T_a_b · p_b`).
  출력은 `T_station_base`. 회전은 2D 각 1개(yaw) — 쿼터니언은 ROS 경계에서만 생성.
- 직선 표현: 단위 법선 `n` + 부호 거리 `d` (`n·p = d`), 법선 정향 규칙은 위 §3.

### 검증 (never-self-approve — 저자 검증은 §5 전체 회귀까지, 최종 판정은 외부)

- core ctest: ① 합성 스캔 왕복 — 기지 자세에서 벽 3면 스캔 생성 → 복원 오차 무잡음
  < 1 mm·0.05°, 잡음 σ=10 mm 에서 < 5 mm·0.3°. ② 퇴화 — 평행 벽만 → 실패 반환(쓰레기
  자세 금지). 벽 1면 → 실패. ③ split-and-merge 단위(코너 스캔 → 선분 2개 등).
  ④ 변환 왕복 항등(numeric §5). 변이 검증 1건 이상(테스트가 실제로 죽는지).
- `colcon build --packages-select wall_localizer_ros2` + 노드 기동 스모크.
- 실기 정밀도 측정(벽 3면 실 스테이션)은 사용자와 별도 세션 — ros2 도메인 §5 기동
  규율(중복 발행자 게이트) 적용.

## BlueBotics 원문 대조 (2026-08-19 — 전 항목 ✓ 1차 source 직접 확인)

사용자 지시로 `References/Bluebotics/` 의 ANT 매뉴얼 3부를 확인했다. 설계에 반영한 사실:

- ✓ 세그먼트(직선 물체)가 자연 특징 측위의 기본 단위이고 **최소 추출 길이 40 cm** —
  [ANT localization⁺ User Manual R2.6, §D 3.1 Automatic mapping, page 128](<../../References/Bluebotics/ANT localization+ User Manual R2.6 V1.0_EN.pdf>)
  → 본 설계의 직선 추출 `min_length_m` 기본값 0.4 m 로 준용.
- ✓ "vehicle needs only one reference in each direction (X and Y) to be well localized" —
  [같은 문서, §D 3.2.2.1 Good ideas, page 132](<../../References/Bluebotics/ANT localization+ User Manual R2.6 V1.0_EN.pdf>)
  → 본 설계의 가관측성 검사(Σnnᵀ 고유값 = 법선 방향 다양성)와 동일 원리.
- ✓ 항상 같이 보이는 **평행 벽은 하나만 기준으로** 쓰라(같은 기준 사용 보장) — 같은 절, page 132
  → 대응 게이트를 엄격히 하고, 스테이션 YAML 작성 지침에 명기(양측 벽이 대칭·유사거리면
  초기 추정 오차가 게이트를 넘는 순간 교차 오인 위험).
- ✓ **동시 가시 특징 ≤ 5 권장** — 같은 절, page 132 → 벽 3면 구성이 권장 범위 안.
- ✓ 세그먼트가 반사판보다 강건·정밀("segments are preferable over reflectors") — 같은 절,
  page 132 → 반사판 없이 벽만 쓰는 본 설계 방향과 일치.
- ✓ **CAD·도면 이론 좌표로 맵을 만드는 것은 명시적 "Bad idea"** — "Small differences are
  always present in a layout" — [같은 문서, §D 3.2.2.2 Bad ideas, page 132](<../../References/Bluebotics/ANT localization+ User Manual R2.6 V1.0_EN.pdf>)
  → 사용자 결정(수동 YAML)과 상충하는 벤더 경고. 위험으로 명기하고(아래 Consequences ②),
  실측 스캔에서 벽 좌표를 뽑아 YAML 을 채우는 **티치 보정 도구**를 후속 과제로 남긴다.
- ✓ ANT 품질 척도: −1(lost), 0(>±21 cm) ~ 100(<±1 cm) —
  [같은 문서, ANT 통신 절, page 여러 곳(예: 원문 텍스트 2857행)](<../../References/Bluebotics/ANT localization+ User Manual R2.6 V1.0_EN.pdf>)
  → 진단 출력에 잔차 기반 품질을 함께 실을 근거(본 설계는 OK/DEGRADED/LOST + 잔차 수치).
- ✓ 종단 정밀도용 **Adjusted stop**(이중 감속 램프: 미리 감속 후 저속 정속 진입) —
  [같은 문서, §C 5.1.4 Adjusted stop, page 104](<../../References/Bluebotics/ANT localization+ User Manual R2.6 V1.0_EN.pdf>)
  → 2단계(추종 제어, LGIT docking_action 참조 시) 반영 사항으로 기록만 해 둔다.

## Alternatives (기각)

- **RANSAC 직선 추출** — 난수 의존·비결정론, 이 점군 규모에서 이득 없음.
- **mcl2d 융합(전역 보강)** — 범위 과대 + 타 세션이 mcl2d 수정 중(충돌 위험). 사용자 기각.
- **ICP 대(對) 기준 스캔(티치)** — 수동 YAML 결정에 따라 보류. 벽 명시 모델이 잔차 해석·
  진단이 명확.
- **커스텀 .msg 신설** — 공개표면 증가 대비 이득 없음, diagnostic_msgs 로 충분.

## Consequences

- 이득: mm 급 스테이션 상대 측위가 기존 제어 체인(`pose_topic` 리맵)에 무수정 접속.
  전역 측위(mcl2d)와 독립 — 타 세션의 mcl2d 작업과 충돌 없음. 순수 코어라 SIL·단위검증 용이.
- 비용: 신규 코드 2디렉토리 + 함수표·전역변수표 신설(계획 단계 생성, §6 이중 기록).
- 남는 위험: ① 스테이션 벽의 실제 평탄도·반사 특성은 실기 측정 전 미검증.
  ② YAML 수기 벽 좌표의 현장 오차는 사람이 흡수(티치 방식 후보를 후속 부채로).
  ③ 추종(제어) 결합은 미착수 — LGIT docking_action 참조 예정.

## Rollback

N/A (가역) — 신규 디렉토리 추가만, 기존 파일 수정 없음. 되돌림 = 두 디렉토리 삭제.
