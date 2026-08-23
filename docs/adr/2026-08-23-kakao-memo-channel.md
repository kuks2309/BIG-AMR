# ADR 2026-08-23 — 경보 노티파이어 다채널화 + 카카오톡 "나에게 보내기" 채널

- **Status**: Accepted — 2026-08-23 (구현·단위검증·**실전송 검증 완료** — 앱 BigAMR-Alert 생성, `--kakao-auth` 인가, `--test-send` 로 telegram·kakao 양 채널 전송 성공)

## Context

- 사용자가 텔레그램에 더해 **카카오톡 수신**을 원한다(2026-08-23). 카카오 방식 중
  알림톡(사업자·템플릿 심사·유료)·친구톡(검수)은 자유 문구 로봇 경보에 부적합하고,
  **"나에게 보내기"**(developers.kakao.com 메시지 API)만 무료·무심사다. 단 **본인 1명
  한정**이며 OAuth(Open Authorization) 토큰이 만료되므로 자동 갱신이 필요하다.
- 기존 `telegram_notifier` 는 전송부(`telegram_api`)가 판정부(`policy`)와 분리돼 있어
  채널 추가가 자연스럽다(ADR [2026-08-23-telegram-can-alert-notifier](2026-08-23-telegram-can-alert-notifier.md)).
- 카카오 REST 키·refresh token 도 봇 토큰과 같은 비밀정보다.

## Decision

1. **설정에 `channels` 도입** — 기본 `["telegram"]`, 허용 {telegram, kakao}. 채널별
   필수값 검증은 그 채널이 켜졌을 때만 한다(텔레그램 없이 카카오 단독도 가능).
2. **`kakao_api.py` 신설**(표준 라이브러리만): 인가 URL 생성 → code 교환 → 토큰
   갱신 → `send_to_me`(text 템플릿, 200자 절단). `KakaoSession` 이 401 에서 refresh
   1회 후 재시도하고 **갱신 즉시 토큰 파일에 저장**(0600) — access(수 시간)·refresh
   (약 2개월) 만료 구조상 저장을 미루면 재인증이 필요해진다.
3. **토큰 파일** `config/telegram_notifier/kakao_tokens.json` — `.gitignore` 등재.
   디렉토리명은 telegram 시절 그대로 둔다(경로 churn 회피, README 에 명시).
4. **인가 절차는 `--kakao-auth`** — 로컬 `http://localhost:8899/oauth` 를 리다이렉트
   URI 로 등록하게 하고, CLI 가 임시 HTTP 서버로 code 를 받아 토큰 교환까지 자동화.
   브라우저가 같은 장비에 있으므로 localhost 로 충분하다.
5. **SendWorker 다채널화** — 채널별 독립 재시도·로그(한 채널 실패가 다른 채널을 막지
   않음). 시험 전송(`--test-send`)도 켜진 채널 전부로 보낸다.

## Alternatives (기각)

- **알림톡/친구톡**: 사업자·템플릿 사전 심사·건당 과금, 자유 문구 불가. 기각.
- **카카오워크 봇**: 별도 유료 워크스페이스 전제. 기각.
- **kakao SDK(Software Development Kit) 의존성 추가**: HTTP 4개 호출에 과하다. 기각.

## Consequences

- 이득: 사용자 선호 메신저로 동일 경보 수신. 채널 구조가 생겨 이후 채널(메일 등) 추가 용이.
- 비용/위험: refresh token 만료(≈2개월 무사용 시)면 `--kakao-auth` 재실행 필요 —
  전송 실패 로그에 안내를 남긴다. "나에게 보내기"는 **계정 소유자 본인만** 받는다 —
  다수 수신은 텔레그램 그룹이 담당(ADR 전편 §Consequences).
- 새 공개표면: `channels`·카카오 설정 키·토큰 파일 스키마·`--kakao-auth`.

## Rollback

가역. 설정 `channels` 에서 `kakao` 제거(코드 변경 불요) → `kakao_tokens.json` 삭제 →
필요시 `kakao_api.py` 와 관련 설정 필드 제거. 카카오 앱은 developers.kakao.com 에서 삭제.
