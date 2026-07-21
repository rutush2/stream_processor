import asyncio
import json
import sqlite3
import aiofiles
from config import (
    BATCH_SIZE,
    WORKER_POLL_INTERVAL_SEC,
    MAX_RETRIES,
    BACKOFF_BASE_DELAY_SEC,
    DLQ_FILE_PATH,
    DATABASE_FILE_PATH
)
from buffer import ReactiveStreamBuffer

class StreamWorker:
    def __init__(self, buffer: ReactiveStreamBuffer):
        self.buffer = buffer
        self.is_running = False
        self._loop_task = None
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(DATABASE_FILE_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    transaction_id TEXT PRIMARY KEY,
                    amount REAL,
                    currency TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    async def start(self) -> None:
        self.is_running = True
        self._loop_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _worker_loop(self) -> None:
        while self.is_running:
            batch = await self.buffer.dequeue_batch(BATCH_SIZE)
            if batch:
                await self._process_batch_with_retry(batch)
            else:
                await asyncio.sleep(WORKER_POLL_INTERVAL_SEC)

    async def _process_batch_with_retry(self, batch: list[dict]) -> None:
        for attempt in range(MAX_RETRIES):
            try:
                failed_items = await asyncio.to_thread(self._write_batch_to_ledger, batch)
                if failed_items:
                    for item in failed_items:
                        await self._quarantine(item)
                return
            except sqlite3.OperationalError:
                if attempt == MAX_RETRIES - 1:
                    for item in batch:
                        await self._quarantine(item)
                    return
                delay = BACKOFF_BASE_DELAY_SEC * (2 ** attempt)
                await asyncio.sleep(delay)
            except Exception:
                for item in batch:
                    await self._quarantine(item)
                return

    def _write_batch_to_ledger(self, batch: list[dict]) -> list[dict]:
        failed_items = []
        with sqlite3.connect(DATABASE_FILE_PATH, timeout=10.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            for transaction in batch:
                try:
                    with conn:
                        conn.execute(
                            "INSERT INTO ledger (transaction_id, amount, currency) VALUES (?, ?, ?)",
                            (transaction["transaction_id"], transaction["amount"], transaction["currency"])
                        )
                except sqlite3.IntegrityError:
                    failed_items.append(transaction)
        return failed_items

    async def _quarantine(self, transaction: dict) -> None:
        async with aiofiles.open(DLQ_FILE_PATH, mode="a") as f:
            await f.write(json.dumps(transaction) + "\n")