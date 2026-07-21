import logging
import json
import sys
import os
from datetime import datetime


class DevConsoleFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        super().format(record)

        time_str = datetime.now().strftime("%H:%M:%S")
        level = f"[{record.levelname}]"

        metrics_summary = ""
        if hasattr(record, "extra_data"):
            data = record.extra_data
            if "latency_ms" in data and "buffer_size" in data:
                metrics_summary = f" | Latency: {data['latency_ms']}ms | Buffer: {data['buffer_size']}"

        return f"{time_str} {level:<7} : {record.message}{metrics_summary}"


class FileJsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        super().format(record)
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.message,
            "logger": record.name
        }
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        return json.dumps(log_data)


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(DevConsoleFormatter())
    logger.addHandler(console_handler)

    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler(os.path.join("logs", "production.log"), encoding="utf-8")
    file_handler.setFormatter(FileJsonFormatter())
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger