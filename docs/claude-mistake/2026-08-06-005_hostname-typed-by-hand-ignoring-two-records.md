---
id: 2026-08-06-005
type: mistake
category: context-missing
status: closed
reflected_assets:
  - Tools/seer_re/amap_server.sh
  - docs/network/seer_network_access.md#amap-server-분석-장비-접근
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-amap1-access.md
---

# 2026-08-06 21:38 (KST) — 개명된 호스트명을 손으로 적어 실패, 정답은 기록 2곳에 이미 있었다

## 무엇을 했는가

6일 만에 재개한 세션에서 원본 바이너리 분석을 위해 분석 장비에 접속하려고
`ssh amap@amap-1` 을 **명령에 직접 타이핑**했다. `Could not resolve hostname amap-1` 로 실패하자
`tailscale status | grep amap-1` 로 헤매다(목록에 없음) tailscale IP `100.116.195.65` 를 찾아
IP 직결로 우회해 작업을 계속했다. 작업을 마치고 사용자에게
**"amap-1 은 호스트명이 더는 해석되지 않아 IP 로 붙었습니다 — 메모리에 반영해둘까요?"** 라고 물었다.

## 무엇이 잘못이었나

그 사실은 **이미 기록돼 있었고, 두 곳이었다.**

1. 프로젝트 메모리 `biguamr-amap1-access.md:12` — "**2026-08-06: tailscale 이름이 `amap-1` → `amap-server` 로
   바뀌었다**(IP 동일)". 같은 파일이 하드 경로 오기(`/dev/sda2` → 실제 `/dev/sdb2`)까지 정정해 두었다.
2. 저장소 문서 `docs/network/seer_network_access.md:93,97,103,111` — §amap-server 절이 개명 사실과
   **접속 명령(`ssh -o ConnectTimeout=60 amap@amap-server`)까지** 적어 두었다.

게다가 메모리 요약은 **세션 시작 시 MEMORY.md 로 주입**돼 있었다("amap-server 분석 장비 접근 — 구 이름 amap-1").
즉 눈앞에 답이 있는 상태에서 낡은 이름을 손으로 적었고, 우회에 성공하자 **이미 기록된 것을 사용자에게 되물었다.**
사용자 지적: "amap-1 은 이미 amap-server로 바뀌었는데 또 기록을 안보내".

## 사용자 지적

> "amap-1 은 이미 amap-server로 바뀌었는데 또 기록을 안보내"

"또" — 반복이라는 지적이다. `context-missing` 은 이번이 **네 번째**다
(2026-07-27-004 → 2026-07-28-010 → 2026-07-31-004 → 본 건).

## 원인 분석

`context-missing` — 필요한 컨텍스트가 **주입까지 됐는데도** 조사 후보에 넣지 않았다.

세부 원인 둘:
1. **대화 이력이 기록을 이겼다.** 같은 세션의 6일 전 대화에 `ssh amap@amap-1` 성공 기록이 있어서
   그것을 그대로 재사용했다. 세션이 재개될 때 **환경은 6일치 변했는데** 대화 맥락은 그대로라,
   "이전에 되던 명령"이 "현재 사실"을 덮었다. 재개 시점이 가장 위험한 구간인데 아무 확인도 하지 않았다.
2. **값을 손으로 적을 수 있으면 손으로 적는다.** 호스트명·계정·타임아웃이 문서와 메모리에만 있고
   실행 가능한 형태로 박제돼 있지 않아서, 매번 "기억나는 명령"을 타이핑하게 된다.
   INDEX §메타 패턴이 2026-07-31-004 에서 이미 결론지은 형태다 —
   **「조사하라」를 적는 대신 조사 결과를 상주시켜야 한다**. 상주는 시켰는데 *실행 가능하지 않았다.*

## 재발 방지

「기록을 읽어라」를 또 적지 않는다. **호스트명을 손으로 적을 필요 자체를 없앤다.**

- **`Tools/seer_re/amap_server.sh` 신설** — 호스트·계정·타임아웃·원본 하드 경로·라이브러리 경로를
  한 곳에 상수로 두고 `ssh`/`rsync`/`objdump` 호출을 감싼다. 이름이 또 바뀌면 이 파일 한 줄만 고친다.
  사용법: `amap_server.sh ssh '<명령>'` · `amap_server.sh disasm <addr> <len>` · `amap_server.sh push <파일...>`.
- `docs/network/seer_network_access.md` §amap-server 와 프로젝트 메모리가 **그 스크립트를 가리키도록** 갱신 —
  "접속은 스크립트로 한다, 호스트명을 직접 쓰지 않는다"를 값이 아니라 **경로**로 남긴다.
- 판별 규칙 추가(같은 절): **세션 재개(resume) 직후 원격 접속 전에는 그 장비의 메모리 항목을 먼저 연다** —
  6일 공백 동안 이름·경로·마운트가 바뀐 전례가 실제로 있었다(본 건 + `/dev/sda2`→`sdb2`).
