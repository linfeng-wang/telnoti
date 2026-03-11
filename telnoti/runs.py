"""Persistent run registry for telnoti's /list command."""

import fcntl
import json
import os
import threading
import time

RUNS_PATH = os.path.expanduser("~/.config/.telnoti_runs.json")

_in_process_lock = threading.Lock()


def _locked_read_write(fn):
    with _in_process_lock:
        os.makedirs(os.path.dirname(RUNS_PATH), exist_ok=True)
        with open(RUNS_PATH, "a+") as fh:
            fh.seek(0)
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                content = fh.read()
                data = json.loads(content) if content.strip() else {"runs": {}}
                data = fn(data)
                fh.seek(0)
                fh.truncate()
                json.dump(data, fh, indent=2)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)


def _prune(data):
    """Remove terminal runs older than 24 hours."""
    cutoff = time.time() - 86400
    data["runs"] = {
        rid: r for rid, r in data["runs"].items()
        if r["status"] == "running" or (r.get("ended_at") or 0) > cutoff
    }
    return data


def register_run(run_id: str, name: str, pid: int) -> None:
    def _fn(data):
        data["runs"][run_id] = {
            "run_id": run_id,
            "name": name,
            "pid": pid,
            "started_at": time.time(),
            "ended_at": None,
            "status": "running",
            "last_seen": time.time(),
            "message_count": 0,
            "last_message": None,
        }
        return _prune(data)

    _locked_read_write(_fn)


def update_run(run_id: str, last_message: str = None) -> None:
    def _fn(data):
        if run_id in data["runs"]:
            r = data["runs"][run_id]
            r["last_seen"] = time.time()
            r["message_count"] = r.get("message_count", 0) + 1
            if last_message is not None:
                r["last_message"] = last_message[:100]
        return data

    _locked_read_write(_fn)


def mark_done(run_id: str) -> None:
    def _fn(data):
        if run_id in data["runs"]:
            r = data["runs"][run_id]
            r["status"] = "done"
            r["ended_at"] = time.time()
        return data

    _locked_read_write(_fn)


def mark_error(run_id: str, exc_summary: str = None) -> None:
    def _fn(data):
        if run_id in data["runs"]:
            r = data["runs"][run_id]
            r["status"] = "error"
            r["ended_at"] = time.time()
            if exc_summary:
                r["last_message"] = exc_summary[:100]
        return data

    _locked_read_write(_fn)


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but we can't signal it


def get_runs_for_list() -> dict:
    """Return {"active": [...], "recent": [...]} after stale detection."""
    now = time.time()
    stale_threshold = 5 * 60  # 5 minutes

    dead_ids = []
    active = []
    recent = []

    with _in_process_lock:
        os.makedirs(os.path.dirname(RUNS_PATH), exist_ok=True)
        with open(RUNS_PATH, "a+") as fh:
            fh.seek(0)
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                content = fh.read()
                data = json.loads(content) if content.strip() else {"runs": {}}

                for rid, r in data["runs"].items():
                    if r["status"] == "running":
                        stale = (now - r.get("last_seen", r["started_at"])) > stale_threshold
                        if stale and not _is_pid_alive(r["pid"]):
                            r["status"] = "dead"
                            r["ended_at"] = now
                            dead_ids.append(rid)

                if dead_ids:
                    fh.seek(0)
                    fh.truncate()
                    json.dump(data, fh, indent=2)

                cutoff_24h = now - 86400
                for rid, r in data["runs"].items():
                    if r["status"] == "running":
                        active.append(r.copy())
                    elif r.get("ended_at") and r["ended_at"] > cutoff_24h:
                        recent.append(r.copy())
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    active.sort(key=lambda r: r["started_at"])
    recent.sort(key=lambda r: r.get("ended_at", 0), reverse=True)
    return {"active": active, "recent": recent}
