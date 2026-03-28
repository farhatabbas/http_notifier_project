import asyncio
import argparse
import signal
import sys
from http_notifier import NotificationClient


async def read_and_send(url: str, interval: float) -> None:
    def on_failure(message, exc):
        print(f"[FAILED] '{message}': {exc}", file=sys.stderr)

    client = NotificationClient(url=url, on_failure=on_failure)
    client.start()

    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, shutdown.set)

    try:
        while not shutdown.is_set():
            read_task = asyncio.ensure_future(loop.run_in_executor(None, sys.stdin.readline))
            # Race readline against shutdown so SIGINT unblocks immediately
            done, pending = await asyncio.wait(
                {read_task, asyncio.ensure_future(shutdown.wait())},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            if shutdown.is_set() or read_task not in done:
                break
            line = read_task.result()
            if not line:  # EOF
                break
            message = line.rstrip("\n")
            if message:
                print(f"[SEND] {message}")
                client.notify(message)
                await asyncio.sleep(interval)  # rate-limit only after a real message
    finally:
        print("\n[INFO] Draining queue and shutting down...")
        await client.stop()
        print("[INFO] Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send stdin lines as HTTP notifications.")
    parser.add_argument("--url", required=True, help="Target URL to POST notifications to.")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds to wait between sending messages (default: 1.0).",
    )
    args = parser.parse_args()

    asyncio.run(read_and_send(args.url, args.interval))
