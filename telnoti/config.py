import json
import os

CONFIG_PATH = os.path.expanduser("~/.config/.telnoti.config")


def save_config(token: str, chat_id: str) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"token": token, "chat_id": chat_id}, f)


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"telnoti config not found at {CONFIG_PATH}. "
            "Run telnoti.setup() or `telnoti setup` to configure."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)
