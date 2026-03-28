import asyncio
import aiohttp
import logging
from typing import Callable, Optional, Any


class NotificationClient:
    def __init__(
        self,
        url: str,
        max_concurrent: int = 50,
        max_queue_size: int = 0,
        on_failure: Optional[Callable] = None,
    ):
        self.url = url
        self.on_failure = on_failure
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._inflight: set[asyncio.Task] = set()

    async def _send_request(self, message: Any) -> None:
        async with self._semaphore:
            try:
                async with self._session.post(
                    self.url,
                    data=str(message),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    response.raise_for_status()
            except Exception as e:
                if self.on_failure:
                    result = self.on_failure(message, e)
                    if asyncio.iscoroutine(result):
                        await result
                else:
                    logging.error("Notification failed: %s", e)
            finally:
                self._queue.task_done()  # called after request completes, not before

    async def _worker(self) -> None:
        self._session = aiohttp.ClientSession()
        try:
            while True:
                message = await self._queue.get()
                task = asyncio.create_task(self._send_request(message))
                self._inflight.add(task)
                task.add_done_callback(self._inflight.discard)
        except asyncio.CancelledError:
            # drain any tasks whose task_done() fired but coroutine hasn't fully exited
            await asyncio.gather(*self._inflight, return_exceptions=True)
            await self._session.close()

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    def notify(self, message: Any) -> None:
        if self._worker_task is None:
            raise RuntimeError("Call start() before notify()")
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            logging.warning("Queue full, dropping: %s", message)

    async def stop(self) -> None:
        await self._queue.join()  # wait until all task_done() calls (i.e. requests) complete
        if self._worker_task:
            self._worker_task.cancel()
            await asyncio.gather(self._worker_task, return_exceptions=True)
