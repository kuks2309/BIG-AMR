# telegram_notifier — CAN 통신 경보 텔레그램 통보

can_relay 가 도메인 125 `/diagnostics` 로 발행하는 CAN 경보(버스 이상·피드백 두절·E-stop)를
구독해 텔레그램으로 보낸다. **관측 전용이다 — 어떤 하드웨어도 제어하지 않는다.**

설계 결정과 근거: [`docs/adr/2026-08-23-telegram-can-alert-notifier.md`](../../../docs/adr/2026-08-23-telegram-can-alert-notifier.md)
구조(함수표·전역변수표): [`docs/sw_structure/telegram-notifier/2026-08-23.md`](docs/sw_structure/telegram-notifier/2026-08-23.md)

## 왜 판다를 직접 열지 않나

이 장비의 CAN 은 socketcan 이 아니라 comma.ai panda USB 로 다니고, 그 USB 는
`amr-can-relay.service` 가 단일 점유한다. 그래서 CAN 상태의 원천은 릴레이 노드가 이미
1 Hz 로 폴링해 발행하는 `/diagnostics`(status name `can_relay: 릴레이 구동`) 하나뿐이다.
릴레이 노드 자신이 죽는 경우는 진단 무수신(스테일) 통보로 잡는다 — 그 이상(소생)은
relay supervisor 소관이다.

## 통보 정책 (전이 기반 — 반복 스팸 없음)

| 사건 | 통보 |
| --- | --- |
| ERROR 진입 (CAN 버스 이상·피드백 끊긴 노드·E-stop·루프 오류) | 🔴 즉시 + 버스/노드 상세 |
| ERROR 지속 | 🔴 `renotify_s`(기본 1800 s) 간격 재통보 |
| ERROR 이탈 | 🟢 복구 |
| `/diagnostics` 무수신 `stale_after_s`(기본 15 s) | ⚠ 릴레이 노드 중단 의심 (1회) |
| 수신 재개 | 🟢 |
| WARN | 기본 무통보. `notify_warn: true` 로 켜도 상시 대기 상태(`제어권 미획득 (대기)`)는 제외 |

전송 실패(무선 단절 등)는 3회 재시도 후 버리고 로그만 남긴다 — 통보기가 로봇을 방해하지 않는다.

## 설정 — 봇 만들기부터

```bash
# 1. 텔레그램에서 @BotFather → /newbot → 토큰 발급
# 2. 설정 파일 생성 (telegram.json 은 .gitignore — 절대 커밋 금지)
cd config/telegram_notifier
cp telegram.example.json telegram.json && chmod 600 telegram.json
#    token 채우기
# 3. 만든 봇에게 텔레그램에서 아무 메시지나 하나 보낸 뒤 chat_id 확인
cd ../../src/Safety/telegram_notifier
python3 -m telegram_notifier.notifier_node --get-updates
#    → chat_id=... 를 telegram.json 에 채우기
# 4. 시험 전송
python3 -m telegram_notifier.notifier_node --test-send
```

`--get-updates`·`--test-send` 는 ROS 없이 동작한다(rclpy 는 상주 실행에서만 import).

## 카카오톡 "나에게 보내기" 채널 (선택)

무료·무심사인 대신 **카카오 계정 소유자 본인에게만** 간다(다수 수신은 텔레그램 그룹 담당).
텍스트는 200자에서 잘린다. access token 만료는 자동 갱신하며, 갱신 결과는
`kakao_tokens.json`(.gitignore) 에 즉시 저장된다. refresh token 까지 만료(약 2개월
무사용)면 `--kakao-auth` 를 다시 실행한다.

```bash
# 1. developers.kakao.com → 앱 만들기 → [앱 키] 의 REST API 키 확보
# 2. [제품 설정 > 카카오 로그인] 활성화 + 리다이렉트 URI 등록: http://localhost:8899/oauth
#    [동의항목] 에서 카카오톡 메시지 전송(talk_message) 활성화
# 3. telegram.json 에 "channels": ["telegram", "kakao"], "kakao_rest_api_key" 기입
# 4. 인가(이 장비 브라우저에서 로그인·동의) → 토큰 저장
python3 -m telegram_notifier.notifier_node --kakao-auth
# 5. 시험 전송 (켜진 채널 전부로)
python3 -m telegram_notifier.notifier_node --test-send
```

## 상주 실행

```bash
# 수동 (도메인을 맞춰야 /diagnostics 가 보인다)
ROS_DOMAIN_ID=125 python3 -m telegram_notifier.notifier_node

# systemd — 저장소에 있을 뿐 자동 설치되지 않는다
./install_service.sh            # dry-run
./install_service.sh --apply    # 설치·기동
./install_service.sh --status
./install_service.sh --remove   # 되돌리기(설정 보존)
journalctl -u amr-telegram-notifier -f
```

유닛은 `install/` 이 아니라 **소스 트리**를 `PYTHONPATH` 로 가리킨다 — `colcon build` 가
`install/` 을 비우는 순간 통보기가 죽으면 안 되기 때문이다(system_health 관례). ROS 는
`/opt/ros/humble` 만 source 한다(표준 메시지만 사용, 오버레이 불요).

## 테스트

```bash
python3 -m pytest test/ -q      # 25 PASS (2026-08-23)
```

## 하지 않는 것

- **개입하지 않는다.** 경보를 보내기만 하고 릴레이·모터·E-stop 을 건드리지 않는다.
- **판다 USB 를 열지 않는다.** 원천은 `/diagnostics` 뿐이다.
- **명령 수신 봇이 아니다.** 텔레그램 → 로봇 방향은 없다(getUpdates 는 chat_id 탐색 전용).
