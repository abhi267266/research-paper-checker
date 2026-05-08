"""TDD: Job polling endpoint tests."""
import uuid
from app.models.job import Job


def _create_job(db, user_id, status="pending", result_json=None, output_s3_key=None):
    job = Job(
        user_id=str(user_id),
        job_type="humanize",
        status=status,
        input_s3_key="uploads/test.txt",
        result_json=result_json,
        output_s3_key=output_s3_key,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _get_user_id(client, registered_user):
    from app.services.auth_service import decode_token
    resp = client.post("/auth/login", json=registered_user)
    token = resp.cookies["humanizer_access_token"]
    return decode_token(token)["sub"]


def test_poll_pending_job(auth_cookies, registered_user):
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    user_id = _get_user_id(auth_cookies, registered_user)
    job = _create_job(db, user_id, status="pending")

    resp = auth_cookies.get(f"/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    db.close()


def test_poll_completed_job(auth_cookies, registered_user, mocker):
    from tests.conftest import TestingSessionLocal
    mocker.patch("app.routers.jobs.s3_service.presigned_url", return_value="http://minio/output.docx")
    db = TestingSessionLocal()
    user_id = _get_user_id(auth_cookies, registered_user)
    job = _create_job(db, user_id, status="completed", output_s3_key="outputs/out.docx")

    resp = auth_cookies.get(f"/jobs/{job.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "download_url" in data
    db.close()


def test_poll_other_users_job(client, registered_user):
    """User B cannot see User A's job."""
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    other_id = uuid.uuid4()
    job = _create_job(db, other_id, status="pending")

    client.post("/auth/login", json=registered_user)
    resp = client.get(f"/jobs/{job.id}")
    assert resp.status_code == 403
    db.close()


def test_poll_nonexistent_job(auth_cookies):
    resp = auth_cookies.get(f"/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404
