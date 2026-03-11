import threading

_timer_state = {"timer": None, "func": None, "interval": None}


def _fire() -> None:
    try:
        _timer_state["func"]()
    except Exception:
        pass
    t = threading.Timer(_timer_state["interval"], _fire)
    t.daemon = True
    _timer_state["timer"] = t
    t.start()


def start_status(func, every_n_seconds: float = 60) -> None:
    _timer_state["func"] = func
    _timer_state["interval"] = every_n_seconds
    t = threading.Timer(every_n_seconds, _fire)
    t.daemon = True
    _timer_state["timer"] = t
    t.start()


def stop_status() -> None:
    if _timer_state["timer"] is not None:
        _timer_state["timer"].cancel()
        _timer_state["timer"] = None
