import asyncio
from config import BUFFER_MAX_SIZE

class BufferFullError(Exception):
    pass

class ReactiveStreamBuffer:
    def __init__(self):
        self._queue = asyncio.Queue(maxsize=BUFFER_MAX_SIZE)

    async def enqueue(self, item: dict) -> None:
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            raise BufferFullError()

    async def dequeue_batch(self, batch_size: int) -> list[dict]:
        batch = []
        if self._queue.empty():
            return batch

        for _ in range(min(batch_size, self._queue.qsize())):
            try:
                item = self._queue.get_nowait()
                batch.append(item)
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        return batch

    def size(self) -> int:
        return self._queue.qsize()

