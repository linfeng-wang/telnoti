import atexit
import os
import sys
import time
import traceback
import uuid

import requests

from .config import load_config, save_config

_state = {"token": None, "chat_id": None, "initialized": False, "enabled": True, "run_id": None}


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{_state['token']}/{method}"


def _post(method: str, **kwargs) -> None:
    if not _state["initialized"]:
        print("[telnoti] warning: not initialized. Call telnoti.init() first.", file=sys.stderr)
        return
    if not _state["enabled"]:
        return
    try:
        requests.post(_api_url(method), **kwargs)
    except Exception as exc:
        print(f"[telnoti] warning: failed to send ({exc})", file=sys.stderr)


def _on_exit() -> None:
    run_id = _state.get("run_id")
    if not run_id:
        return
    from .runs import mark_done
    try:
        mark_done(run_id)
    except Exception:
        pass


def init(token: str = None, chat_id: str = None, run_name: str = None) -> None:
    if token and chat_id:
        _state["token"] = token
        _state["chat_id"] = chat_id
    else:
        cfg = load_config()
        _state["token"] = cfg["token"]
        _state["chat_id"] = cfg["chat_id"]
    _state["initialized"] = True

    run_id = str(uuid.uuid4())
    _state["run_id"] = run_id

    if run_name:
        display_name = run_name
    else:
        script = os.path.basename(sys.argv[0]) if sys.argv[0] else "<shell>"
        ts = time.strftime("%H:%M", time.localtime())
        display_name = f"{script} \u00b7 PID {os.getpid()} \u00b7 {ts}"

    from .runs import register_run
    register_run(run_id=run_id, name=display_name, pid=os.getpid())
    atexit.register(_on_exit)

    from .bot import start_polling
    start_polling(_state["token"], _state["chat_id"])


def setup() -> None:
    print("Go to https://t.me/BotFather, create a bot, and copy the token.")
    token = input("Bot token: ").strip()
    print("Send any message to your bot, then open:")
    print(f"  https://api.telegram.org/bot{token}/getUpdates")
    print("Copy the chat.id from the response.")
    chat_id = input("Chat ID: ").strip()
    save_config(token, chat_id)
    print(f"Config saved to ~/.config/.telnoti.config")
    _state["token"] = token
    _state["chat_id"] = chat_id
    _state["initialized"] = True


def disable() -> None:
    _state["enabled"] = False


def enable() -> None:
    _state["enabled"] = True


def send(text: str) -> None:
    _post("sendMessage", data={"chat_id": _state["chat_id"], "text": text})
    if _state.get("run_id") and _state["enabled"]:
        from .runs import update_run
        update_run(_state["run_id"], last_message=text[:100])


def done(text: str) -> None:
    if _state.get("run_id"):
        from .runs import mark_done
        mark_done(_state["run_id"])
    send("✅ " + text)


def error(e: Exception, tb: bool = True) -> None:
    if _state.get("run_id"):
        from .runs import mark_error
        mark_error(_state["run_id"], exc_summary=f"{type(e).__name__}: {e}")
    exc_type = type(e).__name__
    msg = f"❌ {exc_type}: {e}"
    if tb:
        tb_str = traceback.format_exc()
        if tb_str and tb_str.strip() != "NoneType: None":
            msg += f"\n{tb_str}"
    send(msg)


def send_image(path: str, caption: str = None) -> None:
    data = {"chat_id": _state["chat_id"]}
    if caption:
        data["caption"] = caption
    if not _state["initialized"]:
        print("[telnoti] warning: not initialized. Call telnoti.init() first.", file=sys.stderr)
        return
    if not _state["enabled"]:
        return
    try:
        with open(path, "rb") as f:
            requests.post(_api_url("sendPhoto"), data=data, files={"photo": f})
    except Exception as exc:
        print(f"[telnoti] warning: failed to send image ({exc})", file=sys.stderr)


def catch_all() -> None:
    def _hook(exc_type, exc_value, exc_tb):
        error(exc_value, tb=True)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
