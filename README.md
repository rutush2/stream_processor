```markdown
# stream_processor

A high-performance, asynchronous FastAPI backend paired with a real-time Streamlit analytics dashboard. This project implements Command Query Responsibility Segregation (CQRS) and reactive stream buffering to manage high-throughput telemetry ingestion without blocking main request lifecycles.

## 🛠️ Project Structure

```text
stream_processor/
├── logs/                # File-based application log outputs
├── buffer.py            # Reactive stream buffer implementation
├── config.py            # Global application settings
├── dashboard.py         # Real-time Streamlit telemetry visualization interface
├── database.py          # SQLite persistence schema and connection handlers
├── logger_config.py     # Custom structured log formatters
├── main.py              # Main FastAPI application and routing logic
├── README.md            # Project documentation
├── stress_test.py       # Asynchronous load testing script
└── worker.py            # Stream processing background worker

```

```

---

### 2. Setting Up the Virtual Environment

Run this command in your IDE terminal to create and activate the virtual environment:

```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate

```

---

### 3. Installing Dependencies

Install the required packages into your active virtual environment:

```bash
pip install -r requirements.txt

```

---

### 4. Running the System

Start the FastAPI backend server:

```bash
python -m uvicorn main:app --reload

```

* **Interactive API Documentation (Swagger UI):** http://127.0.0.1:8000/docs
* **Health Check Endpoint:** http://127.0.0.1:8000/health'

---

### 5. Launching the Streamlit Dashboard

Open a second terminal window, activate `.venv`, and run:

```bash
streamlit run dashboard.py

```

* **Dashboard UI:** `http://localhost:8501`

---

### 6. Loading the Simulation

Open a third terminal window, activate `.venv`, and run the stress test:

```bash
python stress_test.py

```

---

### 7. Interactive Endpoints Overview

* `POST /clearance/ingest` — Enqueues transaction payloads into the buffer.
* `GET /telemetry/dashboard` — Returns summary metrics (latency and status codes).
* `GET /telemetry/logs` — Fetches backend execution logs.
* `POST /clearance/simulate-load` — Triggers an automated batch load simulation.

---

