# 2026-08-23 — telegram_notifier 다채널화: 카카오톡 "나에게 보내기" 추가

- **세션**: be12909f · **ADR**: [2026-08-23-kakao-memo-channel](../docs/adr/2026-08-23-kakao-memo-channel.md)
- **선행**: [2026-08-23-telegram-notifier-new](2026-08-23-telegram-notifier-new.md)

## 무엇을

- `config.py` — `channels`(기본 `["telegram"]`, 허용 telegram/kakao) 도입. 채널별 필수값
  검증을 그 채널이 켜졌을 때만 하도록 변경(카카오 단독 구성 가능). 카카오 토큰 파일
  기본 경로는 설정 파일 옆 `kakao_tokens.json`(.gitignore 등재).
- `kakao_api.py` 신설 — 인가 URL·code 교환·토큰 갱신·`send_to_me`(text 템플릿 200자
  절단). `KakaoSession` 이 401 에서 refresh 1회 후 재시도, 갱신 즉시 파일 저장(0600).
  REST 키·토큰은 `redact_secrets` 로 가려 예외·로그에 노출하지 않는다.
- `notifier_node.py` — `_build_senders`(channels→전송함수 목록) + `SendWorker` 채널별
  독립 재시도(한 채널 실패가 다른 채널을 막지 않음, 예외 무관 워커 생존).
  `--kakao-auth`(localhost:8899 로 code 수신→토큰 저장)·`--test-send` 다채널화.
- `telegram.example.json`·README 에 카카오 설정 절차 기재.

## 검증

- 단위: **37 PASS** (기존 25 + kakao_api 8 + config 채널 4) — 401→refresh→재전송
  순서, 비-401 전파, 토큰 회전 유무별 저장, 200자 절단, 채널 검증 포함.
- 텔레그램 실전송 회귀: 다채널 개편 후 `--test-send` 재실행 → 도착 확인(2026-08-23).
- 실전송 검증은 아래 §실기 인가·검증 참조(완료).

## 실기 인가·검증 (2026-08-23 19:06)

computer-use 로 developers.kakao.com 에서 앱 생성부터 인가까지 완료:

- 앱 **BigAMR-Alert**(ID 1554258, K&J Robotics) 생성, REST 키·클라이언트 시크릿은
  화면 복사(클립보드)로 확보 — 텔레그램 토큰 OCR 오독 재발 방지.
- 콘솔 설정: 카카오 로그인 ON · 로그인 리다이렉트 URI `http://localhost:8899/oauth`
  (신 콘솔은 **플랫폼 키 > REST API 키 수정** 안에 있다 — 카카오 로그인 메뉴 아님) ·
  동의항목 talk_message **선택 동의**(목적 기재).
- **시크릿 지원 보강이 필수였다**: 키 발급 시 클라이언트 시크릿이 기본 ON 이라
  `client_secret` 없이는 토큰 교환이 거부된다 → `kakao_client_secret` 설정 추가(38 PASS).
- 사고 1건: GTK 클립보드 소유권 소멸로 이전 내용(시크릿)이 구글 검색창에 붙여넣어져
  검색 기록에 노출 → **시크릿 즉시 재발급**으로 무효화, 새 값으로 교체. URL 입력은
  `xdotool type --delay 60` 직접 타이핑으로 전환(옴니박스 비동기 뒤섞임 회피).
- `--kakao-auth` (localhost:8899 code 수신) → 토큰 저장(0600) → `--test-send` 에서
  **telegram·kakao 양 채널 전송 성공**.
