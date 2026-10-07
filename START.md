# SAP BRIM Backend — Developer Quick Start Guide

This guide provides the complete, verified procedure to start the **SAP BRIM GenAI/RAG Backend** from scratch on Windows using PowerShell.

---

## 1. Prerequisites

Ensure you have the following installed before starting:
- **Operating System:** Windows 10/11 (commands in this guide use PowerShell)
- **Python:** Python 3.11.x (tested on 3.11)
- **Docker & Docker Desktop:** Running and configured for Linux containers
- **Git:** For version control
- **API Keys (External):**
  - Groq API Key (`GROQ_API_KEY`) for high-speed inference (e.g. `openai/gpt-oss-120b`), OR OpenAI API Key (`LLM_API_KEY`).
  - *(Optional)* Tavily API Key (`WEB_SEARCH_API_KEY`) for official SAP documentation web fallback search.

---

## 2. Environment Setup

All commands must be run from the repository root (`SAP_Project`).

1. Open PowerShell and navigate to the project directory:
   ```powershell
   cd "C:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project"
   ```

2. Create a Python 3.11 virtual environment if not already present:
   ```powershell
   python -m venv .venv
   ```

3. Enable script execution for the current PowerShell session (if restricted):
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

4. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(Your terminal prompt should now show `(.venv)`).*

---

## 3. Required Environment Configuration (`.env`)

The backend reads configuration from `backend/.env`.

1. Copy the example environment template:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

2. Open `backend/.env` in your editor and configure the variables:

```ini
# ==========================================
# Database Configuration (PostgreSQL + pgvector)
# ==========================================
# Note: Host port is 5434 as defined in docker-compose.yml
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/sap_assistant

# ==========================================
# Security
# ==========================================
JWT_SECRET=your-secure-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ADMIN_API_KEY=your-admin-dev-secret-key

# ==========================================
# LLM Provider Configuration
# ==========================================
# Options: 'groq', 'openai', or 'local'
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=openai/gpt-oss-120b
LLM_MAX_OUTPUT_TOKENS=4000

# (If using OpenAI instead of Groq):
# LLM_PROVIDER=openai
# LLM_API_KEY=sk-your-openai-api-key-here
# LLM_MODEL=gpt-4o-mini

# ==========================================
# RAG & Retrieval Parameters
# ==========================================
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384
TOP_K=30
RERANK_TOP_K=5
RERANKER_MODEL=answerdotai/answerai-colbert-small-v1
RERANKER_ENABLED=True
SIMILARITY_THRESHOLD=0.60
GROUNDING_THRESHOLD=0.65

# ==========================================
# Web Fallback (Optional)
# ==========================================
WEB_FALLBACK_ENABLED=True
WEB_SEARCH_API_KEY=tvly-your_tavily_api_key_here
```

> **Note on `LLM_PROVIDER=local`:** For offline automated testing without incurring LLM API costs or needing an external key, you can set `LLM_PROVIDER=local`.

---

## 4. Database / PostgreSQL Startup

The project requires PostgreSQL 16 with the `pgvector` extension for hybrid vector search.

1. Start the PostgreSQL container in the background:
   ```powershell
   docker compose up -d
   ```

2. Verify that the container is healthy and running on port 5434:
   ```powershell
   docker compose ps
   ```
   **Expected output:**
   ```
   NAME                     IMAGE                    STATUS         PORTS
   sap_assistant_postgres   pgvector/pgvector:pg16   Up ...         0.0.0.0:5434->5432/tcp
   ```

---

## 5. Dependency Installation

With your virtual environment activated, install all required dependencies:

```powershell
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary pgvector pydantic-settings python-dotenv PyJWT bcrypt groq openai sentence-transformers onnxruntime pymupdf tavily-python pytest httpx
```

*(Alternatively, if using the `uv` package manager: `uv pip install ...`)*

---

## 6. Database Migrations & Document Ingestion

### Automatic Table & Index Initialization
Table creation and index setup (`vector` extension, HNSW cosine vector index, and GIN full-text index) are **fully automatic**. When FastAPI starts, the lifespan hook executes `init_db()` in [database.py](file:///c:/Users/Subham%20Patnaik/OneDrive/Desktop/agent/SAP_Project/backend/app/database.py). No manual SQL scripts or Alembic migrations are required.

### Knowledge Base Ingestion (Seed Data)
If starting with an empty database, ingest the SAP BRIM PDF documents located in `knowledge_base/documents/`:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m backend.app.ingestion.ingest
```

This script:
1. Extracts text from all active SAP BRIM PDFs (`SAP CC.pdf`, `SAP CI1-4.pdf`, `SAP FI-CA.pdf`, `pdfdownload.pdf`).
2. Splits text into semantic chunks.
3. Generates vector embeddings using `all-MiniLM-L6-v2`.
4. Stores chunks with pgvector embeddings and GIN full-text indices.

*(Alternatively, trigger ingestion via API: `POST /api/admin/documents/ingest` with header `X-Admin-Key: <ADMIN_API_KEY>`)*.

---

## 7. Backend Startup Command

From the repository root:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected console log:**
```
INFO:     Initializing database and verifying tables...
INFO:     Connected to PostgreSQL database: postgresql://postgres:postgres@localhost:5434/sap_assistant
INFO:     Database tables initialized successfully.
INFO:     pgvector HNSW index and GIN full-text search index verified.
INFO:     SAP Knowledge Assistant backend ready.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 8. API Endpoints & Health Verification

Once running, verify the backend via browser or PowerShell:

- **Root Info:** [http://localhost:8000/](http://localhost:8000/)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **API Prefix:** [http://localhost:8000/api](http://localhost:8000/api)

Quick health verification command:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```
**Expected response:**
```json
{
  "status": "healthy",
  "service": "SAP Knowledge Assistant",
  "version": "1.0.0",
  "knowledge_base": {
    "documents_count": 7,
    "chunks_count": 2840,
    "model": "all-MiniLM-L6-v2"
  }
}
```

---

## 9. Interactive API Documentation (Swagger / ReDoc)

Interactive API exploration is enabled by default:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON):** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 10. How to Run the Test Suite

Run the full automated test suite (all 41 tests) using pytest:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe -s backend/tests/
```

> **Note on `-s` flag:** The `-s` flag (`--capture=no`) is recommended on Windows to prevent standard stream capture conflicts.

### Running Specific Test Suites:
- **Production Improvements & Architecture:**
  ```powershell
  $env:PYTHONPATH="."
  .\.venv\Scripts\pytest.exe -s backend/tests/test_production_improvements.py
  ```
- **Authentication & Tenant Isolation:**
  ```powershell
  $env:PYTHONPATH="."
  .\.venv\Scripts\pytest.exe -s backend/tests/test_auth_and_isolation.py
  ```
- **ColBERT Reranker:**
  ```powershell
  $env:PYTHONPATH="."
  .\.venv\Scripts\pytest.exe -s backend/tests/test_reranker.py
  ```

---

## 11. How to Stop the Backend & Database

### Stopping the FastAPI Backend
Press `Ctrl + C` in the PowerShell terminal where uvicorn is running.

### Stopping PostgreSQL
```powershell
docker compose down
```
*(The pgdata volume persists your ingested chunks and chats).*

### Stopping and Completely Resetting Database (Optional)
To delete all data and start completely fresh:
```powershell
docker compose down -v
```

---

## 12. Common Startup Issues & Verified Fixes

### 1. Port 5434 Mismatch / Connection Refused
- **Symptom:** `Could not connect to PostgreSQL... Falling back to local SQLite engine`.
- **Cause:** PostgreSQL container is not running or `DATABASE_URL` in `backend/.env` is set to standard port `5432` instead of Docker-mapped port `5434`.
- **Fix:** Ensure `DATABASE_URL` specifies port `5434`:
  ```ini
  DATABASE_URL=postgresql://postgres:postgres@localhost:5434/sap_assistant
  ```
  And verify Docker is running: `docker compose up -d`.

### 2. `ModuleNotFoundError: No module named 'backend'`
- **Symptom:** Python throws `ModuleNotFoundError` when running uvicorn or scripts.
- **Cause:** Python's module search path does not include the project root.
- **Fix:** Set `PYTHONPATH` in PowerShell before running:
  ```powershell
  $env:PYTHONPATH="."
  ```

### 3. PowerShell Script Execution Disabled
- **Symptom:** `.\.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system`.
- **Fix:** Run this in your PowerShell window:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 4. Pytest Error: `ValueError: I/O operation on closed file`
- **Symptom:** Pytest fails during session teardown when capturing output.
- **Fix:** Pass `-s` to pytest: `pytest -s backend/tests/`.

### 5. Port 8000 Already in Use
- **Symptom:** `ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`.
- **Fix:** Identify and stop the conflicting process:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
  Stop-Process -Id <OwningProcessId> -Force
  ```
  Or run uvicorn on an alternate port: `--port 8001`.
npm run dev
 .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload