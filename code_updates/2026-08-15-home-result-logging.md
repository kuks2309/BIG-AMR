# 2026-08-15 — `~/home` 결과를 로그에 남긴다 (docstring 이 약속만 하고 있었다)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md` §4).

- 계기: 2026-08-14 동기화 때 대피시킨 `stash@{0}` 을 폐기하기 전 내용을 확인하다 발견.
- 대상: `src/Comm/CAN/can_relay/can_relay/driver_node.py` · `test/test_gui_node.py`

## 무엇이 어긋나 있었나

`_srv_home` 의 docstring 이 이렇게 적고 있었다.

> 결과는 응답뿐 아니라 **로그에도 남긴다** — 0° 복귀가 게이트에 거부돼도 노드 로그로
> 사유를 추적할 수 있어야 한다.

**그런데 남기지 않았다.** 호밍 **전** 경고만 찍고, `backend.home()` 이 돌려준 `(ok, why)` 는
응답에만 실었다. 진행 중 상태 전이는 백엔드가 찍으므로 펌웨어 경로에서는 종료 상태가
로그에 보이지만, 서비스가 무엇을 결론으로 삼았는지는 나오지 않는다. method 35 경로는
반환 문자열이 유일한 통로라 **아무것도 안 보인다**.

## 고친 것

결과를 성패에 따라 `info`/`error` 로 한 줄 남긴다.

⚠ **같은 줄에서 severity 를 바꾸지 않는다.** rclpy 는 로그 컨텍스트를 호출 지점
(파일·함수·줄)으로 캐시하고 severity 변경을 거부한다 — 한 줄에서 `info`/`error` 를 번갈아
부르면 두 번째 호출이 `ValueError` 다. 같은 함정이 감시 노드에서 실제로 터졌다(`03149a9`).

## 시험

`stash@{0}` 에 있던 `test_home_result_is_logged_not_only_returned` 를 옮겼다. 원본의 마지막
단정(로그 줄에 「0° 복귀」가 실려야 한다)은 **기각된 드라이버 결합안**(`home()` 이
`steer_to_zero()` 를 이어 호출) 전제라 뺐다. 현재 설계에서 0° 복귀는 호출자
(`home_and_zero`) 소관이다.

실기 근거는 그대로 살렸다 — 2026-08-08 15:42 호밍이 `DONE` 까지 갔는데 그 뒤로 노드 로그가
한 줄도 없어 조사할 수 없었다.

돌연변이 확인: 로그 한 줄을 지우면 실패한다.

## `stash@{0}` 폐기

내용을 전수 대조하고 버렸다.

| stash 내용 | 처리 |
| --- | --- |
| 2WS `line_follow` CMakeLists | main 에 있음(`9afefce`) — 버림 |
| 드라이버 `steer_zero_after_home` 결합안 | 기각안으로 `session/6e5a2017`(`0522d2d`) 에 보존 — 버림 |
| `test_home_result_is_logged_not_only_returned` | **main 에 없었다 → 옮김**(위) |
| `issues_and_fixes.md` · `function_table.md` 갱신분 | 그 시점 기준이라 현행과 무관 — 버림 |
