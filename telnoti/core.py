import sys
import traceback

import requests

from .config import load_config, save_config

_state = {"token": None, "chat_id": None, "initialized": False}


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{_state['token']}/{method}"


def _post(method: str, **kwargs) -> None:
    if not _state["initialized"]:
        print("[telnoti] warning: not initialized. Call telnoti.init() first.", file=sys.stderr)
        return
    try:
        requests.post(_api_url(method), **kwargs)
    except Exception as exc:
        print(f"[telnoti] warning: failed to send ({exc})", file=sys.stderr)


def init(token: str = None, chat_id: str = None) -> None:
    if token and chat_id:
        _state["token"] = token
        _state["chat_id"] = chat_id
    else:
        cfg = load_config()
        _state["token"] = cfg["token"]
        _state["chat_id"] = cfg["chat_id"]
    _state["initialized"] = True


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


def send(text: str) -> None:
    _post("sendMessage", data={"chat_id": _state["chat_id"], "text": text})


def done(text: str) -> None:
    send("✅ " + text)


def error(e: Exception, tb: bool = True) -> None:
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
