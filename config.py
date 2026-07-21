import os

BUFFER_MAX_SIZE =int(os.getenv("BUFFER_MAX_SIZE", "1000"))

BATCH_SIZE =int(os.getenv("BATCH_SIZE", "50"))
WORKER_POLL_INTERVAL_SEC = float(os.getenv("WORKER_POLL_INTERVAL_SEC", "0.1"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_BASE_DELAY_SEC = float(os.getenv("BACKOFF_BASE_DELAY_SEC", "0.5"))

DLQ_FILE_PATH = os.getenv("DLQ_FILE_PATH", "quarantine_dlq.jsonl")
DATABASE_FILE_PATH = os.getenv("DATABASE_FILE_PATH", "ledger.db")



