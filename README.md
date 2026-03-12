# telnoti

Send Telegram notifications from Python scripts and notebooks. Zero dependencies beyond `requests`.

## Installation

```bash
pip install telnoti
```

## One-time Setup

**Interactive (Python):**
```python
import telnoti as tn
tn.setup()
```

**CLI:**
```bash
telnoti setup
```

Both prompt for your bot token (from [@BotFather](https://t.me/BotFather)) and chat ID, then save to `~/.config/.telnoti.config`.

## Usage

### Basic

```python
import telnoti as tn

tn.init()          # load saved config
tn.send("hello")
tn.done("training complete")

try:
    1 / 0
except Exception as e:
    tn.error(e)    # sends ❌ ZeroDivisionError: ... with traceback
```

### Training Loop with Status Updates

```python
import telnoti as tn

tn.init()

def status():
    tn.send(f"Epoch {current_epoch}/{total_epochs}, loss={loss:.4f}")

tn.start_status(status, every_n_seconds=300)  # every 5 minutes

for epoch in range(total_epochs):
    # ... training ...
    pass

tn.stop_status()
tn.done("Training finished!")
```

### Decorator

```python
import telnoti as tn

tn.init()

@tn.notify(start=True, end=True, error=True)
def run_experiment():
    # ... long-running code ...
    pass

run_experiment()
# sends: ▶️ run_experiment started
# sends: ✅ run_experiment finished  (or ❌ ... on error)
```

### Jupyter Notebook

```python
import telnoti as tn
tn.init()

# In a cell you want to be notified when complete:
# ... heavy computation ...
tn.done("Cell finished")
```

### Send Images

```python
tn.send_image("plot.png", caption="Loss curve")
```

### Catch All Unhandled Exceptions

```python
import telnoti as tn
tn.init()
tn.catch_all()  # any uncaught exception will be sent to Telegram
```

## Bot Commands

Send `/list` to your bot to see all active and recently completed runs:

```
Active runs
  • train.py · PID 12345 · 14:32 (running 1h 23m, 42 msgs — "Epoch 8/10")

Last 24h
  ✅ data_prep.py · PID 10022 · 09:15 (2h 41m)
  ❌ train_v2.py · PID 11500 · 11:00 (45m)
  💀 overnight.py · PID 8800 · 02:00 (7h 12m)
```

The polling thread starts automatically on `tn.init()`. Active runs are always shown; completed/errored runs appear for 24 hours. Dead runs (process killed, last seen > 5 min ago) are shown with 💀.

## Version

```python
import telnoti
print(telnoti.__version__)  # e.g. 0.2.0
```

```bash
telnoti --version  # telnoti 0.2.0
telnoti -V
```

## API

| Function | Description |
|---|---|
| `init(token=None, chat_id=None, run_name=None)` | Initialize (loads config if no args); `run_name` overrides auto-detected name |
| `setup()` | Interactive config wizard |
| `send(text)` | Send a message |
| `done(text)` | Send ✅ message |
| `error(e, tb=True)` | Send ❌ error with optional traceback |
| `send_image(path, caption=None)` | Send an image file |
| `start_status(func, every_n_seconds=60)` | Schedule periodic status messages |
| `stop_status()` | Cancel the status timer |
| `notify(start, end, error)` | Decorator for notifications |
| `catch_all()` | Hook `sys.excepthook` to send all unhandled errors |
| `disable()` | Suppress all notifications (no messages sent) |
| `enable()` | Re-enable notifications |
