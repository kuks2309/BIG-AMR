# 2026-08-23 — telegram_notifier 신설: CAN 통신 경보 텔레그램 통보

- **세션**: be12909f · **ADR**: [2026-08-23-telegram-can-alert-notifier](../docs/adr/2026-08-23-telegram-can-alert-notifier.md)
- **함수표**: [패키지 권위본](../src/Safety/telegram_notifier/docs/code_review/telegram-notifier/2026-08-23.md) · 루트 집계 등재

## 무엇을

`src/Safety/telegram_notifier` 신설 — can_relay 가 도메인 125 `/diagnostics` 로 발행하는
CAN 경보(버스 이상·피드백 두절·E-stop·루프 오류)를 구독해 텔레그램 봇으로 전송하는
관측 전용 노드. 판다 USB 는 릴레이가 단일 점유하므로 직접 열지 않고 `/diagnostics` 를
단일 원천으로 쓴다(이 장비 socketcan 0개 — system_health 편입 기각 근거).

- `telegram_api.py` — Bot API sendMessage/getUpdates, urllib 만(의존 0). 토큰은
  URL 경로에 실리므로 모든 예외·로그 문자열에서 `redact_token` 으로 가림.
- `config.py` — `config/telegram_notifier/telegram.json` 로드. 미지 키 KeyError,
  `_` 접두 주석 키(system_health 관례), 필수값 미충족 SystemExit, 권한 경고.
- `policy.py` — 전이 상태기(순수 로직): ERROR 진입/지속(기본 1800 s 재통보)/복구,
  진단 무수신 스테일(기본 15 s) 1회 통보+재개 통보, WARN 은 기본 무통보(상시 idle 이
  WARN 이므로) · `notify_warn` 켜도 `제어권 미획득 (대기)` 는 제외.
- `notifier_node.py` — rclpy 노드. 전송은 워커 스레드+유한 큐(콜백 무차단, 큐 포화 시
  폐기). rclpy 는 `_spin` 안에서만 import — `--get-updates`(chat_id 탐색)·`--test-send`
  는 ROS 없이 동작.
- `systemd/amr-telegram-notifier.service` + `install_service.sh` — 명시 설치만,
  도메인 125, `/opt/ros/humble` 만 source(오버레이 불요 — colcon build 중에도 생존).
- `.gitignore` 에 `config/telegram_notifier/telegram.json` 등재(봇 토큰 비밀정보),
  커밋은 `telegram.example.json` 만.

## 검증

- 단위: `python3 -m pytest test/ -q` → **25 PASS** (policy 전이 10 · config 9 · api 6).
- colcon build PASS.
- 실기(2026-08-23, 도메인 125 실 `/diagnostics`): status name `can_relay: 릴레이 구동`
  필터 정합 · 실재 ERROR(`CAN 버스 이상: bus2 error-passive (REC=0 TEC=128)`) 수신 →
  기동+경보 2건 전송 시도 확인(더미 토큰이라 401 은 예상 실패, 재시도 3회 후 폐기·로그).
- SIGTERM 종료: 초판은 rclpy 이중 shutdown 으로 트레이스백 — `ExternalShutdownException`
  포획 + `try_shutdown()` 으로 수정, 재실행에서 무사 종료 확인.
- 실전송(2026-08-23 18:08): computer-use 로 웹 텔레그램에서 봇 생성
  (@bigamr_can_alert_bot) → 토큰은 화면 OCR 오독(`1`↔`l`) 이 getMe 401 로 드러나
  **클립보드 복사로 확보** → `--get-updates` 로 chat_id 획득 → `--test-send` 도착을
  화면 캡처로 확인. **검증 완료.** 잔여: systemd 상주 설치(sudo 비밀번호 필요, 사용자 실행).
- ⚠ 부수 발견: 사용자가 처음 접촉한 것은 **가짜 BotFather**(`@Botfagher_bot` 철자 사칭,
  구독 스팸·@Manybot 유도)였다. 진짜(@BotFather, 인증 체크)로 재진행했고 가짜에게 넘어간
  정보는 없다(/start·yes·/newbot 뿐). 가짜 계정은 차단 + 대화 삭제 완료(2026-08-23 18:14, 화면 검증).
- 보안 후속: 토큰이 찍힌 화면 캡처가 `experiments/capture/` 에 남으므로
  `.gitignore` 에 `experiments/capture/` 추가(커밋 차단 확인).
