# 2026-08-26 — 왕복 주행 실기 테스트 구동 UI 신설 (Tools/drive_test_ui)

- 사용자 지시: "최대 1.0 m/s·감속 0.3 m/s² 10왕복 실기 테스트용 구동 UI — 탭 2개,
  첫 탭은 패키지 구동 버튼" + "버튼은 실행과 중지로".
- 사전승인·인벤토리: docs/code_review/drive-test-ui/2026-08-26.md (계획 함수표 선작성).
- 구성: PyQt5 단일 파일. 탭① 상주 9종(측위 브링업(rviz:=true 로 RViz2 동시 기동, DISPLAY 보장)·브리지·IMU·PGV·can_relay·mux·
  translator·전/후진 서버 — smap 마커(seer_map_viz) 사용자 지적으로 추가, 총 10종) 실행/중지+상태 램프+전체 순차 실행, 단발 3종(engage·
  호밍(스윙 경고 확인)·disengage — PGV 방향설정 버튼은 사용자 지시로 제외), 로그 뷰. 탭② 확정 구성(사용자 지시): 위 그룹박스 = 노드 A↔B 실시간 로봇 위치 그래프
  (TrackGraph, 시간×경로위치 스크롤 곡선+노드 기준선, QPainter 직접 묘화), 아래 그룹박스
  왼쪽 = 도착 시 PGV 위치 2차원 산포도(PgvScatter, 1 mm 격자원·공차 3 mm 원·회차 라벨),
  오른쪽 = 실험 조건(1.0/0.3/6.0 m/10회)·실행/중지·상태. 도착 이벤트는 후진 레그 종료 시
  태그 검출이면 sig_arrival 로 산포도에 적재, jsonl 기록 유지.
- 안전: 실험은 /robot_pose·액션 서버 부재 시 시작 거부, 중지=goal cancel,
  E-STOP 비대체 명시. 종료 시 상주 정리 여부 선택.
- 검증: py_compile OK · 오프스크린 기동+rclpy 워커 스핀 OK · 데스크톱 기동 확인(창 표시).
  실기 왕복은 사용자 입회 실험에서.

## 추가 — 이중 기동 방지 (같은 날 후속)

구 UI 강제종료 시 자식(별도 프로세스 그룹)이 잔존한 상태에서 새 UI 로 재기동해
스택 전체가 2중(일부 4중) 기동, mcl 2벌이 /mcl_pose 를 다퉈 측위 불안정 발생 —
전수 정리로 해소. 재발 방지로 ProcManager.start 에 시스템 전역 중복 검사
(marker: launch 파일명/실행 파일명 pgrep) 를 추가, 중복 시 "기동 거부" 로그.
respawn 부모(launch) 잔존이 자식 정리를 되돌리는 함정도 확인(부모 우선 종료).

## 추가 — 종료 확실화 (같은 날 후속, 사용자 지시)

stop() 을 그룹 SIGINT→SIGTERM→SIGKILL 3단 에스컬레이션으로, stop_all() 은 개별 정지 후
marker 기반 전역 잔존 소탕(pkill → 확인 → pkill -9)으로 보강 — respawn/이탈 자식 포함
확실 종료. 함수표 동반 갱신.

## 추가 — kill all 버튼 + 고아 자식 소탕 (같은 날 후속, 사용자 지시 "kill_all_node 방식")

- 탭① 에 "전체 중지 (kill all)" 버튼(확인 후 stop_all) 신설.
- 사고 재현 분석: UI 교체(강제종료) 시 이전 UI 의 bringup launch 부모가 고아(ppid=1)로
  살아남아 respawn 자식을 되살림 — 소탕 목록에 launch 부모 패턴들과 자식 노드 실행 파일
  목록(EXTRA_KILL_MARKERS)을 추가해 고아·respawn 포함 확실 종료.

## 추가 — 버튼 배색 (같은 날 후속, 사용자 지시)

STYLE_RUN(초록)/STYLE_STOP(빨강)/STYLE_KILL(진빨강)/ONESHOT_STYLES(engage 파랑·
호밍 주황·disengage 회청) 상수로 전 버튼 일괄 배색 — 탭①·② 공통.

## 추가 — 탭② 상단 그래프를 x·y 평면 뷰로 (같은 날 후속, 사용자 지시)

TrackGraph 를 시간×위치 곡선에서 맵 x·y 평면 뷰로 교체 — 노드 A·B 원+경로선,
로봇 현재점(빨강)·궤적(최근 60 s 페이드), 횡편차 가시화를 위해 y 축 확대 스케일
(0.1 m 눈금 명시, 최소 폭 0.3 m). sig_nodes 는 (xa,ya,xb,yb) 4항으로 확장.

## 추가 — 실행 중 상태를 버튼 색으로 (같은 날 후속, 사용자 제안)

STYLE_RUNNING(파랑) 신설 — 가동 중이면 실행 버튼이 "실행 중"(파랑)으로, 정지하면
"실행"(초록)으로 복귀(탭① 1 s 폴링·탭② 시작/종료 시점). 전역표에 상수 반영.

## 추가 — x·y 뷰 y 축 라벨 뭉개짐 수정 (같은 날 후속, 사용자 화면 지적)

mcl 표류 outlier 가 y 범위를 키우면 0.1 m 고정 간격 라벨 수십 개가 좌측에 겹쳐
회색 뭉치로 보이던 결함 — y 표시 폭 [0.3, 2.0 m] 클램프 + 라벨 간격 동적 선택
(≤6개, 0.05~5 m 단계)으로 수정. 하단 안내도 실제 간격 표기.

## 추가 — 실시간 위치 뷰 전면 단순화 (같은 날 후속, 사용자 지시 2건)

- 좌표계 고정: 노드 A~B 구간(+0.3 m 여백) × 경로 기준 세로 ±0.25 m, 5 cm 상대
  눈금(경로 중심 0) — 자동 스케일·궤적 제거. 실험 전에는 현재 위치+편도거리로 1회 고정.
- 표시 기호: 노드=원(A 초록/B 주황), AMR=빨간 사각형+중심점(고정 픽셀 크기),
  현재 좌표·횡편차(mm) 병기. TrackGraph 인터페이스 add_pose→set_pose 로 교체.

## 추가 — HIL 규칙 내장: 실행 전 노드 정리 (같은 날 후속, 사용자 지적)

사고: UI 교체 반복으로 can_relay 고아가 4중 축적(버스 writer 4개) — 고아 '자식'은
명령줄에 launch 파일명이 없어 중복 검사가 놓침. 조치: ① start() 중복 검사에
CHILD_PATTERNS(항목별 자식 실행 파일) 추가 ② "전체 순차 실행"은 확인 후
stop_all(전역 소탕) → 순차 기동 — 실행 전 정리 규칙을 도구에 강제.

## 추가 — 종료 로직 결함 정정 (같은 날 후속, 사용자 지적 "종료 로직 점검")

사고: 외부 kill -9 정리(운영 실수)로 can_relay 가 판다 USB 를 해제 못 하고 종료 →
다음 engage 가 무응답 wedge(USB 소프트 리셋으로 해소). 도구 결함 정정:
stop_all 소탕을 INT(정상 종료) 우선→TERM→KILL 로 바꾸고, can_relay 를 KILL 로
잡은 경우 panda_usb_reset()(USBDEVFS_RESET ioctl) 자동 수행.

## 추가 — can_relay 상주(systemd) 모델 통합 (같은 날 후속, 사용자 결정)

배포 서비스(amr-can-relay·supervisor, 도메인 125, Restart=always)를 정본으로 복원:
UI 의 can_relay 기동 항목 제거(자식 패턴·소탕 대상에서도 제외 — 서비스 보호),
systemd 상태 램프로 대체(1 s 폴링), 실험 스택 전체를 ROS_DOMAIN_ID=125 로 이주
(모듈 최상단 setdefault — UI 자식·단발·rclpy 워커 공통). engage/호밍은 단발 유지.

## 추가 — can_relay KILL 전면 금지 (같은 날 후속, 판다 소실 사고)

강제 종료 연쇄로 판다가 USB 버스에서 소실(물리 재연결 필요)되는 사고 후 조임:
stop_all 소탕에서 can_relay 계열은 KILL 폴백 제외(INT/TERM 까지만, 잔존 시 사람 처리).
운영 절차: 판다 소실 시 케이블 재연결 + systemctl restart 두 서비스.

## 추가 — 탭③ 바퀴 방향 시각화 (같은 날 후속, 사용자 제안)

/joint_states(steer_3·4 실측각, rad) 구독 → 차체 상면도에 전륜·후륜을 조향각만큼
회전시켜 표시(|각|<1° 초록 직진 판정, 각도 병기). RosWorker 에 sig_wheels 추가.
반영은 다음 UI 재시작 시(스택 소유 중 교체 금지 규칙 준수).

## 추가 — engage 상태 연동 버튼 활성화 (같은 날 후속, 사용자 지시)

/diagnostics 의 can_relay engaged 값을 구독(sig_engaged)해 미획득 시 호밍·제어권
반환 비활성, 획득 시 engage 버튼 비활성(이중 engage 방지). StackTab 은 worker 를
받도록 시그니처 변경, 첫 진단 수신 전 기본 비활성.

## 추가 — 기동 시 자기정리 (같은 날 후속, 사용자 지시)

main() 진입 시 기존 UI 인스턴스를 감지하면 그 UI(TERM→KILL)와 관련 패키지 전부를
INT 우선으로 내린 뒤 시작(cleanup_previous_ui) — 상주 can_relay 는 목록에 없어 보호.
UI 교체 고아 사고를 원천 차단. 실기 검증: 신판 기동으로 구판 자동 정리·단일 인스턴스 확인.
