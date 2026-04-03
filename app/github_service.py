"""GitHub API integration for committing decisions from Streamlit Cloud."""

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


def get_github_token() -> Optional[str]:
    """Get GitHub token from Streamlit secrets.
    
    Returns None if not configured.
    """
    try:
        token = st.secrets.get("github", {}).get("token")
        if token:
            return token
    except Exception:
        pass
    
    # Fallback: check environment variable
    token = os.environ.get("GITHUB_TOKEN")
    return token


def get_file_sha(token: str, file_path: str) -> Optional[str]:
    """Get the SHA of a file in the repo.
    
    Args:
        token: GitHub personal access token
        file_path: Path to file in repo (e.g., "data/decisions.json")
        
    Returns:
        SHA hash if file exists, None if file doesn't exist
    """
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("sha")
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"GitHub API error getting file SHA: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting file SHA: {e}")
        return None


def commit_file_via_api(
    token: str,
    file_path: str,
    content: str,
    commit_message: str,
    sha: Optional[str] = None
) -> bool:
    """Commit a file to GitHub via API.
    
    Args:
        token: GitHub personal access token
        file_path: Path to file in repo (e.g., "data/decisions.json")
        content: File content (will be base64 encoded)
        commit_message: Git commit message
        sha: SHA of existing file (for updates), None for new files
        
    Returns:
        True if successful, False otherwise
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
            logger.info(f"Successfully committed {file_path}: {commit_message}")
            return True
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error committing file: {e}")
        return False


def commit_decisions_to_github(
    decisions_content: dict,
    moves_count: int
) -> tuple[bool, str]:
    """Commit decisions.json to GitHub via API.
    
    This is the main entry point for Streamlit Cloud to save decisions.
    
    Args:
        decisions_content: The decisions dictionary to save
        moves_count: Number of moves for the commit message
        
    Returns:
        Tuple of (success, message)
    """
    token = get_github_token()
    
    if not token:
        logger.warning("GitHub token not configured - falling back to local save")
        return False, "⚠️ GitHub nicht konfiguriert - lokal gespeichert"
    
    # Convert decisions to JSON string
    json_content = json.dumps(decisions_content, indent=2, ensure_ascii=False)
    
    # Get current file SHA (for updates)
    file_sha = get_file_sha(token, "data/decisions.json")
    
    # Commit via API
    commit_msg = f"Update decisions: {moves_count} moves - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    success = commit_file_via_api(
        token=token,
        file_path="data/decisions.json",
        content=json_content,
        commit_message=commit_msg,
        sha=file_sha
    )
    
    if success:
        return True, "✅ Gespeichert & zu GitHub gepusht!"
    else:
        return False, "⚠️ Lokal gespeichert (GitHub API Fehler)"


def commit_folder_structure_to_github(folder_structure: dict) -> tuple[bool, str]:
    """Commit folder_structure.json to GitHub via API.
    
    Called by the update_folder_structure script.
    
    Args:
        folder_structure: The folder structure dictionary to save
        
    Returns:
        Tuple of (success, message)
    """
    token = get_github_token()
    
    if not token:
        return False, "GitHub token not configured"
    
    # Add metadata
    output = {
        "_comment": "Auto-generated by Tim",
        "last_updated": datetime.now().isoformat(),
        "root_path": "Dokumente/ScanSnap",
        "folders": folder_structure
    }
    
    json_content = json.dumps(output, indent=2, ensure_ascii=False)
    file_sha = get_file_sha(token, "data/folder_structure.json")
    
    commit_msg = f"Update folder structure - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    success = commit_file_via_api(
        token=token,
        file_path="data/folder_structure.json",
        content=json_content,
        commit_message=commit_msg,
        sha=file_sha
    )
    
    if success:
        return True, "✅ Ordnerstruktur zu GitHub gepusht!"
    else:
        return False, "⚠️ GitHub API Fehler"


# Legacy wrapper for backward compatibility
def commit_decisions(moves_count: int) -> bool:
    """Legacy function - imports from data_service and commits.
    
    This maintains compatibility with existing code that imports git_service.
    In new code, use commit_decisions_to_github directly.
    """
    # Import here to avoid circular imports
    from app.data_service import load_decisions
    
    decisions = load_decisions()
    success, _ = commit_decisions_to_github(decisions, moves_count)
    return success


def save_and_commit(moves_count: int) -> tuple[bool, str]:
    """Legacy wrapper for backward compatibility.
    
    New code should:
    1. Call data_service.save_decisions(decisions) to save locally
    2. Call github_service.commit_decisions_to_github(decisions, moves_count)
    """
    from app.data_service import load_decisions
    
    decisions = load_decisions()
    return commit_decisions_to_github(decisions, moves_count)
