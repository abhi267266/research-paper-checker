from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.db import Base

# Valid statuses
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False)  # humanize | check-plagiarism | fix-plagiarism | check-ai-phrases
    status: Mapped[str] = mapped_column(String, default=STATUS_PENDING)
    input_s3_key: Mapped[str] = mapped_column(String, nullable=False)
    output_s3_key: Mapped[str] = mapped_column(String, nullable=True)
    context_s3_key: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    logs: Mapped[str] = mapped_column(Text, nullable=True, default="")
    result_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
