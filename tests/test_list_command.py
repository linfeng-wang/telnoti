"""Tests for /list command: run registry and bot polling."""

import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

import telnoti.runs as runs_mod
import telnoti.bot as bot_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_id():
    import uuid
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def patch_runs_path(tmp_path, monkeypatch):
    path = str(tmp_path / "telnoti_runs.json")
    monkeypatch.setattr(runs_mod, "RUNS_PATH", path)
    # Reset the in-process lock between tests (create fresh one)
    monkeypatch.setattr(runs_mod, "_in_process_lock", threading.Lock())
    yield path


@pytest.fixture(autouse=True)
def reset_bot_state():
    bot_mod._bot_state["running"] = False
    bot_mod._bot_state["thread"] = None
    yield
    bot_mod._bot_state["running"] = False


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

def test_register_run_creates_record(tmp_path):
    rid = _make_run_id()
    runs_mod.register_run(rid, "test.py · PID 1 · 12:00", 1)

    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)

    assert rid in data["runs"]
    r = data["runs"][rid]
    assert r["status"] == "running"
    assert r["pid"] == 1
    assert r["message_count"] == 0


def test_update_run_bumps_count():
    rid = _make_run_id()
    runs_mod.register_run(rid, "train.py", os.getpid())
    runs_mod.update_run(rid, last_message="hello")
    runs_mod.update_run(rid, last_message="world")

    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)

    r = data["runs"][rid]
    assert r["message_count"] == 2
    assert r["last_message"] == "world"


def test_mark_done_sets_status():
    rid = _make_run_id()
    runs_mod.register_run(rid, "train.py", os.getpid())
    runs_mod.mark_done(rid)

    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)

    r = data["runs"][rid]
    assert r["status"] == "done"
    assert r["ended_at"] is not None


def test_mark_error_sets_status():
    rid = _make_run_id()
    runs_mod.register_run(rid, "train.py", os.getpid())
    runs_mod.mark_error(rid, exc_summary="ValueError: bad")

    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)

    r = data["runs"][rid]
    assert r["status"] == "error"
    assert r["ended_at"] is not None


def test_stale_run_detected_as_dead():
    rid = _make_run_id()
    # Use a PID that almost certainly doesn't exist
    fake_pid = 999999
    runs_mod.register_run(rid, "dead.py", fake_pid)

    # Backdate last_seen to > 5 minutes ago
    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)
    data["runs"][rid]["last_seen"] = time.time() - 400
    with open(runs_mod.RUNS_PATH, "w") as f:
        json.dump(data, f)

    result = runs_mod.get_runs_for_list()
    # Should appear in recent as dead (or not in active)
    assert all(r["run_id"] != rid for r in result["active"])
    dead_runs = [r for r in result["recent"] if r["run_id"] == rid]
    assert dead_runs, "dead run should appear in recent"
    assert dead_runs[0]["status"] == "dead"


def test_active_run_with_real_pid():
    rid = _make_run_id()
    runs_mod.register_run(rid, "live.py", os.getpid())

    result = runs_mod.get_runs_for_list()
    active_ids = [r["run_id"] for r in result["active"]]
    assert rid in active_ids


def test_old_completed_run_excluded():
    rid = _make_run_id()
    runs_mod.register_run(rid, "old.py", os.getpid())

    # Manually set ended_at to > 24h ago
    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)
    data["runs"][rid]["status"] = "done"
    data["runs"][rid]["ended_at"] = time.time() - 90000
    with open(runs_mod.RUNS_PATH, "w") as f:
        json.dump(data, f)

    result = runs_mod.get_runs_for_list()
    all_ids = [r["run_id"] for r in result["active"] + result["recent"]]
    assert rid not in all_ids


def test_prune_removes_old_records():
    rid_old = _make_run_id()
    rid_new = _make_run_id()

    runs_mod.register_run(rid_new, "new.py", os.getpid())

    # Insert an old terminal run directly
    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)
    data["runs"][rid_old] = {
        "run_id": rid_old,
        "name": "old.py",
        "pid": 1,
        "started_at": time.time() - 100000,
        "ended_at": time.time() - 90000,
        "status": "done",
        "last_seen": time.time() - 90000,
        "message_count": 0,
        "last_message": None,
    }
    with open(runs_mod.RUNS_PATH, "w") as f:
        json.dump(data, f)

    # register_run triggers _prune
    rid_trigger = _make_run_id()
    runs_mod.register_run(rid_trigger, "trigger.py", os.getpid())

    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)
    assert rid_old not in data["runs"]


# ---------------------------------------------------------------------------
# Bot formatting tests
# ---------------------------------------------------------------------------

def test_list_reply_format():
    fake_runs = {
        "active": [
            {
                "run_id": "abc",
                "name": "train.py · PID 1 · 14:32",
                "pid": 1,
                "started_at": time.time() - 3600,
                "ended_at": None,
                "status": "running",
                "last_seen": time.time(),
                "message_count": 5,
                "last_message": "Epoch 3/10",
            }
        ],
        "recent": [],
    }
    with patch.object(bot_mod, "_build_list_message", wraps=bot_mod._build_list_message):
        msg = bot_mod._build_list_message(fake_runs)

    assert "Active runs" in msg
    assert "train.py · PID 1 · 14:32" in msg
    assert "5 msgs" in msg


def test_handle_update_ignores_wrong_chat():
    update = {
        "update_id": 1,
        "message": {
            "chat": {"id": 99999},
            "text": "/list",
        }
    }
    with patch("requests.post") as mock_post:
        bot_mod._handle_update(update, token="fake", chat_id="12345")
        mock_post.assert_not_called()


def test_handle_update_responds_to_list():
    update = {
        "update_id": 1,
        "message": {
            "chat": {"id": 12345},
            "text": "/list",
        }
    }
    fake_runs = {"active": [], "recent": []}
    with patch("telnoti.bot.runs_mod" if hasattr(bot_mod, "runs_mod") else "telnoti.runs.get_runs_for_list",
               return_value=fake_runs) as _:
        pass  # just test the call chain below

    with patch("telnoti.runs.get_runs_for_list", return_value=fake_runs):
        with patch("requests.post") as mock_post:
            bot_mod._handle_update(update, token="fake", chat_id="12345")
            mock_post.assert_called_once()


def test_start_polling_idempotent():
    with patch("telnoti.bot._poll_loop"):
        bot_mod.start_polling("fake-token", "12345")
        t1 = bot_mod._bot_state["thread"]
        bot_mod.start_polling("fake-token", "12345")
        t2 = bot_mod._bot_state["thread"]
        assert t1 is t2
    bot_mod._bot_state["running"] = False


def test_fmt_duration():
    fmt = bot_mod._fmt_duration
    assert fmt(30) == "30s"
    assert fmt(59) == "59s"
    assert fmt(60) == "1m"
    assert fmt(90) == "1m"
    assert fmt(3600) == "1h"
    assert fmt(3661) == "1h 1m"


def test_concurrent_update_run():
    rid = _make_run_id()
    runs_mod.register_run(rid, "concurrent.py", os.getpid())

    errors = []

    def do_update():
        try:
            runs_mod.update_run(rid)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=do_update) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors

    import json
    with open(runs_mod.RUNS_PATH) as f:
        data = json.load(f)
    assert data["runs"][rid]["message_count"] == 10
