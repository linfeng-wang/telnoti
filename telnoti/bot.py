"""Background polling thread for Telegram bot commands."""

import threading
import time

import requests

_bot_state = {"running": False, "thread": None}


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins:
        return f"{hours}h {mins}m"
    return f"{hours}h"


def _build_list_message(runs: dict) -> str:
    now = time.time()
    lines = []

    active = runs.get("active", [])
    recent = runs.get("recent", [])

    if active:
        lines.append("Active runs")
        for r in active:
            elapsed = _fmt_duration(now - r["started_at"])
            count = r.get("message_count", 0)
            last = r.get("last_message")
            suffix = f'running {elapsed}, {count} msgs'
            if last:
                suffix += f' \u2014 \u201c{last}\u201d'
            lines.append(f"  \u2022 {r['name']} ({suffix})")
    else:
        lines.append("Active runs\n  (none)")

    if recent:
        lines.append("")
        lines.append("Last 24h")
        status_icon = {"done": "\u2705", "error": "\u274c", "dead": "\ud83d\udc80"}
        for r in recent:
            icon = status_icon.get(r["status"], "?")
            started = r.get("started_at", 0)
            ended = r.get("ended_at", started)
            duration = _fmt_duration(ended - started)
            lines.append(f"  {icon} {r['name']} ({duration})")

    return "\n".join(lines)


def _handle_update(update: dict, token: str, chat_id: str) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    msg_chat_id = str(message.get("chat", {}).get("id", ""))
    if msg_chat_id != str(chat_id):
        return

    text = message.get("text", "")
    # Handle /list and /list@BotName
    command = text.split()[0] if text.split() else ""
    base_command = command.split("@")[0]
    if base_command != "/list":
        return

    from .runs import get_runs_for_list
    runs = get_runs_for_list()
    reply = _build_list_message(runs)

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": reply},
            timeout=10,
        )
    except Exception as exc:
        import sys
        print(f"[telnoti] warning: failed to send /list reply ({exc})", file=sys.stderr)


def _poll_loop(token: str, chat_id: str) -> None:
    offset = None
    while _bot_state["running"]:
        try:
            params = {"timeout": 20, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params=params,
                timeout=25,
            )
            data = resp.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    _handle_update(update, token, chat_id)
        except Exception:
            time.sleep(5)


def start_polling(token: str, chat_id: str) -> None:
    if _bot_state["running"]:
        return
    _bot_state["running"] = True
    t = threading.Thread(target=_poll_loop, args=(token, chat_id), daemon=True)
    t.start()
    _bot_state["thread"] = t


def stop_polling() -> None:
    _bot_state["running"] = False
    t = _bot_state["thread"]
    if t and t.is_alive():
        t.join(timeout=30)
    _bot_state["thread"] = None
