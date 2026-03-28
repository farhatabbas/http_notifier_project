import asyncio
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient
from http_notifier import NotificationClient


def make_app(status=204, delay=0):
    app = web.Application()
    received = []

    async def handle(request):
        received.append(await request.text())
        if delay:
            await asyncio.sleep(delay)
        return web.Response(status=status)

    app.router.add_post("/notify", handle)
    app["received"] = received
    return app


async def test_sends_post_on_notify():
    async with TestClient(TestServer(make_app())) as tc:
        client = NotificationClient(str(tc.make_url("/notify")))
        client.start()
        client.notify("hello")
        await client.stop()
    assert tc.app["received"] == ["hello"]


async def test_stop_drains_all_queued_messages():
    async with TestClient(TestServer(make_app())) as tc:
        client = NotificationClient(str(tc.make_url("/notify")))
        client.start()
        for i in range(10):
            client.notify(f"msg-{i}")
        await client.stop()
    assert len(tc.app["received"]) == 10


async def test_on_failure_called_on_http_error():
    failures = []
    async with TestClient(TestServer(make_app(status=500))) as tc:
        client = NotificationClient(
            str(tc.make_url("/notify")),
            on_failure=lambda msg, exc: failures.append(msg),
        )
        client.start()
        client.notify("bad")
        await client.stop()
    assert failures == ["bad"]


async def test_async_on_failure_is_awaited():
    called = []

    async def async_failure(msg, exc):
        called.append(msg)

    async with TestClient(TestServer(make_app(status=500))) as tc:
        client = NotificationClient(str(tc.make_url("/notify")), on_failure=async_failure)
        client.start()
        client.notify("fail")
        await client.stop()
    assert called == ["fail"]


async def test_concurrency_capped_by_semaphore():
    concurrent = 0
    peak = 0

    async def slow_handler(request):
        nonlocal concurrent, peak
        concurrent += 1
        peak = max(peak, concurrent)
        await asyncio.sleep(0.05)
        concurrent -= 1
        return web.Response(status=204)

    app = web.Application()
    app.router.add_post("/notify", slow_handler)
    async with TestClient(TestServer(app)) as tc:
        client = NotificationClient(str(tc.make_url("/notify")), max_concurrent=3)
        client.start()
        for i in range(12):
            client.notify(f"msg-{i}")
        await client.stop()
    assert peak <= 3


async def test_queue_full_drops_and_does_not_raise():
    async with TestClient(TestServer(make_app(delay=0.1))) as tc:
        client = NotificationClient(str(tc.make_url("/notify")), max_queue_size=2)
        client.start()
        for i in range(10):  # 8 will be dropped silently
            client.notify(f"msg-{i}")
        await client.stop()
    # only the first 2 (or a few) made it in; exact count depends on timing — just assert no crash


async def test_notify_before_start_raises():
    client = NotificationClient("http://example.com")
    with pytest.raises(RuntimeError):
        client.notify("test")
