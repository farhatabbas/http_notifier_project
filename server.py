"""
Simple Flask server for testing the HTTP notifier end-to-end.

Usage:
    python server.py
    python server.py --port 5000
"""

import argparse
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)
received: list[dict] = []


@app.post("/notify")
def notify():
    message = request.get_data(as_text=True)
    entry = {"time": datetime.now().isoformat(timespec="seconds"), "message": message}
    received.append(entry)
    print(f"[{entry['time']}] {message}")
    return "", 204


@app.get("/messages")
def messages():
    return {"count": len(received), "messages": received}


def main() -> None:
    parser = argparse.ArgumentParser(description="Test server for HTTP notifier.")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000).")
    args = parser.parse_args()

    app.run(port=args.port, debug=True)


if __name__ == "__main__":
    main()
