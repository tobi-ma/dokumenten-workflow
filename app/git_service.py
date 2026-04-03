"""Git operations for auto-committing decisions from Streamlit Cloud.

This module uses the GitHub REST API to commit changes directly from Streamlit Cloud,
since local git commands don't work in the Streamlit environment.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# GitHub API Configuration
GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "tobi-ma"
REPO_NAME = "dokumenten-workflow"
BRANCH = "main"


def get_github_config() -> dict:
    """Get GitHub configuration from Streamlit secrets.
    
    Returns:
        Dictionary with 'token', 'email', 'name' or empty values if not configured.
    """
    try:
        github_secrets = st.secrets.get("github", {})
        return {
            "token": github_secrets.get("token", ""),
            "email": github_secrets.get("email", ""),
            "name": github_secrets.get("name", ""),
        }
    except Exception:
        # Fallback to environment variables
        return {
            "token": os.environ.get("GITHUB_TOKEN", ""),
            "email": os.environ.get("GITHUB_EMAIL", ""),
            "name": os.environ.get("GITHUB_NAME", ""),
        }


def get_file_sha(token: str, file_path: str) -> Optional[str]:
    """Get the SHA of a file in the repo (required for updates).
    
    Args:
        token: GitHub personal access token
        file_path: Path to file in repo (e.g., "data/decisions.json")
        
    Returns:
        SHA hash if file exists, None if file doesn't exist or error occurred.
    """
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            sha = response.json().get("sha")
            logger.debug(f"Got SHA for {file_path}: {sha[:7] if sha else 'N/A'}")
            return sha
        elif response.status_code == 404:
            logger.debug(f"File {file_path} not found (will create new)")
            return None
        else:
            logger.error(f"GitHub API error getting SHA: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Error getting file SHA: {e}")
        return None


def commit_to_github(
    token: str,
    file_path: str,
    content: str,
    commit_message: str,
    sha: Optional[str] = None
) -> bool:
    """Commit a file to GitHub via REST API.
    
    This creates or updates a file directly in the GitHub repository.
    
    Args:
        token: GitHub personal access token
        file_path: Path to file in repo (e.g., "data/decisions.json")
        content: File content (will be base64 encoded automatically)
        commit_message: Git commit message
        sha: SHA of existing file (for updates), None for new files
        
    Returns:
        True if commit succeeded, False otherwise
    """
    import base64
    
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Encode content to base64
    content_bytes = content.encode("utf-8")
    content_b64 = base64.b64encode(content_bytes).decode("ascii")
    
    data = {
        "message": commit_message,
        "content": content_b64,
        "branch": BRANCH
    }
    
    if sha:
        data["sha"] = sha
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=15)
        
        if response.status_code in [200, 201]:
            result = response.json()
            commit = result.get("commit", {})
            logger.info(f"Successfully committed {file_path}: {commit_message}")
            logger.debug(f"Commit SHA: {commit.get('sha', 'N/A')}")
            return True
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout committing {file_path}")
        return False
    except Exception as e:
        logger.error(f"Error committing file: {e}")
        return False


def save_and_commit(moves_count: int = 0, decisions_content: Optional[dict] = None) -> tuple[bool, str]:
    """Save decisions to GitHub via API.
    
    This is the main entry point called by the Streamlit app.
    
    Args:
        moves_count: Number of moves for the commit message (legacy, optional)
        decisions_content: Optional pre-loaded decisions content (if None, reads from file)
        
    Returns:
        Tuple of (success, message) where:
        - success: True if GitHub commit succeeded
        - message: User-friendly status message
    """
    config = get_github_config()
    token = config.get("token")
    
    if not token:
        logger.warning("GitHub token not configured - saving locally only")
        return False, "⚠️ GitHub nicht konfiguriert - lokal gespeichert"
    
    # Load decisions content if not provided
    if decisions_content is None:
        from app.data_service import load_decisions
        decisions_content = load_decisions()
    
    # Convert to JSON
    json_content = json.dumps(decisions_content, indent=2, ensure_ascii=False)
    
    # Get current file SHA for update
    file_path = "data/decisions.json"
    sha = get_file_sha(token, file_path)
    
    # Build commit message
    actual_moves = len(decisions_content.get("moves", []))
    actual_deletions = len(decisions_content.get("deletions", []))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"Update decisions: {actual_moves} moves, {actual_deletions} deletions - {timestamp}"
    
    # Commit via API
    success = commit_to_github(
        token=token,
        file_path=file_path,
        content=json_content,
        commit_message=commit_msg,
        sha=sha
    )
    
    if success:
        logger.info(f"GitHub commit successful: {commit_msg}")
        return True, "✅ Gespeichert & zu GitHub gepusht!"
    else:
        logger.error("GitHub commit failed")
        return False, "⚠️ Lokal gespeichert (GitHub API Fehler)"


# Legacy function for backward compatibility
def commit_decisions(moves_count: int) -> bool:
    """Legacy function - use save_and_commit instead.
    
    Maintains compatibility with old code that imports commit_decisions.
    """
    success, _ = save_and_commit(moves_count)
    return success


# Additional utility: commit any file
def commit_any_file(file_path: str, content: str, commit_message: str) -> tuple[bool, str]:
    """Commit any file to GitHub (for other modules like folder_structure updates).
    
    Args:
        file_path: Path in repo (e.g., "data/folder_structure.json")
        content: File content (string, will be encoded)
        commit_message: Commit message
        
    Returns:
        Tuple of (success, message)
    """
    config = get_github_config()
    token = config.get("token")
    
    if not token:
        return False, "GitHub token not configured"
    
    sha = get_file_sha(token, file_path)
    success = commit_to_github(token, file_path, content, commit_message, sha)
    
    if success:
        return True, f"✅ {file_path} zu GitHub gepusht!"
    else:
        return False, f"⚠️ GitHub API Fehler bei {file_path}"
