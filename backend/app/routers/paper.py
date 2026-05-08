import logging
import tempfile
import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.job import Job, STATUS_PENDING
from app.models.user import User
from app.schemas.job import JobEnqueuedResponse
from app.services import s3_service, github_service
from app.worker.tasks import (
    humanize_task,
    check_plagiarism_task,
    fix_plagiarism_task,
    check_ai_phrases_task,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/paper", tags=["paper"])

ALLOWED_EXTENSIONS = {".docx", ".txt"}


def _validate_and_upload(file: UploadFile, user_id: str) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported file type. Use .docx or .txt")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=422, detail="Uploaded file is empty")
        tmp.write(content)
        tmp_path = tmp.name
        print(f"DEBUG: Received file {file.filename}, size: {len(content)} bytes")

    key = f"{user_id}/{uuid.uuid4()}{ext}"
    try:
        s3_service.upload_file(tmp_path, s3_service.BUCKET_UPLOADS, key)
        print(f"DEBUG: Uploaded to S3: {key}")
    finally:
        os.unlink(tmp_path)
    return key


def _create_job(db: Session, user_id: str, job_type: str, input_key: str, params: dict, context_key: str | None = None) -> Job:
    job = Job(
        user_id=user_id,
        job_type=job_type,
        status=STATUS_PENDING,
        input_s3_key=input_key,
        context_s3_key=context_key,
        params=params,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _resolve_context(github_url: str | None) -> str | None:
    if not github_url:
        return None
    if not github_service.validate_github_url(github_url):
        raise HTTPException(status_code=422, detail="Invalid GitHub URL. Must be https://github.com/...")
    try:
        return github_service.get_or_create_context(github_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/humanize", status_code=202, response_model=JobEnqueuedResponse)
def humanize(
    file: UploadFile = File(...),
    threshold: int = Form(5),
    github_url: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    input_key = _validate_and_upload(file, current_user.id)
    context_key = _resolve_context(github_url)
    job = _create_job(db, current_user.id, "humanize", input_key, {"threshold": threshold}, context_key)
    humanize_task.delay(job.id)
    logger.info("Enqueued humanize job %s for user %s", job.id, current_user.id)
    return JobEnqueuedResponse(job_id=job.id)


@router.post("/check-plagiarism", status_code=202, response_model=JobEnqueuedResponse)
def check_plagiarism(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    input_key = _validate_and_upload(file, current_user.id)
    job = _create_job(db, current_user.id, "check-plagiarism", input_key, {})
    check_plagiarism_task.delay(job.id)
    return JobEnqueuedResponse(job_id=job.id)


@router.post("/fix-plagiarism", status_code=202, response_model=JobEnqueuedResponse)
def fix_plagiarism(
    file: UploadFile = File(...),
    github_url: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    input_key = _validate_and_upload(file, current_user.id)
    context_key = _resolve_context(github_url)
    job = _create_job(db, current_user.id, "fix-plagiarism", input_key, {}, context_key)
    fix_plagiarism_task.delay(job.id)
    return JobEnqueuedResponse(job_id=job.id)


@router.post("/check-ai-phrases", status_code=202, response_model=JobEnqueuedResponse)
def check_ai_phrases(
    file: UploadFile = File(...),
    page_size: int = Form(300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    input_key = _validate_and_upload(file, current_user.id)
    job = _create_job(db, current_user.id, "check-ai-phrases", input_key, {"page_size": page_size})
    check_ai_phrases_task.delay(job.id)
    return JobEnqueuedResponse(job_id=job.id)
