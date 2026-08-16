# odom 관련 파일 주석 전면 재작성

## 무엇을

오도메트리를 **생산**하거나 **소비**하는 파일 17개의 주석을 걷어내고 `conventions.md §4`
(주석은 현재 코드의 사실만 · why 를 적는다 · 이력 금지 · 낡은 주석은 삭제·교정)에 맞춰 다시 썼다.
코드는 한 줄도 바꾸지 않았다.

| 구분 | 파일 |
| --- | --- |
| 오도 소비(측위) | `mcl2d_core/{types,motion_model,particle_filter,skid_detector}.{hpp,cpp}` · `mcl2d_core/test/test_motion_oracle.cpp` · `mcl2d_standalone/mcl2d_localizer.{hpp,cpp}` · `mcl2d_ros2/{conversions.hpp,mcl2d_localization_node.cpp}` |
| 오도 생산 | `motor_control/driver_node.py`(실기 휠 오도) |

시뮬 오도(`trnav_2ws_gazebo/scripts/wheel_odometry.py` · `translate_sim_odom`)도 함께 재작성했으나,
Gazebo·SIL 인프라는 이 세션 목적(Seer 원본 odom 분석·이식본 정합) 밖이라
`session/5466b21a-simgeom` 브랜치로 분리했다.

## 왜

잘못된 주석이 기술·이해 부채를 키운다는 지적. 실제로 재작성 중 **코드와 어긋난 서술**이 나왔다:

- `particle_filter.hpp` — 파이프라인을 "predict(균등산포 모션)" 이라 적었으나 predict 는 **결정론**이고
  산포는 `extraMove` 소관이다.
- `mcl2d_localization_node.cpp` — 헤더에 "발행: TF(map→base_link)" 라 적었으나 실제 발행은 **map→odom** 이다.
  (map→base_link 를 내면 부모 중복이 된다는 설명이 같은 파일 아래쪽에 있는데도 머리말이 반대였다.)
- `translate_sim_odom_node.hpp` — `trnav_msgs::WheelSetArray` 로 인용했으나 실제 소속은 `trnav_msgs::msg`.

## 규칙 적용에서 정한 것

- **날짜·이력 서술 전면 제거.** 인용은 낡지 않는 것만 남겼다 — 원본 심볼·주소, `robot.param` 키, debt id.
  날짜가 박힌 문서 경로 인용도 뺐다(경로가 곧 날짜라 게이트에 걸리고, 문서가 옮겨지면 낡는다).
- **감사 흔적 제거.** "오라클 400/400 비트 일치" 같은 측정 집계는 문서 소관이고, 코드에는
  "둘 중 하나만 쓰면 원본과 비트가 갈린다 — 지우지 말 것" 처럼 **다음 사람이 지키게 하는 문장**만 남겼다.
- **미판정은 지우지 않고 형태만 바꿨다.** `initialpose` 의 `prev_odom_` 리셋 여부, 부호·매핑 3건,
  조향 counts/° 의 순환 측정 문제는 전부 "확정으로 인용하지 말 것" 으로 유지했다.

## 검증

- 주석 게이트 패턴(날짜·값 변천 화살표·버전 태그·이력 서술어) 파일 전체 스캔: **33건 → 0건**
- `Tools/comment_check --checks anchor,path,symbol,const,history`: 대상 6경로 **불일치 0건**
  (착수 시 10건 — `path` 1 · `symbol` 1 · `history` 8)
- 주석 외 변경이 없음을 기계 확인: C++ 은 주석 제거 후 토큰 대조로 **전 파일 동일**,
  Python 2개는 모듈 docstring 이 문법상 코드라 `git diff` 로 개별 확인(값·문장 구조 무변경)
- 빌드: `mcl2d_core` · `mcl2d_ros2` · `translate_sim_odom` 통과. 시험: core 3/3 · standalone 2/2

## 남긴 것

- **debt-102** — 슬립 감지의 전제(`/odom` 이 휠 오도여야 함)가 런치 구성에 따라 무너진다. 주석에만 적었고 가드는 없다.
- **debt-103** — 주석 규율이 기계 강제되지 않는다. 훅은 신규 추가분만 보고, 파일 전체 스캐너는 임시 스크립트뿐이다.
- 저장소의 나머지 트리는 손대지 않았다 — 요청 범위(odom) 밖이다.
