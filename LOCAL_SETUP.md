# Local Development Setup Guide

If you prefer to run the Research Paper Humanizer platform locally without Docker, follow these instructions. 

This setup requires you to run multiple terminal windows to host the different services (Frontend, Backend API, Celery Worker, Redis, and MinIO).

## Prerequisites
- **Node.js** (v18+ recommended)
- **Python** (3.12+ recommended)
- **Redis** installed locally (or via a lightweight docker container)
- **MinIO** installed locally (or via a lightweight docker container)
- A valid LLM API key (Groq, Anthropic, or Gemini)

---

## 1. Setup Infrastructure Dependencies
You will need Redis (for the Celery broker) and MinIO (for S3 storage) running.

**Option A: Run them locally via Docker (Easiest)**
```bash
# Terminal 1: Run Redis
docker run -p 6379:6379 redis:alpine

# Terminal 2: Run MinIO
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

**Option B: Native Install**
Install Redis via Homebrew (`brew install redis`) and MinIO natively.

---

## 2. Setup the Backend Environment

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   # Using standard venv and pip
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Or using uv (if installed)
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to ensure `REDIS_URL=redis://localhost:6379/0` and that your API keys (`GROQ_API_KEY`, etc.) are set.*

---

## 3. Run the Backend API

In a new terminal window (with your virtual environment activated):

```bash
cd backend
# Run the database migrations (if necessary)
alembic upgrade head

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at `http://localhost:8000`.

---

## 4. Run the Background Worker

In a new terminal window (with your virtual environment activated):

```bash
cd backend
# Start the Celery worker
celery -A app.worker.celery_app worker --loglevel=info
```
The worker will connect to your local Redis instance and wait for document jobs.

---

## 5. Setup and Run the Frontend

In a new terminal window:

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. Start the Next.js development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`.

---

## Summary of Ports
- **3000**: Next.js Frontend
- **8000**: FastAPI Backend
- **6379**: Redis Broker
- **9000**: MinIO S3 API
- **9001**: MinIO Web Console
