import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.job import Job, STATUS_COMPLETED, STATUS_FAILED, STATUS_PENDING, STATUS_PROCESSING
from app.models.user import User
from app.schemas.job import JobStatusResponse, JobListItem
from app.services import s3_service
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListItem])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    download_url = None
    if job.status == STATUS_COMPLETED and job.output_s3_key:
        download_url = s3_service.presigned_url(s3_service.BUCKET_OUTPUTS, job.output_s3_key)

    return JobStatusResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        download_url=download_url,
        result=job.result_json,
        error=job.error_message,
        logs=job.logs,
    )


@router.get("/{job_id}/download")
def download_job_result(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if job.status != STATUS_COMPLETED or not job.output_s3_key:
        raise HTTPException(status_code=400, detail="Result not ready for download")

    from fastapi.responses import StreamingResponse
    obj = s3_service.get_object(s3_service.BUCKET_OUTPUTS, job.output_s3_key)
    
    return StreamingResponse(
        obj["Body"],
        media_type=obj.get("ContentType", "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename={job.output_s3_key}"
        }
    )


@router.post("/{job_id}/terminate")
def terminate_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if job.status in (STATUS_PENDING, STATUS_PROCESSING):
        celery_app.control.revoke(job.id, terminate=True)
        job.status = STATUS_FAILED
        job.error_message = "Terminated by user."
        db.commit()

    return {"message": "Job terminated"}


@router.delete("/{job_id}")
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if job.status in (STATUS_PENDING, STATUS_PROCESSING):
        raise HTTPException(status_code=400, detail="Job is currently running. Please terminate it first.")

    # Delete associated files from MinIO
    if job.input_s3_key:
        s3_service.delete_object(s3_service.BUCKET_UPLOADS, job.input_s3_key)
    if job.output_s3_key:
        s3_service.delete_object(s3_service.BUCKET_OUTPUTS, job.output_s3_key)
    if job.context_s3_key:
        s3_service.delete_object(s3_service.BUCKET_CODEBASE, job.context_s3_key)

    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}
