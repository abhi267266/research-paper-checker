# Research Paper AI Humanizer & Plagiarism Fixer (Web Platform)

A premium web-based platform designed for researchers and academics to polish and humanize their papers. This platform leverages the Claude AI/OpenAI/Gemini/Groq API to improve flow, eliminate AI detection, and ensure structural uniqueness while maintaining technical accuracy.

## 🚀 Features

- **✨ AI Humanization**: Intelligent rewriting of AI-sounding segments to improve natural flow and evade modern AI detectors.
- **🔍 Plagiarism Analysis**: Deep-scan document extracts for internal inconsistencies and standard plagiarism markers.
- **🛠️ Structural Plagiarism Fixing**: Complete structural restructuring of sentences to bypass plagiarism matchers without losing technical meaning.
- **🤖 AI Phrase Detection**: Sequential scanning for generic AI assistant "artifacts" (e.g., "Certainly!", "I can assist with...") with precise location reporting.
- **📂 Cloud Storage**: Secure file management via local S3 (MinIO), allowing you to download your humanized papers anytime.
- **⚡ Background Processing**: Powered by Celery and Redis to handle complex document processing in the background while you stay productive.

## 🛠️ Quick Start (Docker)

The easiest way to run the entire stack (Frontend, Backend, Database, Workers, and S3 Storage) is using Docker Compose.

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd research-paper-humanizere
   ```

2. **Configure Environment**:
   Update the `backend/.env` file with your LLM API keys and model choices:
   ```env
   # API Keys (Provide at least one)
   CLAUDE_API_KEY=your_anthropic_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here

   # LiteLLM Multi-Tier Routing
   ACTIVE_MODEL_LOW=groq/llama-3.1-8b-instant
   ACTIVE_MODEL_HIGH=groq/llama-3.3-70b-versatile
   ```

3. **Launch the Platform**:
   ```bash
   docker-compose up --build
   ```

4. **Access the App**:
   - **Frontend**: [http://localhost:3000](http://localhost:3000)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Storage Console (MinIO)**: [http://localhost:9001](http://localhost:9001)

## 🏗️ Architecture

- **Frontend**: Next.js 15 (App Router) with a premium, dark-mode design system.
- **Backend**: FastAPI (Python 3.12) with SQLAlchemy and JWT Authentication.
- **Worker**: Celery for asynchronous AI document processing.
- **Data**: PostgreSQL (Database), Redis (Message Broker), and MinIO (S3 Storage).

## 📖 UI Usage

1. **Dashboard**: View your recent jobs and their processing status (Pending, Processing, Completed, Failed).
2. **Upload**: Select a `.docx` or `.txt` file and choose your desired operation (Humanize, Check Plagiarism, etc.).
3. **Download**: Once a job is completed, click the download button to retrieve your polished document directly from the secure storage.

---
*Note: This platform leverages LiteLLM for routing. It requires at least one valid API key (Groq, Anthropic, or Gemini) to function properly.*
