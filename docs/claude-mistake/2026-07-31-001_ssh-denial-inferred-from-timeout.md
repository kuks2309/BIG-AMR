---
id: 2026-07-31-001
type: mistake
category: wrong-assumption
status: closed
reflected_assets:
  - docs/network/seer_network_access.md#amap-1-분석-장비-접근
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-amap1-access.md
---

# 2026-07-31 17:10 (KST) — 타임아웃을 정책 거부로 오독해 "SSH 차단" 을 5턴 확정 보고

## 무엇을 했는가

amap-1(Seer 분석 장비)의 리버스 엔지니어링(Reverse Engineering) 문서·원본 하드를 읽으려고 SSH 를 시도했다.
사용자 4개로 시험했고 결과가 갈렸다.

| 사용자 | 결과 | 소요 |
| --- | --- | --- |
| `nvidia` | `tailscale: tailnet policy does not permit you to SSH as user "nvidia"` | 즉시 |
| `kuksauto` | 같은 정책 거부 | 즉시 |
| `ubuntu` | 같은 정책 거부 | 즉시 |
| **`amap`** | **`Terminated`(exit 143 = 내 15초 timeout)** | 15초 |

이 표에서 마지막 행만 성격이 다른데도 "**전 사용자 차단**" 으로 묶어 보고했고, 이후 5턴에 걸쳐
"재부팅해도 안 풀린다", "tailnet ACL(Access Control List) 을 열어야 한다" 를 확정형으로 반복했다.
사용자에게 ACL 수정 또는 수동 명령 실행이라는 **불필요한 우회 작업을 요구**했다.

사용자가 붙여넣은 amap-1 로그인 배너의 `Last login: ... from 100.92.214.74`(이 장비 IP) 를 보고서야
`amap@amap-1` 을 60초 타임아웃으로 재시도했고 **즉시 성공**했다. 그 뒤 원본 하드를 읽기 전용으로 조회해
`robot.param` 배포값과 `libMCLoc.so` 디스어셈블까지 이번 세션에서 끝냈다.

## 무엇이 잘못이었나

`Terminated`(내가 건 timeout 만료)와 `tailnet policy does not permit`(서버의 명시적 거부)은 **다른 사건**인데
같은 결론("차단")으로 합쳤다. 도구가 낸 두 종류의 실패 신호를 구분하지 않은 것이다.
그 결과 "이 경로는 불가능하다" 는 **부정형 단정**을 근거 블록까지 붙여 확정했고, 실제로는 열려 있었다.

## 사용자 지적

직접적인 지적은 없었다. 사용자가 amap-1 셸 배너를 붙여넣으며 `????` 라고만 물었고,
그 배너의 `Last login ... from 100.92.214.74` 가 "이 장비에서 접속된 적이 있다" 는 반증이었다.
사용자가 이 로그를 보여주지 않았다면 오판이 세션 끝까지 유지됐을 것이다.

## 원인 분석

`wrong-assumption` — 도구(SSH/tailscale) 의 실패 모드를 검증 없이 동일시했다.

세부 원인 셋:
1. **표본이 스스로 반증을 담고 있었다.** 4개 중 3개는 즉시 거부, 1개만 타임아웃이었다. 이 비대칭이
   "그 계정만 통과해 실제 접속 단계로 갔다" 는 신호였는데, 다수결로 눌러 버렸다.
2. **타임아웃 값을 실패 원인에서 배제했다.** 15초는 내가 정한 값이다. 내 파라미터가 만든 결과를
   상대 시스템의 정책으로 귀속시켰다.
3. **부정형 단정에 확증 절차를 적용하지 않았다.** "된다" 는 주장에는 실행·출력을 요구하면서
   "안 된다" 에는 실패 출력 하나로 만족했다. `docs/claude-mistake/INDEX.md` §메타 패턴이
   2026-07-27-003 이래 반복 경고해 온 형태이고, 그 경고는 SessionStart 로 이번 세션에도 주입돼 있었다.

## 재발 방지

지식 자산 두 곳에 접근 사실과 판별 규칙을 고정했다.

- `docs/network/seer_network_access.md` 에 **§amap-1(분석 장비) 접근** 절 신설 —
  계정은 `amap` 하나만 허용(나머지는 tailnet 정책 거부), 최초 핸드셰이크가 느려 **타임아웃 60초 이상** 필요,
  63G 원본 하드 마운트 경로, 읽기 전용 취급 규칙을 기록.
- 프로젝트 메모리 `biguamr-amap1-access.md` 에 같은 사실 + **판별 규칙** 기록:
  `Terminated`/exit 143 은 **내 타임아웃**이고 거부가 아니다 — 접근 불가를 단정하기 전에
  타임아웃을 늘려 재시도하고, 서버가 낸 거부 메시지(`permission denied`, `policy does not permit`)를
  본문에 인용할 수 있을 때만 "차단" 이라고 쓴다.
