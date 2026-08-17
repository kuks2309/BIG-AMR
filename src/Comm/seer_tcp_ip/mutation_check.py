#!/usr/bin/env python3
"""seer_tcp_ip 회귀의 **검출력** 검사 — 동작을 하나씩 망가뜨려 시험이 잡는지 본다.

## 왜 필요한가

`41 passed` 는 「고정했다」의 증거가 아니다. 시험이 대상 코드를 실제로 지나가지 않으면
그 시험은 옳아도 통과하고 망가뜨려도 통과한다. 이 저장소에서 실제로 그 일이 있었다
(`docs/claude-mistake/2026-08-04-001_regression-without-detection-power.md` — 통과 111개가
배선 미검증을 가렸다).

여기서 되돌리는 것들은 **이관 전 두 구현이 실제로 갖고 있던 결함**이 대부분이다
(seq 고정·응답 편호 미대조·부분 수신 미처리). 그것들이 재도입되면 시험이 잡아야 한다.

## 무엇을 하는가

대상 파일을 한 번에 하나씩 변조한 사본으로 바꾸고 전체 시험을 돌린다.
변조했는데 통과하면(미검출) 그 동작을 고정하는 회귀가 없다 — `exit 1`.
앵커(찾을 문자열) 불일치도 `exit 1` — 코드가 바뀌었으면 이 파일을 함께 갱신해야 한다.

## 사용

    python3 src/Comm/seer_tcp_ip/mutation_check.py            # 전 항목
    python3 src/Comm/seer_tcp_ip/mutation_check.py T1 P2      # 지정 항목만

원본은 어떤 경로로 끝나도 복원한다(예외·중단 포함).
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE / "seer_tcp_ip"

# (id, 되돌리는 내용, 파일명, [(찾을 문자열, 바꿀 문자열), …])
MUTATIONS = [
    # ---- 전송: 프레임 생성 ----
    ("T1", "빈 요청에도 본문 '{}' 를 붙임 — 공식 packMsg 와 바이트 어긋남", "transport.py", [
        ('    body = b""\n    if msg:\n        body = json.dumps(msg).encode("ascii")',
         '    body = json.dumps(msg or {}).encode("ascii")')]),
    ("T2", "sync 바이트를 0x5B 로 — 로봇이 헤더 파싱 실패로 연결을 끊는다", "transport.py", [
        ("SYNC = 0x5A", "SYNC = 0x5B")]),
    ("T3", "seq 를 1 로 고정 — 이관 전 두 구현의 결함 재도입", "transport.py", [
        ("        seq = next(self._seq)", "        seq = 1")]),
    ("T4", "예약 6바이트를 빼먹음 — 헤더가 10B 가 됨", "transport.py", [
        ('RSV = b"\\x00" * 6', 'RSV = b""')]),

    # ---- 전송: 응답 대조 ----
    ("T5", "응답 편호 대조 제거 — 엉뚱한 응답(60000)을 정상으로 받음", "transport.py", [
        ("        if resp_type != want:\n"
         "            self._raise_connection_limit_if_that(resp_type, body)\n"
         "            raise SeerProtocolError(f\"응답 편호 {resp_type} (기대 {want}, 요청 {api_type})\")",
         "        if False:\n            pass")]),
    ("T6", "응답 seq 대조 제거 — 어긋난 응답을 그대로 받음", "transport.py", [
        ("        if resp_seq != seq:\n"
         "            raise SeerProtocolError(f\"응답 seq {resp_seq} (기대 {seq}) — 응답 어긋남\")",
         "        if False:\n            pass")]),
    ("T7", "sync 검사 제거", "transport.py", [
        ("    if sync != SYNC:\n"
         '        raise SeerProtocolError(f"sync 불일치 0x{sync:02X} (기대 0x{SYNC:02X})")',
         "    if False:\n        pass")]),
    ("T8", "헤더 길이 검사 제거 — 짧은 버퍼가 struct 로 흘러감", "transport.py", [
        ("    if len(head) != HEAD_LEN:\n"
         '        raise SeerProtocolError(f"헤더 길이 {len(head)}B (기대 {HEAD_LEN}B)")',
         "    if False:\n        pass")]),

    # ---- 전송: 수신·수명 ----
    ("T9", "공식 데모식 단발 recv 로 복귀 — 큰 응답이 잘린다", "transport.py", [
        ("        buf = bytearray()\n"
         "        while len(buf) < n:\n"
         "            chunk = self._sock.recv(n - len(buf))\n"
         "            if not chunk:\n"
         '                raise ConnectionError(f"수신 중 연결 종료 ({len(buf)}/{n}B)")\n'
         "            buf += chunk\n"
         "        return bytes(buf)",
         "        return self._sock.recv(n)")]),
    ("T10", "실패 시 소켓을 닫지 않음 — 끊긴 소켓이 남아 재연결 불가", "transport.py", [
        ("        except (OSError, ConnectionError):\n"
         "            self.close()  # 끊긴 소켓을 남기지 않는다 — 다음 요청이 재연결한다\n"
         "            raise",
         "        except (OSError, ConnectionError):\n            raise")]),
    ("T11", "요청 간 최소 간격 무력화 — 과빈번 요청으로 로봇이 연결 정리", "transport.py", [
        ("        if not self.min_interval or self._last_request_at is None:\n            return",
         "        if True:\n            return")]),
    ("T12", "connect 를 매번 새 소켓으로 — 연결 누수", "transport.py", [
        ("        if self._sock is None:", "        if True:")]),

    # ---- 포트 정책 ----
    ("P1", "19207 실측 한도 5 → 1 로 되돌림(옛 v1.2.1 오값)", "ports.py", [
        ("    API_PORT_CONFIG: 5,\n    API_PORT_OTHER: 5,",
         "    API_PORT_CONFIG: 1,\n    API_PORT_OTHER: 1,")]),
    # ⚠ 이 돌연변이는 `... or frozenset({...})` 형태로 쓰면 **무력하다** — 파생 집합이 비면
    #    falsy 라 `or` 가 원본 리터럴로 되돌아간다. 실제로 그렇게 썼다가 미검출로 나왔다.
    #    리터럴 블록을 통째로 치환해야 한다.
    ("P2", "게이트 집합을 한도에서 파생 — 한도가 5 라 집합이 비고 게이트가 사라진다", "ports.py", [
        ("GUARDED_PORTS = frozenset({\n"
         "    API_PORT_CTRL,    # 2000 정지 · 2002 재측위 · 2010 개루프 주행\n"
         "    API_PORT_TASK,    # 3051 자율 주행\n"
         "    API_PORT_CONFIG,  # 4002 파라미터 쓰기 (4011 맵 다운로드는 읽기지만 포트 단위로 묶는다)\n"
         "    API_PORT_OTHER,   # 6001 DO 출력\n"
         "})",
         "GUARDED_PORTS = frozenset(p for p, n in OBSERVED_MAX_CONNECTIONS.items() if n <= 1)")]),
    ("P3", "응답 편호 오프셋을 0 으로", "ports.py", [
        ("RESPONSE_TYPE_OFFSET = 10000", "RESPONSE_TYPE_OFFSET = 0")]),
    ("P4", "한도 초과 ret_code 를 61001 → 61000 으로", "ports.py", [
        ("CONNECTION_LIMIT_RET_CODE = 61001", "CONNECTION_LIMIT_RET_CODE = 61000")]),
    ("P5", "한도 파라미터 이름 오배선(control → status)", "ports.py", [
        ('    API_PORT_CTRL: "RobotControlAPITCPServerMaxConnections",',
         '    API_PORT_CTRL: "RobotStatusAPITCPServerMaxConnections",')]),

    # ---- API 바인딩 ----
    ("A1", "지령 포트 차단 제거 — broker 없이 19205 를 잡는다", "api.py", [
        ("        if ports.is_guarded(port) and not self.allow_guarded:",
         "        if False:")]),
    ("A2", "ret_code 오류를 삼킴", "api.py", [
        ('        ret = resp.get("ret_code")\n        if ret not in (0, None):',
         '        ret = resp.get("ret_code")\n        if False:')]),
    ("A3", "ret_code 부재를 오류로 취급 — 정상 응답이 예외가 됨", "api.py", [
        ("        if ret not in (0, None):", "        if ret != 0:")]),
    ("A4", "위치 편호를 1004 → 1005 로 오배선", "api.py", [
        ("API_LOC = 1004", "API_LOC = 1005")]),
    ("A5", "맵 다운로드 편호를 4011 → 4010 으로", "api.py", [
        ("API_CONFIG_DOWNLOAD_MAP = 4011", "API_CONFIG_DOWNLOAD_MAP = 4010")]),
    ("A6", "맵 응답을 파싱해 dict 로 반환 — md5 대조가 불가능해짐", "api.py", [
        ("        self._raise_if_error_payload(API_CONFIG_DOWNLOAD_MAP, raw)",
         "        self._raise_if_error_payload(API_CONFIG_DOWNLOAD_MAP, raw)\n"
         "        raw = raw.decode('utf-8', 'replace').encode('utf-8')[:len(raw) - 1]")]),
    ("A7", "에러 판정 크기 제한 제거 — 큰 맵 안의 ret_code 를 오류로 오판", "api.py", [
        ("        if len(raw) > 4096:\n            return", "        if False:\n            return")]),
    ("A8", "md5 대조 제거", "api.py", [
        ("            if got != verify_md5:", "            if False:")]),
    ("A9", "get_lasers 의 step 인자를 무시", "api.py", [
        ('        msg = {"step": int(step)} if step else None', "        msg = None")]),
    ("A10", "포트별 전송 재사용 제거 — 매 호출 새 연결", "api.py", [
        ("        tr = self._transports.get(port)\n        if tr is None:",
         "        tr = None\n        if tr is None:")]),
    ("A11", "close 가 아무것도 하지 않음", "api.py", [
        ("        for tr in self._transports.values():\n            tr.close()\n"
         "        self._transports.clear()",
         "        pass")]),
    ("A12", "알람 평탄화에서 fatals 를 빠뜨림", "api.py", [
        ('        for level in ("fatals", "errors", "warnings"):',
         '        for level in ("errors", "warnings"):')]),
    ("A13", "한도 조회를 로봇에 묻지 않고 상수로 답함 — 런타임 변경을 놓친다", "api.py", [
        ("        resp = self.get_param(\"NetProtocol\", name)\n"
         "        return resp.get(\"NetProtocol\", {}).get(name, {}).get(\"value\")",
         "        return ports.OBSERVED_MAX_CONNECTIONS.get(port)")]),
    ("A14", "한도 조회 편호를 1400 → 1401 로", "api.py", [
        ("API_PARAM = 1400", "API_PARAM = 1401")]),
    ("T13", "한도 거부(61001)를 일반 편호 불일치로 흘림 — 원인이 가려진다", "transport.py", [
        ("            self._raise_connection_limit_if_that(resp_type, body)\n", "")]),
    ("T14", "한도 거부 판정에서 포트 대조를 제거 — 무관한 응답까지 한도로 오진", "transport.py", [
        ("        if resp_type != self.port or not body:", "        if not body:")]),

    # ---- 제어권 세션 (control.py) ----
    ("C1", "반납 전 정지를 보내지 않음 — 관성으로 계속 간다", "control.py", [
        ("            if self.stop_on_exit:\n                self.api.stop()",
         "            if False:\n                self.api.stop()")]),
    ("C2", "예외 경로에서 반납하지 않음 — 다음 클라이언트가 40020 으로 막힌다", "control.py", [
        ("    def __exit__(self, *exc):\n        self.release()\n        return False\n\n\n"
         "class JogKeepalive",
         "    def __exit__(self, *exc):\n        return False\n\n\nclass JogKeepalive")]),
    ("C3", "정지 실패 시 반납을 건너뜀 — 제어권을 쥔 채 남는다", "control.py", [
        ("        try:\n            if self.stop_on_exit:\n                self.api.stop()\n"
         "        finally:\n            self.held = False\n            self.api.release_control()",
         "        if self.stop_on_exit:\n            self.api.stop()\n"
         "        self.held = False\n        self.api.release_control()")]),
    ("C4", "이중 획득 가드 제거 — 반납 짝이 깨진다", "control.py", [
        ("        if self.held:\n            raise SeerControlError(",
         "        if False:\n            raise SeerControlError(")]),
    ("C5", "소유자 조회 실패가 획득을 막는다", "control.py", [
        ("        try:\n            self.previous_owner = self.api.get_control_owner()\n"
         "        except Exception:\n            self.previous_owner = {}",
         "        self.previous_owner = self.api.get_control_owner()")]),
    ("C6", "빈 nick_name 가드 제거 — 로봇 화면에서 소유자를 못 가린다", "control.py", [
        ('        if not str(nick_name).strip():', '        if False:')]),
    ("C7", "주기 ≥ dead-man 검증 제거 — 매 주기 섰다 갔다 한다", "control.py", [
        ("        if interval_s * 1000.0 >= duration_ms:", "        if False:")]),
    ("C8", "duration_ms=0(무한) 을 허용 — dead-man 이 사라진다", "control.py", [
        ("        if duration_ms <= 0:", "        if False:")]),
    ("C9", "jog 재송신에서 duration 을 뺌 — 그 지령이 무한이 된다", "control.py", [
        ("        self.api.open_loop_move(self.vx, self.vy, self.w, duration_ms=self.duration_ms)",
         "        self.api.open_loop_move(self.vx, self.vy, self.w, duration_ms=0)")]),
    ("C10", "due() 가 항상 True — 과송신으로 로봇이 연결을 정리한다", "control.py", [
        ("        if self._last_sent_at is None:\n            return True\n"
         "        return (self._clock() - self._last_sent_at) >= self.interval_s",
         "        return True")]),
    ("C11", "set_velocity 가 즉시 송신 — 주기 계약 붕괴", "control.py", [
        ("        self.vx, self.vy, self.w = float(vx), float(vy), float(w)\n\n    def due",
         "        self.vx, self.vy, self.w = float(vx), float(vy), float(w)\n"
         "        self.tick()\n\n    def due")]),
    ("C12", "stop() 이 속도를 0 으로 되돌리지 않음 — 다음 tick 이 다시 달린다", "control.py", [
        ("        self.vx = self.vy = self.w = 0.0\n        return self.api.stop()",
         "        return self.api.stop()")]),

    # ---- 확장 편호 (api.py) ----
    ("N1", "open_loop_move 에 duration 기본값 부여 — 호출자가 정지 시간을 안 고른다", "api.py", [
        ("def open_loop_move(self, vx: float, vy: float, w: float,"
         " duration_ms: int) -> dict:",
         "def open_loop_move(self, vx: float = 0.0, vy: float = 0.0,"
         " w: float = 0.0,\n                       duration_ms: int = 600) -> dict:")]),
    ("N2", "2010 요청에서 duration 필드 누락", "api.py", [
        ('                         {"vx": float(vx), "vy": float(vy), "w": float(w),\n'
         '                          "duration": int(duration_ms)})',
         '                         {"vx": float(vx), "vy": float(vy), "w": float(w)})')]),
    ("N3", "제어권 획득을 조회 포트로 보냄 — 게이트를 우회한다", "api.py", [
        ("        return self.call(ports.API_PORT_CONFIG, API_CONFIG_SEIZE_CONTROL,",
         "        return self.call(ports.API_PORT_STATE, API_CONFIG_SEIZE_CONTROL,")]),
    ("N4", "제어권 편호 4005/4006 맞바꿈", "api.py", [
        ("API_CONFIG_SEIZE_CONTROL = 4005  # {\"nick_name\":…}\n"
         "API_CONFIG_RELEASE_CONTROL = 4006  # 무파라미터",
         "API_CONFIG_SEIZE_CONTROL = 4006  # {\"nick_name\":…}\n"
         "API_CONFIG_RELEASE_CONTROL = 4005  # 무파라미터")]),
    ("N5", "40020 상수를 다른 값으로 — 제어권 거부를 못 알아본다", "api.py", [
        ("CONTROL_PREEMPTED_RET_CODE = 40020", "CONTROL_PREEMPTED_RET_CODE = 40021")]),
    ("N6", "go_target 에서 source_id 를 뺌", "api.py", [
        ('        body = {"id": str(site_id), "source_id": str(source_id)}',
         '        body = {"id": str(site_id)}')]),
    ("N7", "set_params 가 save 무시하고 항상 4002(저장) — 휘발 의도가 사라진다", "api.py", [
        ("        api = API_CONFIG_SAVE_PARAMS if save else API_CONFIG_SET_PARAMS",
         "        api = API_CONFIG_SAVE_PARAMS")]),
    ("N8", "소프트 비상정지를 제어 포트로 보냄", "api.py", [
        ("        return self.call(ports.API_PORT_OTHER, API_OTHER_SOFT_ESTOP,",
         "        return self.call(ports.API_PORT_CTRL, API_OTHER_SOFT_ESTOP,")]),
    ("N9", "1060 조회 편호를 1061 로", "api.py", [
        ("API_CONTROL_OWNER = 1060", "API_CONTROL_OWNER = 1061")]),
    ("N10", "맵 md5 반환 키를 로봇 형태로 — 1300 의 이름과 안 맞물린다", "api.py", [
        ('        return {orig: by_sent[s] for orig, s in zip(wanted, sent)}',
         '        return by_sent')]),
    ("N11", "1302 에 .smap 을 안 붙임 — 로봇이 40051 로 거부한다", "api.py", [
        ('        sent = [n if n.endswith(".smap") else n + ".smap" for n in wanted]',
         '        sent = list(wanted)')]),
    ("N12", "요청한 이름이 응답에 없어도 통과 — None 이 md5 처럼 흘러간다", "api.py", [
        ("        missing = [o for o, s in zip(wanted, sent) if s not in by_sent]\n"
         "        if missing:\n"
         '            raise SeerProtocolError(f"1302 응답에 요청한 지도가 없다: {missing}")\n'
         "        return {orig: by_sent[s] for orig, s in zip(wanted, sent)}",
         "        return {orig: by_sent.get(s) for orig, s in zip(wanted, sent)}")]),
]


def main(argv: list[str]) -> int:
    want = {a.upper() for a in argv[1:]}
    targets = sorted({m[2] for m in MUTATIONS})
    pristine = {name: (PKG / name).read_text(encoding="utf-8") for name in targets}
    rows, misses, skipped = [], [], []

    def restore():
        for name, text in pristine.items():
            (PKG / name).write_text(text, encoding="utf-8")

    try:
        for mid, what, fname, subs in MUTATIONS:
            if want and mid.upper() not in want:
                continue
            src = pristine[fname]
            anchor_ok = True
            for old, new in subs:
                if old not in src:
                    anchor_ok = False
                    break
                src = src.replace(old, new, 1)
            if not anchor_ok:
                skipped.append(mid)
                rows.append((mid, what, "‼ 앵커 불일치", "코드가 바뀌었다 — 돌연변이를 갱신하라"))
                continue
            (PKG / fname).write_text(src, encoding="utf-8")
            # ⚠ 바이트코드 캐시를 반드시 무력화한다. .pyc 유효성은 (mtime 초, 파일크기)로
            # 판정되므로, 같은 초에 같은 크기로 쓴 변조(예: 1004→1005, 4011→4010)는
            # **직전 항목의 .pyc 가 재사용되어** 엉뚱한 항목이 검출된 것처럼 보인다.
            # 실제로 첫 실행에서 A5 가 A4 의 실패 목록을 그대로 보고했다.
            shutil.rmtree(PKG / "__pycache__", ignore_errors=True)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            run = subprocess.run(
                [sys.executable, "-B", "-m", "pytest", "test", "-q", "-p", "no:cacheprovider",
                 "--no-header", "--tb=no"],
                cwd=HERE, env=env, capture_output=True, text=True, timeout=900)
            caught = [ln.split("::")[-1].split()[0]
                      for ln in run.stdout.splitlines() if ln.startswith("FAILED")]
            if run.returncode:
                rows.append((mid, what, "✅ 검출", ", ".join(caught[:3]) or "(수집 실패)"))
            else:
                misses.append(mid)
                rows.append((mid, what, "❌ 미검출", "이 동작을 고정하는 회귀가 없다"))
            restore()
    finally:
        restore()  # 어떤 경로로 끝나도 원본 복원

    width = max((len(r[1]) for r in rows), default=0)
    for mid, what, verdict, detail in rows:
        print(f"{verdict}  {mid:4s} {what:<{width}}  {detail}")
    if skipped:
        print(f"\n‼ 앵커 불일치 {len(skipped)}건({', '.join(skipped)}) — "
              f"코드가 바뀌었으면 이 파일의 MUTATIONS 를 함께 갱신한다.")
    if misses:
        print(f"\n❌ 검출력 없는 항목 {len(misses)}건: {', '.join(misses)}")
        print("   시험이 통과하는 것과 결함을 잡는 것은 다르다. 시험을 보강하라.")
        return 1
    if skipped:
        return 1
    print(f"\n✅ {len(rows)}개 항목 전부 검출.")
    print("   ⚠ 범위 한정 — 여기서 검증된 것은 '이 목록의 동작이 회귀로 고정돼 있다'까지다."
          " 목록에 없는 동작·문서 서술·실기 정합은 검증되지 않았다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
