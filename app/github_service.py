"""GitHub REST API integration for committing files.

Single module for all GitHub operations. Token is always passed explicitly
(decrypted from the encrypted constant via the user's password).
"""

import base64
import json
import logging
from datetime import datetime

import requests

from app.config import GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_BRANCH

logger = logging.getLogger(__name__)

_API = "https://api.github.com"
_TIMEOUT = 15


def _headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _get_file_sha(token: str, path: str) -> str | None:
    """Get the current SHA of a file on GitHub (needed to update it)."""
    url = f"{_API}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{path}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=_headers(token), timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json().get("sha")
        if r.status_code == 404:
            return None
        logger.error("SHA lookup failed: %s %s", r.status_code, r.text[:200])
        return None
    except Exception as e:
        logger.error("SHA lookup error: %s", e)
        return None


def _put_file(token: str, path: str, content: str, message: str, sha: str | None) -> bool:
    """Create or update a file via the GitHub Contents API."""
    url = f"{_API}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{path}"
    body: dict = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha

    try:
        r = requests.put(url, headers=_headers(token), json=body, timeout=_TIMEOUT)
        if r.status_code in (200, 201):
            logger.info("Committed %s: %s", path, message)
            return True
        logger.error("Commit failed: %s %s", r.status_code, r.text[:300])
        return False
    except requests.exceptions.Timeout:
        logger.error("Timeout committing %s", path)
        return False
    except Exception as e:
        logger.error("Commit error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def commit_decisions(token: str, decisions: dict) -> tuple[bool, str]:
    """Commit decisions.json to GitHub.

    Args:
        token: Decrypted GitHub PAT.
        decisions: The full decisions dictionary.

    Returns:
        (success, user-facing message)
    """
    path = "data/decisions.json"
    content = json.dumps(decisions, indent=2, ensure_ascii=False)

    sha = _get_file_sha(token, path)

    moves = len(decisions.get("moves", []))
    deletions = len(decisions.get("deletions", []))
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"Update decisions: {moves} moves, {deletions} deletions - {ts}"

    if _put_file(token, path, content, message, sha):
        return True, "Gespeichert & zu GitHub gepusht!"
    return False, "GitHub API Fehler — lokal gespeichert"


def commit_file(token: str, path: str, content: str, message: str) -> tuple[bool, str]:
    """Commit any file to GitHub (e.g. folder_structure.json).

    Args:
        token: Decrypted GitHub PAT.
        path: Repo-relative path (e.g. "data/folder_structure.json").
        content: File content as string.
        message: Commit message.

    Returns:
        (success, user-facing message)
    """
    sha = _get_file_sha(token, path)
    if _put_file(token, path, content, message, sha):
        return True, f"{path} zu GitHub gepusht!"
    return False, f"GitHub API Fehler bei {path}"
