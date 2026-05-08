# Developer Documentation: Research Paper Humanizer

Welcome to the development guide for the Research Paper Humanizer platform. This document explains the architecture, directory structure, and design patterns used in this project to help you get started quickly.

## 🏗️ Architecture Overview

The project follows a **Distributed Monolith** architecture with a clear separation between the API layer and the heavy-lifting processing layer.

### Core Components
1.  **Frontend (Next.js)**: A React-based SPA that communicates with the API via proxy. It uses a modern design system with dark mode and glassmorphism.
2.  **API Backend (FastAPI)**: A high-performance Python API that handles authentication, job management, and file coordination.
3.  **Worker (Celery)**: A task queue worker that executes long-running AI humanization and plagiarism fixing tasks.
4.  **Storage (MinIO/S3)**: All files are stored in an S3-compatible object store. No local disk persistence is used for user data.
5.  **State (PostgreSQL & Redis)**: PostgreSQL stores relational data (Users, Jobs), while Redis handles message brokering and caching.

## 📂 Directory Structure

```text
research-paper-humanizere/
├── backend/                # API & Core Logic
│   ├── app/                # Main Application Package
│   │   ├── models/         # SQLAlchemy Database Models
│   │   ├── routers/        # FastAPI Route Handlers
│   │   ├── services/       # Business Logic & External Integrations
│   │   └── worker/         # Celery Task Definitions
│   ├── commands/           # Logic-heavy CLI-style modules (reused by worker)
│   ├── core/               # Shared Utilities (Docx parsing, AI logic)
│   ├── prompts/            # AI Prompt Templates
│   └── main.py             # API Entry point
├── frontend/               # Next.js Application
│   ├── src/
│   │   ├── components/     # Reusable UI Components
│   │   └── app/            # Next.js App Router (Pages & API routes)
├── docs/                   # Documentation (You are here)
└── docker-compose.yml      # Orchestration for the entire stack
```

## 🛠️ Design Patterns & Principles

### 1. Clean Architecture (Separation of Concerns)
- **Routers** only handle HTTP concerns (validation, response codes).
- **Services** encapsulate third-party interactions (S3, GitHub, Claude).
- **Commands** contain the "Domain Logic"—the specific rules for humanizing or fixing text.

### 2. Async Task Offloading
Heavy operations (like calling AI APIs for 20-page documents) are never done in the HTTP request. We use the **Task-Job pattern**:
1. User uploads file.
2. API saves metadata as a "Job" in `PENDING` state and returns a `job_id`.
3. Worker picks up the job, updates state to `PROCESSING`, and eventually `COMPLETED`.
4. Frontend polls the `/jobs` endpoint to update the UI in real-time.

### 3. Containerization First
The project is built to be environment-agnostic. We use **Docker Compose** to manage service discovery. Services connect to each other using internal DNS names (e.g., `http://backend:8000`) instead of hardcoded IP addresses.

## 🚀 Setting Up for Development

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local IDE linting)
- Node.js 20+ (for local frontend work)

### Local Development Flow
1.  **Environment**: Copy `backend/.env.example` to `backend/.env` and add your API keys.
2.  **Launch Dependencies**: Run `docker-compose up postgres redis minio` to start the infrastructure.
3.  **Run Backend**: Use `uv run uvicorn app.main:app --reload` in the `backend/` directory.
4.  **Run Worker**: Use `celery -A app.worker.celery_app worker --loglevel=info` in the `backend/` directory.
5.  **Run Frontend**: Use `npm run dev` in the `frontend/` directory.

## 🤝 Contributing
- **Branching**: Use feature branches (`feature/your-feature`).
- **Linting**: We use `ruff` for Python and `eslint` for TypeScript.
- **Testing**: Add tests in `backend/tests/` using `pytest`.
