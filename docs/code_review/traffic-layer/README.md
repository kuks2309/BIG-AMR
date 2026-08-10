# traffic-layer — review timeline

The rules that decide *whether a robot may move now*: collision avoidance,
junction reservation, the give-way handshake, the bay entry interlock, and the
road network they run on. Routing and the job lifecycle are reviewed elsewhere
(`docs/code_review/csm/`).

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| 2026-08-10 | `f543422` + dirty tree (sim_acs sha `7742b8ad4849dd1f`) | REQUEST CHANGES | Critical 1 (measured robot-to-robot contact at 0.90 m), High 4 — all at seams between traffic layers, none inside one |

Staleness: the reviewed state is the working tree, not a commit. Re-review once
these changes are committed so the version can be pinned to a hash.
