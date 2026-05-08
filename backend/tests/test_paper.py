"""TDD: Paper endpoint tests — all Claude calls are mocked."""
import io
import pytest


TXT_CONTENT = b"This is a test research paper. It contains several sentences for analysis."


def _upload_file(client, endpoint, extra_data=None):
    files = {"file": ("test.txt", io.BytesIO(TXT_CONTENT), "text/plain")}
    data = extra_data or {}
    return client.post(endpoint, files=files, data=data)


def test_humanize_requires_auth(client):
    resp = _upload_file(client, "/paper/humanize", {"threshold": "4"})
    assert resp.status_code == 401


def test_humanize_enqueues_job(auth_cookies, mocker):
    mocker.patch("app.routers.paper.s3_service.upload_file", return_value="uploads/test.txt")
    mocker.patch("app.routers.paper.humanize_task.delay", return_value=mocker.Mock(id="task-1"))

    resp = _upload_file(auth_cookies, "/paper/humanize", {"threshold": "4"})
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_check_plagiarism_enqueues_job(auth_cookies, mocker):
    mocker.patch("app.routers.paper.s3_service.upload_file", return_value="uploads/test.txt")
    mocker.patch("app.routers.paper.check_plagiarism_task.delay", return_value=mocker.Mock(id="task-2"))

    resp = _upload_file(auth_cookies, "/paper/check-plagiarism")
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_fix_plagiarism_enqueues_job(auth_cookies, mocker):
    mocker.patch("app.routers.paper.s3_service.upload_file", return_value="uploads/test.txt")
    mocker.patch("app.routers.paper.fix_plagiarism_task.delay", return_value=mocker.Mock(id="task-3"))

    resp = _upload_file(auth_cookies, "/paper/fix-plagiarism")
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_check_ai_phrases_enqueues_job(auth_cookies, mocker):
    mocker.patch("app.routers.paper.s3_service.upload_file", return_value="uploads/test.txt")
    mocker.patch("app.routers.paper.check_ai_phrases_task.delay", return_value=mocker.Mock(id="task-4"))

    resp = _upload_file(auth_cookies, "/paper/check-ai-phrases", {"page_size": "300"})
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_unsupported_file_type_rejected(auth_cookies, mocker):
    mocker.patch("app.routers.paper.s3_service.upload_file", return_value="uploads/test.pdf")
    files = {"file": ("test.pdf", io.BytesIO(b"PDF content"), "application/pdf")}
    resp = auth_cookies.post("/paper/humanize", files=files, data={"threshold": "4"})
    assert resp.status_code == 422
