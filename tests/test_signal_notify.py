import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "signal_notify", Path(__file__).resolve().parent.parent / "__init__.py"
)
sn = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sn)

SECRETS = {
    "SIGNAL_HTTP_URL": "http://signal.test:8080",
    "SIGNAL_ACCOUNT": "+15550000001",
    "SIGNAL_HOME_CHANNEL": "+15550000002",
}


def make(config=None, secrets=SECRETS):
    sent = []
    notifier = sn.Notifier(
        get_config=lambda key, default: (config or {}).get(key, default),
        get_secret=lambda name: secrets.get(name, ""),
        sender=lambda url, account, recipient, message: sent.append(
            {"url": url, "account": account, "recipient": recipient, "message": message}
        ),
        background=False,
    )
    return notifier, sent


def end(n, **kw):
    base = {"session_id": "sess-12345678", "turn_id": "t1", "completed": True, "platform": "cli"}
    n.on_session_end(**{**base, **kw})


def test_pause_includes_reply_preview_and_home_channel():
    n, sent = make()
    n.on_post_llm_call(session_id="sess-12345678", assistant_response="All tests pass.\nDone.")
    end(n)
    assert sent[0]["recipient"] == "+15550000002"
    assert sent[0]["message"] == "⏸ Hermes paused [cli …12345678]\nAll tests pass. Done."


def test_failed_turn_reports_reason():
    n, sent = make()
    end(n, completed=False, failed=True, turn_exit_reason="context overflow")
    assert sent[0]["message"].startswith("❌ Hermes errored")
    assert "context overflow" in sent[0]["message"]


def test_incomplete_turn_without_flags_counts_as_failed():
    n, sent = make()
    end(n, completed=False)
    assert sent[0]["message"].startswith("❌")


def test_interrupted_turn():
    n, sent = make()
    end(n, completed=False, interrupted=True, turn_exit_reason="user_stop")
    assert sent[0]["message"].startswith("⏹ Hermes stopped")


@pytest.mark.parametrize(
    "kind,label",
    [
        ("clarify", "❓ Hermes is asking"),
        ("approval", "🔐 Hermes needs approval"),
        ("sudo", "🔑 Hermes needs a sudo password"),
        ("future_kind", "❓ Hermes is waiting (future_kind)"),
    ],
)
def test_input_requests(kind, label):
    n, sent = make()
    n.on_human_input_request(kind=kind, prompt="Commit now?", session_id="s1", platform="tui")
    assert sent[0]["message"] == f"{label} [tui …s1]\nCommit now?"


@pytest.mark.parametrize("platform", ["signal", "cron", "subagent", "SIGNAL"])
def test_skipped_platforms(platform):
    n, sent = make()
    end(n, platform=platform)
    n.on_human_input_request(kind="clarify", prompt="q", platform=platform)
    assert sent == []


def test_exit_copy_without_turn_id_is_ignored():
    n, sent = make()
    n.on_session_end(
        session_id="s", completed=False, interrupted=True, platform="cli", reason="shutdown"
    )
    assert sent == []


def test_exit_copy_of_reported_turn_is_not_sent_twice():
    n, sent = make()
    end(n, completed=False, interrupted=True, turn_exit_reason="user_stop")
    end(n, completed=False, interrupted=True, reason="keyboard_interrupt")
    assert len(sent) == 1


def test_exit_copy_of_unreported_turn_uses_its_reason():
    n, sent = make()
    end(n, completed=False, interrupted=True, reason="keyboard_interrupt")
    assert sent[0]["message"] == "⏹ Hermes stopped [cli …12345678]\nkeyboard_interrupt"


def test_failed_wins_over_interrupted():
    n, sent = make()
    end(n, completed=False, failed=True, interrupted=True)
    assert sent[0]["message"].startswith("❌")


def test_identical_messages_within_window_are_deduped():
    n, sent = make()
    for _ in range(3):
        n.on_human_input_request(kind="approval", prompt="git push", session_id="s", platform="cli")
    assert len(sent) == 1


def test_string_and_bad_config_values_are_coerced():
    n, sent = make(
        {"notify_on": "question, paused", "skip_platforms": "tui", "reply_chars": "not a number"}
    )
    n.on_human_input_request(kind="clarify", prompt="q", platform="tui")
    n.on_post_llm_call(session_id="sess-12345678", assistant_response="x" * 400, platform="cli")
    end(n)
    assert len(sent) == 1
    assert sent[0]["message"].endswith("x" * 299 + "…")


def test_reply_cache_is_bounded_clipped_and_skips_filtered_platforms():
    n, _ = make({"reply_chars": 10})
    for i in range(sn.MAX_TRACKED + 20):
        n.on_post_llm_call(session_id=f"s{i}", assistant_response="y" * 1000, platform="cli")
    n.on_post_llm_call(session_id="sub", assistant_response="z", platform="subagent")
    assert len(n._last_reply) == sn.MAX_TRACKED
    assert "sub" not in n._last_reply
    assert all(len(v) <= 10 for v in n._last_reply.values())


def test_notify_on_filters_events_and_recipient_override():
    n, sent = make({"notify_on": ["question"], "recipient": "+15559999999"})
    end(n)
    n.on_human_input_request(kind="clarify", prompt="q", platform="cli")
    assert [s["recipient"] for s in sent] == ["+15559999999"]


def test_reply_chars_zero_sends_no_conversation_text():
    n, sent = make({"reply_chars": 0})
    n.on_post_llm_call(session_id="sess-12345678", assistant_response="secret plan")
    end(n)
    n.on_human_input_request(kind="approval", prompt="rm -rf build", platform="cli")
    assert all("secret" not in s["message"] and "rm -rf" not in s["message"] for s in sent)


def test_reply_cache_is_cleared_per_turn():
    n, sent = make()
    n.on_post_llm_call(session_id="sess-12345678", assistant_response="first")
    end(n)
    end(n, turn_id="t2")
    assert sent[1]["message"] == "⏸ Hermes paused [cli …12345678]"


def test_missing_settings_send_nothing():
    n, sent = make(secrets={})
    end(n)
    assert sent == []


def test_clip():
    assert sn.clip("a  b\nc", 10) == "a b c"
    assert sn.clip("abcdef", 4) == "abc…"
    assert sn.clip("abc", 0) == ""


def test_register_wires_three_hooks():
    hooks = {}

    class Ctx:
        def get_config(self, key, default=None):
            return default

        def register_hook(self, name, fn):
            hooks[name] = fn

    sn.register(Ctx())
    assert set(hooks) == {"post_llm_call", "on_session_end", "on_human_input_request"}


class _Handler(BaseHTTPRequestHandler):
    reply = {"jsonrpc": "2.0", "result": {"timestamp": 1}, "id": "x"}
    received = []

    def do_POST(self):
        length = int(self.headers["content-length"])
        self.received.append((self.path, json.loads(self.rfile.read(length))))
        payload = json.dumps(self.reply).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    _Handler.received = []
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_send_signal_posts_json_rpc(server):
    sn.send_signal(server + "/", "+15550000001", "+15550000002", "hello")
    path, body = _Handler.received[0]
    assert path == "/api/v1/rpc"
    assert body["method"] == "send"
    assert body["params"] == {
        "account": "+15550000001",
        "recipient": ["+15550000002"],
        "message": "hello",
    }


def test_send_signal_swallows_rpc_errors_and_network_failures(server, caplog):
    _Handler.reply = {"jsonrpc": "2.0", "error": {"message": "Unregistered user"}, "id": "x"}
    sn.send_signal(server, "a", "b", "hi")
    sn.send_signal("http://127.0.0.1:9", "a", "b", "hi")
    assert "Unregistered user" in caplog.text
    assert "send failed" in caplog.text
