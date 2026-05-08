"""
GitHub codebase context service.
Clones a public GitHub repo (depth=1), extracts context via the existing
extractor module, serialises to JSON, and caches in S3.
"""
import sys
import os
import json
import hashlib
import tempfile
import shutil
import logging

import git

from app.services import s3_service

logger = logging.getLogger(__name__)

# Add parent repo root to path so we can import the existing extractor
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.extractor import extract_codebase_context  # noqa: E402


def _cache_key(github_url: str) -> str:
    return hashlib.sha256(github_url.strip().lower().encode()).hexdigest() + ".json"


def validate_github_url(url: str) -> bool:
    return url.startswith("https://github.com/") and len(url) > 25


def get_or_create_context(github_url: str) -> str:
    """
    Returns the S3 key of the context JSON in the codebase bucket.
    Uses cache if the key already exists.
    """
    key = _cache_key(github_url)

    if s3_service.object_exists(s3_service.BUCKET_CODEBASE, key):
        logger.info("Codebase context cache hit: %s", key)
        return key

    logger.info("Cloning repo %s for context extraction", github_url)
    tmpdir = tempfile.mkdtemp()
    try:
        git.Repo.clone_from(github_url, tmpdir, depth=1)
        context_text = extract_codebase_context(tmpdir)
        payload = json.dumps({"context": context_text}).encode()
        s3_service.upload_bytes(payload, s3_service.BUCKET_CODEBASE, key)
        logger.info("Codebase context cached at %s", key)
        return key
    except git.exc.GitCommandError as exc:
        raise ValueError(f"Failed to clone repository: {exc}") from exc
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
