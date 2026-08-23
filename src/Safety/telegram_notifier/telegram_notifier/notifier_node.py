"""can_relay `/diagnostics` 를 구독해 CAN 경보를 텔레그램으로 보내는 노드.

rclpy 는 :func:`_spin` 안에서만 import 한다 — ``--test-send``·``--get-updates`` 는
ROS 환경 없이도 동작해야 설정 단계에서 쓸 수 있다.
"""
from __future__ import annotations

import argparse
import json
import platform
import queue
import sys
import threading
import time
from pathlib import Path

from telegram_notifier import kakao_api, telegram_api
from telegram_notifier.config import NotifierConfig, load_config
from telegram_notifier.policy import AlertPolicy, LEVEL_ERROR

# can_relay 의 DiagnosticStatus.name 접두 — 이 status 만 감시한다
_WATCH_NAME_PREFIX = "can_relay:"
_QUEUE_MAX = 50
_RETRY = 3
_RETRY_BACKOFF_S = 2.0
_TICK_PERIOD_S = 1.0
# ERROR 상세에 싣는 KeyValue 키 접두(버스 카운터·노드별 상태)
_DETAIL_KEY_PREFIXES = ("bus", "node")


def _default_config_path() -> str:
    """저장소 루트의 config/telegram_notifier/telegram.json (소스 트리 실행 기준)."""
    return str(Path(__file__).resolve().parents[4]
               / "config" / "telegram_notifier" / "telegram.json")


def _level_int(raw) -> int:
    """DiagnosticStatus.level 은 ROS2 에서 ``byte``(rclpy 는 bytes 로 노출)다."""
    if isinstance(raw, (bytes, bytearray)):
        return raw[0] if raw else 0
    return int(raw)


def _format_detail(values) -> str:
    """KeyValue 목록에서 버스·노드 상태만 추려 사람이 읽을 줄로 만든다."""
    lines = []
    for kv in values:
        if kv.key.startswith(_DETAIL_KEY_PREFIXES):
            lines.append(f"{kv.key}: {kv.value}")
    return "\n".join(lines)


def _build_senders(cfg: NotifierConfig) -> list:
    """설정의 channels 에 따라 (채널명, 전송함수) 목록을 만든다."""
    senders = []
    if "telegram" in cfg.channels:
        senders.append(("telegram", lambda t: telegram_api.send_message(
            cfg.token, cfg.chat_id, t, cfg.send_timeout_s)))
    if "kakao" in cfg.channels:
        session = kakao_api.KakaoSession(
            cfg.kakao_rest_api_key, cfg.kakao_token_file, cfg.send_timeout_s,
            cfg.kakao_client_secret)
        senders.append(("kakao", session.send))
    return senders


class SendWorker:
    """전송 전용 스레드 — rclpy 콜백이 HTTP 로 막히지 않게 한다.

    큐가 가득 차면 새 경보를 버린다(로봇 감시가 전송 지연에 물리면 안 된다).
    채널별로 독립 재시도한다 — 한 채널 실패가 다른 채널을 막지 않는다.
    """

    def __init__(self, senders: list, prefix: str,
                 log_error, log_info) -> None:
        self._senders = senders
        self._prefix = prefix
        self._log_error = log_error
        self._log_info = log_info
        self._q: queue.Queue[str | None] = queue.Queue(maxsize=_QUEUE_MAX)
        self._thread = threading.Thread(
            target=self._run, name="notify-send", daemon=True)
        self._thread.start()

    def submit(self, text: str) -> bool:
        """큐 적재만 한다(무차단). 가득 차면 버리고 False."""
        try:
            self._q.put_nowait(f"[{self._prefix}] {text}")
            return True
        except queue.Full:
            self._log_error("전송 큐 포화 — 경보 1건 폐기")
            return False

    def _run(self) -> None:
        while True:
            text = self._q.get()
            if text is None:
                return
            for name, send in self._senders:
                for attempt in range(1, _RETRY + 1):
                    try:
                        send(text)
                        self._log_info(f"{name} 전송: {text.splitlines()[0]}")
                        break
                    except Exception as exc:
                        # 예외 종류와 무관하게 워커는 살아남는다 — 경보기가 죽으면 안 된다
                        if attempt == _RETRY:
                            self._log_error(f"{name} 전송 실패(폐기): {exc}")
                        else:
                            time.sleep(_RETRY_BACKOFF_S * attempt)

    def stop(self, timeout_s: float = 5.0) -> None:
        """잔여 큐 소진 후 스레드를 내린다(데몬 스레드라 강제 종료도 무해)."""
        try:
            self._q.put(None, timeout=timeout_s)
        except queue.Full:
            return
        self._thread.join(timeout=timeout_s)


def _spin(cfg: NotifierConfig) -> int:
    """rclpy 노드를 만들어 종료 신호까지 돈다. rclpy import 는 여기서만."""
    import rclpy
    from diagnostic_msgs.msg import DiagnosticArray
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node

    prefix = cfg.message_prefix or platform.node()

    class TelegramNotifierNode(Node):
        """`/diagnostics` 구독 + 1 s 스테일 타이머 → policy → worker."""

        def __init__(self) -> None:
            super().__init__("telegram_notifier")
            self._policy = AlertPolicy(
                notify_warn=cfg.notify_warn, warn_ignore=cfg.warn_ignore,
                renotify_s=cfg.renotify_s, stale_after_s=cfg.stale_after_s)
            self.worker = SendWorker(
                _build_senders(cfg), prefix,
                lambda m: self.get_logger().error(m),
                lambda m: self.get_logger().info(m))
            self.create_subscription(
                DiagnosticArray, "/diagnostics", self._on_diagnostics, 10)
            self.create_timer(_TICK_PERIOD_S, self._on_timer)
            if cfg.notify_start:
                self.worker.submit("🚀 telegram_notifier 기동 — can_relay 진단 감시 시작")

        def _on_diagnostics(self, msg: DiagnosticArray) -> None:
            for st in msg.status:
                if not st.name.startswith(_WATCH_NAME_PREFIX):
                    continue
                level = _level_int(st.level)
                detail = _format_detail(st.values) if level >= LEVEL_ERROR else ""
                ev = self._policy.on_status(
                    level, st.message, detail, time.monotonic())
                if ev is not None:
                    self.worker.submit(ev.text)

        def _on_timer(self) -> None:
            ev = self._policy.on_tick(time.monotonic())
            if ev is not None:
                self.worker.submit(ev.text)

    rclpy.init()
    node = TelegramNotifierNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # SIGINT/SIGTERM — rclpy 가 컨텍스트를 이미 내렸을 수 있다
        pass
    finally:
        node.worker.stop()
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


def _kakao_auth(cfg: NotifierConfig) -> int:
    """카카오 인가 절차 — 인가 URL 안내 후 localhost 로 code 를 받아 토큰 저장."""
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    if "kakao" not in cfg.channels:
        raise SystemExit('설정 "channels" 에 "kakao" 를 추가한 뒤 다시 실행하라')
    redirect = kakao_api.DEFAULT_REDIRECT_URI
    port = urllib.parse.urlparse(redirect).port
    print("1) developers.kakao.com 앱 [카카오 로그인] 에 리다이렉트 URI 등록 확인:")
    print(f"   {redirect}")
    print("2) 이 장비의 브라우저에서 아래 URL 을 열어 로그인·동의:")
    print(f"   {kakao_api.build_auth_url(cfg.kakao_rest_api_key)}")

    holder: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — http.server 인터페이스 고정
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("code"):
                holder["code"] = q["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("인가 완료 — 터미널로 돌아가세요.".encode("utf-8"))

        def log_message(self, *args):
            pass

    deadline = time.monotonic() + 300.0
    with HTTPServer(("127.0.0.1", port), Handler) as srv:
        srv.timeout = 5.0
        print(f"3) localhost:{port} 에서 code 대기 중 (최대 300초)…")
        while "code" not in holder and time.monotonic() < deadline:
            srv.handle_request()
    if not holder.get("code"):
        raise SystemExit("code 를 받지 못했다 — 브라우저에서 동의까지 완료했는지 확인")
    tokens = kakao_api.exchange_code(
        cfg.kakao_rest_api_key, holder["code"],
        client_secret=cfg.kakao_client_secret)
    kakao_api.save_tokens(cfg.kakao_token_file, tokens)
    print(f"토큰 저장 완료: {cfg.kakao_token_file}")
    print("시험 전송: python3 -m telegram_notifier.notifier_node --test-send")
    return 0


def _parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="telegram_notifier",
        description="can_relay /diagnostics → 텔레그램/카카오 경보")
    parser.add_argument("--config", default=_default_config_path(),
                        help="telegram.json 경로 (기본: 저장소 config/)")
    parser.add_argument("--test-send", action="store_true",
                        help="설정 검증용 시험 메시지를 켜진 채널 전부로 전송 후 종료")
    parser.add_argument("--get-updates", action="store_true",
                        help="봇이 받은 메시지의 chat_id 를 나열 후 종료 "
                             "(token 만 있으면 된다)")
    parser.add_argument("--kakao-auth", action="store_true",
                        help="카카오 나에게-보내기 인가(브라우저 로그인) 후 토큰 저장")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """진입점. --get-updates·--test-send 는 ROS 없이 동작한다."""
    args = _parse_args(argv)

    if args.get_updates:
        try:
            with open(args.config, encoding="utf-8") as f:
                token = str(json.load(f).get("token", ""))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"설정 읽기 실패 ({args.config}): {exc}")
        if not token:
            raise SystemExit(f"token 이 비어 있다 ({args.config})")
        updates = telegram_api.get_updates(token)
        if not updates:
            print("업데이트 없음 — 텔레그램에서 봇에게 아무 메시지나 먼저 보내라")
        for u in updates:
            chat = (u.get("message") or {}).get("chat") or {}
            print(f"chat_id={chat.get('id')}  "
                  f"({chat.get('type')}, {chat.get('title') or chat.get('username') or chat.get('first_name')})")
        return 0

    cfg = load_config(args.config)

    if args.kakao_auth:
        return _kakao_auth(cfg)

    if args.test_send:
        prefix = cfg.message_prefix or platform.node()
        for name, send in _build_senders(cfg):
            send(f"[{prefix}] ✅ telegram_notifier 시험 전송 성공 ({name})")
            print(f"{name}: 시험 전송 성공")
        return 0

    return _spin(cfg)


if __name__ == "__main__":
    sys.exit(main())
