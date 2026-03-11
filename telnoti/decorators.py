import functools

from . import core


def notify(start: bool = True, end: bool = True, error: bool = True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if start:
                core.send(f"▶️ {func.__name__} started")
            try:
                result = func(*args, **kwargs)
                if end:
                    core.done(f"{func.__name__} finished")
                return result
            except Exception as e:
                if error:
                    core.error(e, tb=True)
                raise

        return wrapper

    return decorator
