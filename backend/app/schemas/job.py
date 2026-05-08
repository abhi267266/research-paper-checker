from typing import Any
from pydantic import BaseModel


class JobEnqueuedResponse(BaseModel):
    job_id: str
    status: str = "pending"


class JobStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    download_url: str | None = None
    result: Any | None = None
    error: str | None = None
    logs: str | None = ""


class JobListItem(BaseModel):
    id: str
    job_type: str
    status: str
    created_at: Any  # datetime
    error_message: str | None = None
    result_json: Any | None = None
    logs: str | None = ""

    class Config:
        from_attributes = True

