---
id: 2026-08-06-004
type: mistake
category: context-missing
status: closed
reflected_assets:
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-seer-internal-transport.md
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-amap1-access.md
---

# 2026-08-06 20:05 (KST) — 원본 하드를 조회하지 않고 「zmq 근거 없음」으로 판정

## 무엇을 했는가

사용자가 "Seer 원본은 ROS 가 아니라 자체 zmq+protobuf 를 쓴다"는 내 서술을 되물었다. 저장소를
`grep` 해 보니 그 주장의 출처가 우리 포팅본 주석 1줄(`Tools/mcl2d_standalone/include/mcl2d_localizer.hpp:2`)
뿐이고 `references/seer/libMCLoc/` 의 RE 문서·공식 매뉴얼에는 zmq 언급이 없었다. 이를 근거로
**"제 서술은 근거가 없습니다 / 2차 자료를 1차처럼 인용했습니다 / zmq 라고 단정할 근거가 없습니다"**
라고 정정 보고했다.

## 무엇이 잘못이었나

**참인 명제는 "저장소 문서에 zmq 근거가 없다" 였는데 "zmq 라는 근거가 없다" 로 적었다.**
사용자가 원본 위치(`amap-server` 63G SATA)를 알려주어 조회하니 정반대였다:

- `libMCLoc.so` 의 `DT_NEEDED` 에 **`libzmq.so.5`** 와 **`libprotobuf.so.17`** 이 모두 있다.
- 그 플러그인이 **zmq C API 심볼 20개를 직접 import** 한다(`zmq_ctx_new`·`zmq_socket`·`zmq_bind`·
  `zmq_connect`·`zmq_msg_*`·`zmq_close`·`zmq_ctx_term` 등).
- 심볼에 **zmq 소켓으로 protobuf 메시지를 주고받는 래퍼**가 그대로 박혀 있다 —
  `profiler::IO::TrySend(zmq::socket_t&, const google::protobuf::Message&, zmq::send_flags)`,
  `TryReceive(zmq::socket_t&, std::shared_ptr<google::protobuf::Message>&, ...)`.
- 배포본에 `rbk/3rdlib/libzmq.so.5.2.4` 가 동봉돼 있고 `rbk/proto/` 에 `.proto` 스키마 수십 개가 있다.
- 바이너리 문자열에 zmq 엔드포인트 형식 `inproc://backend`·`tcp://*:%d` 가 있다.

즉 **포팅본 주석이 옳았고 내 "정정" 이 오히려 틀렸다.** 정확한 인용을 근거 없는 추측으로 몰아세운
형태이며, 이는 2026-07-28-006(정오표 v1 이 정확한 Handbook 인용을 「오진」으로 규정)과 같은 유형이다.

## 사용자 지적

> "seer원본은 amap-server에 63g sata에 있습니다."

한 줄로 조사 후보를 지정해 주었고, 그 조회 한 번으로 판정이 뒤집혔다.

## 원인 분석

INDEX §메타 패턴의 **「없다」의 근거 범위를 넘겨 일반화** (2026-08-03-002 → 2026-08-05-001 →
2026-08-06-002)의 **네 번째 재발**이다. 이번에는 가중 사유가 있다 — **원본이 어디 있는지 내가 이미
알고 있었다.** 메모리 `biguamr-amap1-access` 에 63G 하드의 호스트·마운트 경로·`libMCLoc.so` 위치까지
적혀 있었고, 같은 세션에서 `references/seer/libMCLoc/PROVENANCE.md`(원본 위치를 명시한 파일)를
직접 열어 읽기까지 했다. 그런데도 조사 대상에 넣지 않고 저장소 grep 만으로 부정 판정을 내렸다.

「조사 범위를 지목된 것으로 한정」이 아니라 **「이미 아는 원본을 후보에서 누락」** 이라는 점에서
더 나쁘다. 저장소 안만 뒤지는 습관이 굳어 있다는 신호다.

## 재발 방지

- 신규 메모리 `biguamr-seer-internal-transport.md` 에 **결과를 값으로** 상주시켰다(zmq+protobuf
  링크·심볼·엔드포인트·`proto/` 구성, 그리고 「주 데이터 경로인지는 미확정」이라는 한계까지).
  「조사하라」는 지시를 또 적는 대신 조사 결과 자체를 남기는 방식 — 2026-07-31-004 에서 채택한 것과 동일.
- `biguamr-amap1-access` 를 갱신했다: 호스트명이 `amap-server` 로 바뀐 사실, 63G = `sdb2`,
  Tailscale SSH 의 브라우저 재인증 요구와 그 우회 절차. 다음 세션이 조회를 망설이지 않도록.
- **판정 문구 규율**: 원본 자산이 존재하는 주제에서 「근거가 없다」를 쓰려면 **그 원본을 조회한
  명령·출력을 함께 적는다.** 저장소 grep 만 했으면 「저장소 문서에는 없다」까지만 쓴다.
