# ADR 2026-08-23 — CAN 통신 경보 텔레그램 노티파이어

- **Status**: Accepted — 2026-08-23 (구현·단위검증·**실전송 검증 완료** — 봇 @bigamr_can_alert_bot 생성, `--test-send` 도착 화면 확인. systemd 상주 설치만 잔여: sudo 필요)

## Context

- 사용자 요구: **CAN 통신 이상을 텔레그램 메신저로 통보**받고 싶다 (2026-08-23).
- 이 장비(Jetson, tegra)의 CAN 은 socketcan 인터페이스가 **0개**다 — `ls /sys/class/net/` 실측
  (2026-08-23). CAN 은 comma.ai panda USB 어댑터(`lsusb: bbaa:ddcc`)로만 다니고, 그 USB 는
  `amr-can-relay.service` 가 상주 점유한다. 별도 감시 프로세스가 판다를 직접 열면 릴레이와
  충돌한다 (`Tools/docking_field_kit/amap2_canhealth_watchdog.py` 방식은 릴레이 미가동 장비 전용).
- `can_relay` 드라이버 노드가 이미 per-bus CAN 헬스(펌웨어 0xc3: bus_off/error_passive/
  error_warning/REC/TEC/LEC)를 1 Hz 로 폴링해 **도메인 125** `/diagnostics`(DiagnosticArray,
  status name `can_relay: 릴레이 구동`)로 발행한다
  ([driver_node.py:402-471](../../src/Comm/CAN/can_relay/can_relay/driver_node.py)). 판정:
  - ERROR: 루프 오류 · CAN 버스 이상(bus_fault) · E-stop 인가 · 피드백 끊긴 노드
  - WARN: 제어권 미획득(대기 — **릴레이의 상시 idle 상태**) · 호밍 중 · SDO 거부
- `api.telegram.org` HTTPS 도달 실측 확인(2026-08-23, curl 302/0.77 s).
- 텔레그램 봇 토큰은 비밀정보다 — 저장소 커밋 금지(coding §4 금지 패턴: 하드코딩 secret).
  또한 Bot API 는 토큰을 **URL 경로**에 싣는다(`/bot<token>/...`) — 예외·로그에 URL 이 새면
  토큰이 샌다.

## Decision

1. **새 ROS2 패키지 `src/Safety/telegram_notifier`** — rclpy 노드가 `/diagnostics` 를 구독해
   상태 전이를 텔레그램으로 전송한다. 도메인(125)은 systemd 유닛 환경변수로 지정한다.
2. **전이 기반 전송 정책** (반복 스팸 금지):
   - ERROR 진입 → 즉시 통보, ERROR 지속 → `renotify_s`(기본 1800 s) 간격 재통보
   - ERROR 이탈(복구) → 통보
   - `/diagnostics` 무수신 `stale_after_s`(기본 15 s) → "릴레이 노드 무응답" 통보, 재개 시 복구 통보
     (경보 원천인 노드 자신의 사망을 잡는 유일한 수단)
   - WARN 은 기본 **무통보**(상시 idle 이 WARN 이므로), `notify_warn` 옵션으로만 켠다.
     켜도 `warn_ignore` 목록(기본: `제어권 미획득 (대기)`)은 제외.
3. **전송은 워커 스레드 + 유한 큐** — rclpy 콜백에서 blocking HTTP 를 부르지 않는다
   (coding §4 금지 패턴). 전송 실패는 재시도 후 버리고 로그만 남긴다 — 통보기가 로봇 동작을
   방해하지 않는다.
4. **표준 라이브러리 `urllib` 만 사용** — 의존성 추가 없음. 예외 문자열의 URL 은 토큰을
   가린 뒤에만 로그에 쓴다.
5. **토큰·chat_id 는 `config/telegram_notifier/telegram.json`** — `.gitignore` 등재(커밋 금지),
   커밋은 `telegram.example.json` 만. 미지의 키는 KeyError 로 거부(system_health
   `Thresholds.from_mapping` 관례), `_` 접두 키는 주석으로 무시.
6. **systemd 유닛 `amr-telegram-notifier.service`** — 저장소에 템플릿만 두고
   `install_service.sh --apply` 명시 실행 시에만 설치(system_health 관례). ROS 는
   `/opt/ros/humble` 만 source(표준 메시지 `diagnostic_msgs` 만 쓰므로 오버레이 불요 —
   colcon build 가 `install/` 을 비워도 죽지 않는다).

## Alternatives (기각)

- **판다 직접 폴링**(amap2_canhealth_watchdog 이식): USB 단일 점유를 릴레이와 다투므로 기각.
- **system_health 에 편입**: socketcan 0개라 CAN 을 볼 수 없고, Phase 1 의 ROS 무의존
  원칙(rclpy import 금지 테스트)이 깨진다. 기각.
- **journald 문구 파싱**: 로그 문구 결합은 취약하고 판정 중복이다. 기각.
- **python-telegram-bot 의존성 추가**: sendMessage POST 한 개에 라이브러리는 과하다. 기각.
  (의존성 3필드 심사 자체가 불필요 — 의존 0)

## Consequences

- **이득**: CAN 버스 이상·피드백 두절·E-stop·릴레이 사망이 현장 밖 사용자에게 수 초 내 도달.
  판정 로직은 can_relay 단일 소스를 재사용(중복 판정 없음).
- **비용/위험**:
  - 경보 원천이 can_relay 노드다 — 노드가 죽으면 CAN 판정도 없다. 스테일 통보가 그 사실을
    알리는 것까지가 이 도구의 한계(릴레이 소생은 supervisor 소관).
  - 외부 인터넷(무선) 의존 — 단절 구간의 경보는 재시도 한도 내에서만 살아남는다(유한 큐).
  - 새 공개표면: `telegram.json` 스키마 · 유닛 이름 · 전송 정책 파라미터.
- 실전송 검증은 사용자 봇 토큰 수령 후(--test-send). 그 전까지 미검증 상태를 Status 에 명시.

## Rollback

가역. `./install_service.sh --remove` (유닛 정지·삭제) → 패키지 디렉토리
`src/Safety/telegram_notifier` 와 `config/telegram_notifier/` 삭제 → `.gitignore` 의
`config/telegram_notifier/telegram.json` 줄 제거. 다른 패키지가 이 패키지를 import 하지 않는다.
