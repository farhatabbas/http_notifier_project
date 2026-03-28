# HTTP Notifier

Modern async notification client.

## Requirements

- Python 3.10+

## Installation

**1. Clone the repo and enter the directory:**

```bash
git clone https://github.com/farhatabbas/http_notifier_project.git
cd http_notifier_project
```

**2. Create and activate a virtual environment:**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**3. Install the package and all dependencies:**

```bash
pip install -e ".[test,dev]"
```

## Running end-to-end

**Terminal 1 — start the test server:**

```bash
python server.py
```

The server listens on `http://localhost:5000` by default. Use `--port` to change it.

**Terminal 2 — send notifications from stdin:**

```bash
# Interactive: type a line and press Enter; it is sent after the interval elapses
notify --url http://localhost:5000/notify --interval 1.0

#feeds the contents of messages.txt into the notify utility to be sent
notify --url http://localhost:5000/notify < messages.txt

# Pipe a file or heredoc
echo -e "alert: disk full\nalert: high cpu\nalert: service down" | \
  notify --url http://localhost:5000/notify --interval 0.5
```

| Flag | Default | Description |
|---|---|---|
| `--url` | *(required)* | URL to POST each notification to |
| `--interval` | `1.0` | Seconds to wait between sends |

**Check received messages:**

```bash
curl http://localhost:5000/messages
```

The server also prints each message with a timestamp as it arrives in Terminal 1.

## Library API

```python
from http_notifier import NotificationClient

client = NotificationClient(
    url="http://localhost:5000/notify",
    max_concurrent=50,   # max parallel HTTP requests (default: 50)
    max_queue_size=0,    # 0 = unbounded; set a limit to shed load under spikes
    on_failure=None,     # optional callable(message, exc) — sync or async
)
client.start()
client.notify("hello")   # non-blocking; returns immediately
await client.stop()      # drains the queue, waits for all requests to finish
```

`on_failure` is called (and awaited if async) for every request that fails with a non-2xx response or a network error.

## Running tests

```bash
pytest
```

Run a single test by name:

```bash
pytest tests/test_client.py::test_concurrency_capped_by_semaphore
```
