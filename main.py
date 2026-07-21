import sys
import os
import time
import sqlite3
from database import init_db, insert_log, DB_NAME

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from config import DATABASE_FILE_PATH
from buffer import ReactiveStreamBuffer, BufferFullError
from worker import StreamWorker
from logger_config import setup_logger

logger = setup_logger("stream_processor")


class Transaction(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0.0)
    currency: str = Field(..., min_length=3, max_length=3)


buffer = ReactiveStreamBuffer()
worker = StreamWorker(buffer)


def db_logging_worker(method: str, path: str, status_code: int, response_time_ms: float):
    try:
        insert_log(
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms
        )
    except Exception as e:
        logger.error(f"Failed to persist telemetry log to database: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DB and Stream Processor...")
    init_db()
    await worker.start()
    yield
    logger.info("Shutting down Stream Processor...")
    await worker.stop()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    extra_log_metrics = {
        "extra_data": {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": process_time_ms,
            "buffer_size": buffer.size(),
            "client_ip": request.client.host if request.client else "unknown"
        }
    }

    logger.info(
        f"Handled {request.method} {request.url.path} - Status {response.status_code}",
        extra=extra_log_metrics
    )

    if not hasattr(response, "background") or response.background is None:
        response.background = BackgroundTasks()

    response.background.add_task(
        db_logging_worker,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        response_time_ms=process_time_ms
    )

    return response


@app.exception_handler(BufferFullError)
async def custom_backpressure_handler(request: Request, exc: BufferFullError):
    logger.warn("Throttling request due to buffer saturation", extra={"extra_data": {"buffer_size": buffer.size()}})
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Buffer capacity exceeded. System is throttling."}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    extra_log_metrics = {
        "extra_data": {
            "errors": exc.errors(),
            "body": str(getattr(exc, "body", ""))
        }
    }
    logger.error("Validation failed for incoming request", extra=extra_log_metrics)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


@app.post("/clearance/ingest", status_code=status.HTTP_200_OK)
async def ingest_transaction(transaction: Transaction):
    await buffer.enqueue(transaction.model_dump())
    return {"status": "accepted"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "buffer_occupancy": buffer.size(),
        "worker_active": worker.is_running
    }


@app.get("/telemetry/dashboard", status_code=status.HTTP_200_OK)
async def get_telemetry_dashboard():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total_requests, AVG(response_time_ms) as avg_latency FROM api_logs")
            summary = cursor.fetchone()

            cursor.execute("SELECT status_code, COUNT(*) as count FROM api_logs GROUP BY status_code")
            status_distribution = {str(row["status_code"]): row["count"] for row in cursor.fetchall()}

            return {
                "total_processed_requests": summary["total_requests"] or 0,
                "average_latency_ms": round(summary["avg_latency"] or 0.0, 2),
                "status_code_distribution": status_distribution
            }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Failed to retrieve metrics: {str(e)}"}
        )


@app.get("/telemetry/logs", status_code=status.HTTP_200_OK)
async def get_telemetry_logs(limit: int = Query(default=50, ge=1, le=500)):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, method, path, status_code, response_time_ms FROM api_logs ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            logs = [dict(row) for row in cursor.fetchall()]
            return {"logs": logs}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Failed to retrieve logs: {str(e)}"}
        )


@app.post("/clearance/simulate-load", status_code=status.HTTP_200_OK)
async def simulate_load(count: int = Query(default=10, ge=1, le=100)):
    for i in range(count):
        dummy_transaction = {
            "transaction_id": f"sim_{int(time.time())}_{i}",
            "amount": round(10.0 * (i + 1), 2),
            "currency": "USD"
        }
        try:
            await buffer.enqueue(dummy_transaction)
        except BufferFullError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": f"Simulation stopped early at index {i} due to buffer saturation."}
            )
    return {"status": "success", "simulated_transactions_enqueued": count}


if __name__ == "__main__":
    try:
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "dev_clean": {
                    "()": "logger_config.DevConsoleFormatter",
                },
            },
            "handlers": {
                "console": {
                    "formatter": "dev_clean",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
                "uvicorn": {
                    "handlers": ["console"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }

        uvicorn.run("main:app", host="127.0.0.1", port=8000, log_config=log_config)
    except KeyboardInterrupt:
        sys.exit(0)