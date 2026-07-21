import asyncio
import random
import sys
import httpx

TARGET_URL = "http://127.0.0.1:8000/clearance/ingest"
CONCURRENT_REQUESTS = 2000


async def send_transaction(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, tx_id: str, amount: float,
                           currency: str) -> int:
    payload = {
        "transaction_id": tx_id,
        "amount": amount,
        "currency": currency
    }
    async with semaphore:
        try:
            response = await client.post(TARGET_URL, json=payload, timeout=5.0)
            return response.status_code
        except httpx.RequestError:
            return 0


async def run_stress_test():
    print(f"Starting stress test: Sending {CONCURRENT_REQUESTS} transactions...")
    print("Press Ctrl+C at any time to cancel.")

    semaphore = asyncio.Semaphore(100)

    limits = httpx.Limits(max_keepalive_connections=200, max_connections=1000)

    async with httpx.AsyncClient(limits=limits) as client:
        tasks = []
        for i in range(CONCURRENT_REQUESTS):
            tx_id = f"tx_{i}"
            if i % 10 == 0:
                tx_id = f"tx_{random.randint(0, 50)}"

            amount = round(random.uniform(10.0, 5000.0), 2)
            currency = random.choice(["USD", "EUR", "GBP"])

            tasks.append(send_transaction(client, semaphore, tx_id, amount, currency))

        try:
            results = await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("\nTest cancelled by user.")
            return

        status_counts = {}
        for status_code in results:
            status_counts[status_code] = status_counts.get(status_code, 0) + 1

        print("\n--- Stress Test Completed ---")
        print(f"Total Transactions Dispatched: {CONCURRENT_REQUESTS}")
        for status_code, count in sorted(status_counts.items()):
            if status_code == 0:
                print(f"Connection Failures: {count}")
            elif status_code == 200:
                print(f"HTTP 200 OK (Accepted into buffer): {count}")
            elif status_code == 503:
                print(f"HTTP 503 Service Unavailable (Throttled via backpressure): {count}")
            else:
                print(f"HTTP {status_code}: {count}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(run_stress_test())
    except KeyboardInterrupt:
        print("\nExecution stopped via Ctrl+C.")
        sys.exit(0)