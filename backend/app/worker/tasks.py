"""
Celery tasks — each task wraps an existing commands/* module.
They operate on files from/to S3 via temp paths.
"""
import json
import logging
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.worker.celery_app import celery_app
from app.db import SessionLocal
from app.models.job import Job, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED
from app.models.user import User
from app.services import s3_service

# Make existing CLI modules importable
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
print(f"DEBUG: tasks.py __file__: {__file__}")
print(f"DEBUG: Calculated _BACKEND_ROOT: {_BACKEND_ROOT}")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
print(f"DEBUG: sys.path: {sys.path}")
try:
    print(f"DEBUG: /app contents: {os.listdir('/app')}")
    print(f"DEBUG: /app/commands contents: {os.listdir('/app/commands')}")
except Exception as e:
    print(f"DEBUG: Error listing /app: {e}")

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_job(db, job_id: str) -> Job:
    return db.query(Job).filter(Job.id == job_id).first()


def _mark(db, job: Job, status: str, **kwargs):
    job.status = status
    job.updated_at = datetime.now(timezone.utc)
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()


class DbLogWriter:
    def __init__(self, db, job_id: str):
        self.db = db
        self.job_id = job_id
        self.buffer = ""
        self.full_output = ""
        
    def write(self, s):
        if sys.__stdout__ is not None:
            sys.__stdout__.write(s)
            sys.__stdout__.flush()
        if not s:
            return
        self.buffer += s
        self.full_output += s
        # Flush to DB on newlines to provide real-time updates
        if "\n" in s:
            self.flush()
            
    def flush(self):
        if not self.buffer:
            return
        try:
            job = self.db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.logs = (job.logs or "") + self.buffer
                self.db.commit()
            self.buffer = ""
        except Exception as e:
            logger.error("Failed to flush log to DB: %s", e)
            self.db.rollback()

    def getvalue(self):
        return self.full_output


class JobLogger:
    """Context manager to capture stdout and stream logs to the DB."""
    def __init__(self, db, job_id: str):
        self.db = db
        self.job_id = job_id
        self.writer = DbLogWriter(db, job_id)

    def __enter__(self):
        from contextlib import redirect_stdout
        self.redirector = redirect_stdout(self.writer) # type: ignore
        self.redirector.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.redirector.__exit__(exc_type, exc_val, exc_tb)
        self.writer.flush()
        
    @property
    def io(self):
        return self.writer


def _download_input(job: Job) -> str:
    """Download input file from S3 to a temp path and return the path."""
    ext = os.path.splitext(job.input_s3_key)[1] or ".txt"
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.close()
    try:
        s3_service.download_file(s3_service.BUCKET_UPLOADS, job.input_s3_key, tmp.name)
        size = os.path.getsize(tmp.name)
        print(f"DEBUG: Downloaded {job.input_s3_key} to {tmp.name}, size: {size} bytes")
        if size == 0:
            raise ValueError(f"Downloaded file {job.input_s3_key} is empty")
    except Exception as e:
        print(f"DEBUG: Download failed: {e}")
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise e
    return tmp.name


def _download_context(job: Job) -> str:
    """Return codebase context string (or empty string)."""
    if not job.context_s3_key:
        return ""
    raw = s3_service.download_bytes(s3_service.BUCKET_CODEBASE, job.context_s3_key)
    return json.loads(raw).get("context", "")


def _upload_output(local_path: str, job_id: str, ext: str) -> str:
    key = f"{job_id}{ext}"
    s3_service.upload_file(local_path, s3_service.BUCKET_OUTPUTS, key)
    return key


# ── tasks ─────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="humanize")
def humanize_task(self, job_id: str):
    # Ensure sys.path is correct inside the worker subprocess
    _BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _BACKEND_ROOT not in sys.path:
        sys.path.insert(0, _BACKEND_ROOT)
    
    from commands.humanize import execute  # noqa

    db = SessionLocal()
    job = None
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        _mark(db, job, STATUS_PROCESSING)

        input_path = _download_input(job)
        context = _download_context(job)
        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        output_path = tmp.name
        tmp.close()

        args = SimpleNamespace(
            input=input_path,
            threshold=job.params.get("threshold", 5),
            out=output_path,
            codebase="",
        )

        import core.extractor as extractor  # noqa
        extractor.extract_codebase_context = lambda codebase_path: context
        # Ensure get_architectural_memory uses the mocked context
        orig_get_memory = extractor.get_architectural_memory
        extractor.get_architectural_memory = lambda codebase_path: orig_get_memory("")

        with JobLogger(db, job_id):
            execute(args)

        output_key = _upload_output(output_path, job_id, ".docx")
        _mark(db, job, STATUS_COMPLETED, output_s3_key=output_key)
        logger.info("humanize job %s completed", job_id)
    except Exception as exc:
        logger.exception("humanize job %s failed: %s", job_id, exc)
        if job:
            _mark(db, job, STATUS_FAILED, error_message=str(exc))
    finally:
        db.close()
        for p in [input_path if 'input_path' in dir() else None,
                  output_path if 'output_path' in dir() else None]:
            if p and os.path.exists(p):
                os.unlink(p)


@celery_app.task(bind=True, name="check_plagiarism")
def check_plagiarism_task(self, job_id: str):
    # Ensure sys.path is correct inside the worker subprocess
    _BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _BACKEND_ROOT not in sys.path:
        sys.path.insert(0, _BACKEND_ROOT)
        
    from commands.check import execute  # noqa
    import io
    from contextlib import redirect_stdout

    db = SessionLocal()
    input_path = None
    job = None
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        _mark(db, job, STATUS_PROCESSING)

        input_path = _download_input(job)
        args = SimpleNamespace(input=input_path)

        # Capture printed output for structured result and logs
        with JobLogger(db, job_id) as jl:
            execute(args)
            # Need to get the full output before flush clears it
            output = jl.io.getvalue()
        
        # Parse score/reason from printed output
        score, reason = None, output
        for line in output.splitlines():
            if line.startswith("Plagiarism Score:"):
                try:
                    score = int(line.split(":")[1].strip().rstrip("%"))
                except ValueError:
                    pass
            elif line.startswith("Reason:"):
                reason = line[len("Reason:"):].strip()

        _mark(db, job, STATUS_COMPLETED, result_json={"score": score, "reason": reason})
        logger.info("check_plagiarism job %s completed, score=%s", job_id, score)
    except Exception as exc:
        logger.exception("check_plagiarism job %s failed: %s", job_id, exc)
        if job:
            _mark(db, job, STATUS_FAILED, error_message=str(exc))
    finally:
        db.close()
        if input_path and os.path.exists(input_path):
            os.unlink(input_path)


@celery_app.task(bind=True, name="fix_plagiarism")
def fix_plagiarism_task(self, job_id: str):
    # Ensure sys.path is correct inside the worker subprocess
    _BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _BACKEND_ROOT not in sys.path:
        sys.path.insert(0, _BACKEND_ROOT)
        
    from commands.fix import execute  # noqa

    db = SessionLocal()
    input_path = output_path = None
    job = None
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        _mark(db, job, STATUS_PROCESSING)

        input_path = _download_input(job)
        context = _download_context(job)
        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        output_path = tmp.name
        tmp.close()

        args = SimpleNamespace(input=input_path, out=output_path, codebase="")

        import core.extractor as extractor  # noqa
        extractor.extract_codebase_context = lambda codebase_path: context
        # Ensure get_architectural_memory uses the mocked context
        orig_get_memory = extractor.get_architectural_memory
        extractor.get_architectural_memory = lambda codebase_path: orig_get_memory("")


        with JobLogger(db, job_id):
            execute(args)

        output_key = _upload_output(output_path, job_id, ".docx")
        _mark(db, job, STATUS_COMPLETED, output_s3_key=output_key)
        logger.info("fix_plagiarism job %s completed", job_id)
    except Exception as exc:
        logger.exception("fix_plagiarism job %s failed: %s", job_id, exc)
        if job:
            _mark(db, job, STATUS_FAILED, error_message=str(exc))
    finally:
        db.close()
        for p in [input_path, output_path]:
            if p and os.path.exists(p):
                os.unlink(p)


@celery_app.task(bind=True, name="check_ai_phrases")
def check_ai_phrases_task(self, job_id: str):
    # Ensure sys.path is correct inside the worker subprocess
    _BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _BACKEND_ROOT not in sys.path:
        sys.path.insert(0, _BACKEND_ROOT)
        
    from commands.detect_ai_phrases import execute  # noqa
    import io
    from contextlib import redirect_stdout

    db = SessionLocal()
    input_path = None
    job = None
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        _mark(db, job, STATUS_PROCESSING)

        input_path = _download_input(job)
        page_size = job.params.get("page_size", 300)
        args = SimpleNamespace(input=input_path, page_size=page_size)

        # detect_ai_phrases collects structured data internally; capture output for summary and logs
        with JobLogger(db, job_id) as jl:
            execute(args)
            output = jl.io.getvalue()

        _mark(db, job, STATUS_COMPLETED, result_json={"output": output})
        logger.info("check_ai_phrases job %s completed", job_id)
    except Exception as exc:
        logger.exception("check_ai_phrases job %s failed: %s", job_id, exc)
        if job:
            _mark(db, job, STATUS_FAILED, error_message=str(exc))
    finally:
        db.close()
        if input_path and os.path.exists(input_path):
            os.unlink(input_path)
