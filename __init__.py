"""signal-notify: Signal texts when a Hermes turn ends or Hermes waits on a person.

Messages go to signal-cli's JSON-RPC endpoint (SIGNAL_HTTP_URL) from the account in
SIGNAL_ACCOUNT. Sends run on a daemon thread so a slow or unreachable signal-cli never
blocks the agent loop or a prompt.
"""

import json
import logging
import threading
import time
import urllib.request
from collections import OrderedDict
from typing import Any, Callable, Optional

logger = logging.getLogger("signal_notify")

SEND_TIMEOUT_SECONDS = 20
DEDUPE_WINDOW_SECONDS = 60
MAX_TRACKED = 64
DEFAULTS: dict[str, Any] = {
    "recipient": "",
    "notify_on": ["paused", "failed", "interrupted", "question"],
    "skip_platforms": ["signal", "cron", "subagent"],
    "reply_chars": 300,
}
INPUT_LABELS = {
    "clarify": "❓ Hermes is asking",
    "approval": "🔐 Hermes needs approval",
    "sudo": "🔑 Hermes needs a sudo password",
}


def _get_secret(name: str) -> str:
    try:
        from agent.secret_scope import get_secret
    except ImportError:  # Hermes without secret scopes; never read .env ourselves
        return ""
    return get_secret(name, "") or ""


def clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if limit <= 0:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def as_list(value: Any, default: list) -> list:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value]
    return list(default)


def as_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _remember(store: "OrderedDict[str, Any]", key: str, value: Any) -> None:
    store[key] = value
    store.move_to_end(key)
    while len(store) > MAX_TRACKED:
        store.popitem(last=False)


def turn_outcome(completed: bool, failed: bool, interrupted: bool) -> str:
    if failed or not (completed or interrupted):
        return "failed"
    return "interrupted" if interrupted else "paused"


def send_signal(url: str, account: str, recipient: str, message: str) -> None:
    body = json.dumps({
        "jsonrpc": "2.0", "method": "send", "id": f"signal_notify_{int(time.time() * 1000)}",
        "params": {"account": account, "recipient": [recipient], "message": message},
    }).encode()
    req = urllib.request.Request(f"{url.rstrip('/')}/api/v1/rpc", data=body,
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=SEND_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read() or b"{}")
    except Exception as e:  # a failed notification must never reach the agent loop
        logger.warning("signal-notify: send failed: %s", e)
        return
    if "error" in data:
        logger.warning("signal-notify: signal-cli error: %s", data["error"])
    else:
        logger.info("signal-notify: sent %r", message.splitlines()[0][:80])


class Notifier:
    def __init__(self, get_config: Callable[[str, Any], Any],
                 get_secret: Callable[[str], str] = _get_secret,
                 sender: Callable[[str, str, str, str], None] = send_signal,
                 background: bool = True):
        self._get_config = get_config
        self._get_secret = get_secret
        self._sender = sender
        self._background = background
        self._last_reply: "OrderedDict[str, str]" = OrderedDict()
        self._reported_turns: "OrderedDict[str, bool]" = OrderedDict()
        self._recent: "OrderedDict[str, float]" = OrderedDict()
        self._lock = threading.Lock()

    def _setting(self, key: str) -> Any:
        value = self._get_config(key, DEFAULTS[key])
        if key in ("notify_on", "skip_platforms"):
            return as_list(value, DEFAULTS[key])
        if key == "reply_chars":
            return as_int(value, DEFAULTS[key])
        return DEFAULTS[key] if value is None else str(value).strip()

    def _wants(self, event: str, platform: str) -> bool:
        skip = {p.lower() for p in self._setting("skip_platforms")}
        notify_on = {e.lower() for e in self._setting("notify_on")}
        return event in notify_on and (platform or "").lower() not in skip

    def _is_duplicate(self, message: str) -> bool:
        now = time.monotonic()
        with self._lock:
            last = self._recent.get(message)
            _remember(self._recent, message, now)
        return last is not None and now - last < DEDUPE_WINDOW_SECONDS

    def _deliver(self, message: str) -> None:
        if self._is_duplicate(message):
            logger.info("signal-notify: skipped duplicate %r", message.splitlines()[0][:80])
            return
        url, account = self._get_secret("SIGNAL_HTTP_URL"), self._get_secret("SIGNAL_ACCOUNT")
        recipient = self._setting("recipient") or self._get_secret("SIGNAL_HOME_CHANNEL")
        if not (url and account and recipient):
            logger.warning("signal-notify: SIGNAL_HTTP_URL, SIGNAL_ACCOUNT or recipient missing")
            return
        if not self._background:
            self._sender(url, account, recipient, message)
            return
        threading.Thread(target=self._sender, args=(url, account, recipient, message),
                         name="signal-notify", daemon=True).start()

    def on_post_llm_call(self, session_id: str = "", assistant_response: str = "",
                         platform: str = "", **_: Any) -> None:
        if not (session_id and assistant_response) or not self._wants("paused", platform):
            return
        preview = clip(assistant_response, self._setting("reply_chars"))
        with self._lock:
            _remember(self._last_reply, session_id, preview)

    def on_session_end(self, session_id: str = "", completed: bool = False, failed: bool = False,
                       interrupted: bool = False, turn_exit_reason: str = "", platform: str = "",
                       turn_id: Optional[str] = None, **extra: Any) -> None:
        # CLI exit paths fire a second copy that carries `reason`. Report it only for a turn
        # the turn finalizer has not already reported.
        exit_copy = "reason" in extra
        with self._lock:
            reply = self._last_reply.pop(session_id, "")
            if not turn_id or turn_id in self._reported_turns:
                return
            _remember(self._reported_turns, turn_id, True)
        outcome = turn_outcome(completed, failed, interrupted)
        if not self._wants(outcome, platform):
            return
        where = f"[{platform or 'hermes'} …{(session_id or '?')[-8:]}]"
        reason = turn_exit_reason or (str(extra.get("reason") or "") if exit_copy else "")
        if outcome == "failed":
            message = f"❌ Hermes errored {where}\n{reason or 'turn failed'}"
        elif outcome == "interrupted":
            message = f"⏹ Hermes stopped {where}\n{reason or 'interrupted'}"
        else:
            message = f"⏸ Hermes paused {where}" + (f"\n{reply}" if reply else "")
        self._deliver(message)

    def on_human_input_request(self, kind: str = "", prompt: str = "", session_id: str = "",
                               platform: str = "", **_: Any) -> None:
        if not self._wants("question", platform):
            return
        label = INPUT_LABELS.get(kind, f"❓ Hermes is waiting ({kind or 'input'})")
        where = f"[{platform or 'hermes'} …{(session_id or '?')[-8:]}]"
        preview = clip(prompt, self._setting("reply_chars"))
        self._deliver(f"{label} {where}" + (f"\n{preview}" if preview else ""))


def register(ctx) -> None:
    notifier = Notifier(ctx.get_config)
    ctx.register_hook("post_llm_call", notifier.on_post_llm_call)
    ctx.register_hook("on_session_end", notifier.on_session_end)
    ctx.register_hook("on_human_input_request", notifier.on_human_input_request)
