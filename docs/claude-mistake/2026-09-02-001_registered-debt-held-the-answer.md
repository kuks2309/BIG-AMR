---
id: 2026-09-02-001
type: rule-violation
category: source-of-truth-skipped
status: closed
reflected_assets:
  - src/Comm/seer_tcp_ip/include/seer_tcp_ip/api.hpp
  - References/Seer-Driver/robokit_tcp_api.md
  - References/Seer-Driver/sources.md
  - src/Comm/seer_tcp_ip/tools/param_probe.cpp
  - docs/debt/registry.md
---

# 설정 API 편호 4종이 전부 틀렸고, 정답은 3주 전부터 부채 대장에 적혀 있었다

## 무슨 일이 있었나

`seer_tcp_ip` 의 설정 쓰기를 실기로 검증하려고 `param_probe` 를 만들어 돌렸더니,
로봇이 `{"ret_code":0}` 을 돌려주는데 값은 바뀌지 않았다. 나는 이것을 **기전의 수수께끼**로
읽고 가설 셋을 세웠다 — ⓐ 배차 문맥이라 무시된다 ⓑ `RobotNote` 만 읽기 전용이다
ⓒ 별도 적용 트리거가 필요하다. 셋 다 틀렸고, `debt-126` 을 「기전 미규명」으로 등록한 뒤
커밋·푸시·머지까지 마쳤다.

원인은 단순했다. **편호가 틀렸다.**

| 우리가 보낸 것 | 공식 |
|---|---|
| 4001 | **4100** `robot_config_setparams_req` |
| 4002 | **4101** `robot_config_saveparams_req` |
| 4003 | **4102** `robot_config_reloadparams_req` |
| 4004 | **4300** `robot_config_clearfatal_req` |

로봇은 정의되지 않은 4001 요청에 `ret_code 0` 만 돌려줬다.

## 정답이 이미 있던 곳 — 세 곳

1. **`docs/debt/registry.md` 의 `debt-095`** (2026-08-08 등록):
   > ④ 문서의 `4001/4002 = setparams/saveparams` 는 실제 **`4100/4101`**
   이 행은 "이 문서를 근거로 매핑을 자동화하면 엉뚱한 명령을 보낸다" 고 **예고까지** 했다.
   나는 오늘 이 파일을 **여러 번 열어 편집했고**(debt-126 등록·debt-111 갱신), 그러면서도
   `4001` 로 grep 하지 않았다.
2. **`References/Seer-Driver/github_sdk/robotkit-netprotocol-l-1.2.1.txt:3320,3401`** — 공식 PDF
   추출본. `4100 robot_config_setparams_req` · 응답 `14100`.
3. **SEER RoboKit 위키** — `Set Robot Params Temporarily` = `API number 4100 (0x1004)`.
   그 URL 은 `References/Seer-Driver/sources.md` **§3-1a 에 이미 적혀 있었다.**

## 대신 내가 한 일

`sources.md` 를 열지 않은 채 웹을 뒤졌다. Feishu wiki 루트로 갔다가 QR 로그인 벽을 만나고,
GitHub 조직 페이지를 열고, 공개 저장소 둘을 clone 해 grep 했다(0건). 사용자가
**"매번 새롭게 이상한곳 찾지말고"** 라 지적하고 URL 을 직접 열어 준 뒤에야 `sources.md` 를 열었고,
거기엔 그 URL 과 "computer-use 로 guest 열람 성공" 기록이 이미 있었다.

## 왜 이번엔 잡혔나

**되읽기 왕복** 때문이다. `param_probe` 를 「쓰고 `ret_code` 확인」으로 끝냈으면 통과로 기록됐을
것이다. 쓴 뒤 `getParam` 으로 되읽어 값을 비교했기 때문에 「수리됨 ≠ 반영됨」이 드러났다.
단위 시험 232건은 이것을 잡을 수 없었다 — 전부 **우리 상수를 우리 기대값으로** 대조했기 때문이다
(`CHECK_EQ(api::kConfigSetParams, 4001)` 은 4001 이 틀렸다는 사실에 무력하다).

## 재발 방지 (자산에 반영한 것)

- **편호 4종 정정** — `api.hpp`, 시험 고정값, `param_probe` 문구. 정정 후 실기 왕복 **PASS**.
- **근본 원인 문서 정정** — `References/Seer-Driver/robokit_tcp_api.md:171-174`. 이 표가 코드에
  틀린 값을 물려줬다.
- **`sources.md` 에 「원문이 이긴다」 명시** — 파생 정리본과 공식 PDF·위키가 갈리면 원문이 정본.
  Chromium 필요(Firefox 는 본문 미렌더)라는 열람 조건도 같이 적었다.
- **거짓 자산 철회** — `ports::kDispatchingRetCode`(40012). 존재하지 않는 편호 4003 에 대한
  응답이었고 공식 오류표에 없다. 상수와 시험 고정을 삭제했다.
- **판정 지점 한 줄** — **외부 편호·주소·매직값을 코드에 넣기 전, 그 값으로 저장소를 전수 grep
  한다.** `grep -rn "4001"` 한 번이면 `debt-095` 가 나왔다. 이것은 앞선 여덟 건과 같은 공백이며
  (INDEX §메타 패턴), 이번 변형은 **부채 대장 자신이 정답을 갖고 있었다** 는 점이다 — 대장은
  "무엇을 모르는지" 뿐 아니라 **"무엇을 이미 알아냈는지"** 도 담는다.
