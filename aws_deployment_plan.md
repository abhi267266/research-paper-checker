# AWS Deployment Strategy: Research Paper Humanizer

Based on your requirement for **serverless architectures**, **free tiers**, and **scale-to-zero** capabilities to minimize costs, here is the recommended deployment strategy for your full-stack application on AWS.

Your current architecture consists of:
*   **Frontend**: Next.js
*   **Backend API**: FastAPI
*   **Worker**: Celery
*   **Queue**: Redis
*   **Database**: PostgreSQL
*   **Storage**: MinIO (S3-compatible)

---

## Service Mapping & Recommendations

### 1. Object Storage (Replacing MinIO)
*   **AWS Service**: **Amazon S3**
*   **Why**: MinIO is literally an open-source clone of S3. Migrating to actual AWS S3 requires zero code changes (just update the `.env` variables to point to AWS instead of `http://minio:9000`).
*   **Cost**: Huge free tier (5GB storage, 20,000 GET requests/month). Scales exactly to zero when unused.

### 2. Frontend (Next.js)
*   **AWS Service**: **AWS Amplify Hosting**
*   **Why**: It natively supports Next.js Server-Side Rendering (SSR). You just connect your GitHub repository, and it automatically builds and deploys on every push.
*   **Cost**: Free tier includes 1000 build minutes and 15GB of bandwidth per month. Pay-per-use after that (fractions of a penny per request). Scales to zero.

### 3. Backend API (FastAPI)
*   **AWS Service**: **AWS Lambda + API Gateway** (Using the `Mangum` library)
*   **Why**: Instead of running a persistent Docker container, you wrap your FastAPI app in a library called `Mangum`. This allows FastAPI to run inside AWS Lambda. When a user makes a request, AWS spins up a Lambda function, runs the FastAPI route, and shuts it down.
*   **Cost**: 1 Million free requests per month permanently. Scales exactly to zero when no one is using the app.

### 4. Database (PostgreSQL)
*   **AWS Option**: **Amazon RDS (db.t4g.micro)**
    *   *Cost*: AWS offers 750 free hours per month for 12 months. It does **not** scale to zero, but it is free for the first year. (Note: AWS Aurora Serverless v2 exists, but it has a minimum cost of ~$45/month).
*   **Better Alternative (Non-AWS)**: **Neon.tech** or **Supabase**
    *   *Why*: If you truly want scale-to-zero Postgres, third-party serverless Postgres providers are currently better and cheaper than AWS for small projects. They offer generous, permanent free tiers that pause compute when not in use.

### 5. Background Workers (Celery & Redis)
> [!WARNING]
> Celery and Redis are fundamentally designed to run 24/7. They **do not** scale to zero. To achieve a true serverless architecture, you have two distinct paths:

#### Path A: The "No Code Changes" Approach (Free Tier EC2)
Keep Celery and Redis exactly as they are, but host them on a small server.
*   **Service**: **Amazon EC2 (t4g.micro)**
*   **How**: Spin up a free-tier Linux server. Install Docker, and run just your `worker` and `redis` containers on it.
*   **Cost**: 750 free hours per month for 12 months. Does not scale to zero, but is completely free for a year.

#### Path B: The "True Serverless" Approach (Refactor Required)
Remove Celery and Redis entirely and embrace AWS native serverless queues.
*   **Services**: **Amazon SQS** (Queue) + **AWS Lambda** (Worker)
*   **How**: 
    1. When a user submits a job in FastAPI, instead of calling `celery_app.send_task()`, the backend sends a JSON message to an SQS Queue.
    2. SQS automatically triggers a background AWS Lambda function.
    3. The Lambda function runs your python scripts (`humanize.py`, `check.py`) and saves the result to the DB and S3.
*   **Cost**: SQS provides 1 Million free messages per month. Lambda provides 1 Million free invocations. This scales **exactly to zero** and eliminates the need to manage Redis entirely.

---

## Step-by-Step Deployment Action Plan

If you want to proceed with this, here is the order of operations:

1.  **Infrastructure Setup**:
    *   Create an AWS Account.
    *   Create an S3 Bucket (e.g., `research-paper-data-prod`).
    *   Set up a hosted PostgreSQL database (RDS free tier or Neon).
2.  **Code Adjustments**:
    *   Install `mangum` and wrap your FastAPI `app.py` so it can run on Lambda.
    *   Decide between Path A (EC2 for Celery) or Path B (SQS + Lambda refactor).
3.  **Deployment**:
    *   Deploy the Backend Lambda using a framework like **Serverless Framework** or **AWS SAM**.
    *   Connect AWS Amplify to your GitHub repo to deploy the Next.js frontend, pointing its environment variables to your new API Gateway URL.

**How would you like to proceed?** If you'd like, we can start by refactoring the backend to use `Mangum` to prepare it for Lambda, or we can look into converting Celery to SQS!
