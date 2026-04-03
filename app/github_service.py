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
    moves_count: int,
    max_retries: int = 3
) -> tuple[bool, str]:
    """Commit decisions.json to GitHub via API with retry on SHA conflict.
    
    This is the main entry point for Streamlit Cloud to save decisions.
    Handles race conditions by retrying with fresh SHA if conflict occurs.
    
    Args:
        decisions_content: The decisions dictionary to save
        moves_count: Number of moves for the commit message
        max_retries: Maximum retry attempts on SHA conflict (default: 3)
        
    Returns:
        Tuple of (success, message)
    """
    token = get_github_token()
    
    if not token:
        logger.warning("GitHub token not configured - falling back to local save")
        return False, "⚠️ GitHub nicht konfiguriert - lokal gespeichert"
    
    file_path = "data/decisions.json"
    
    for attempt in range(max_retries):
        try:
            # Get current file SHA (fresh for each retry)
            file_sha = get_file_sha(token, file_path)
            
            # If file exists on GitHub, we need to merge with remote changes
            if file_sha and attempt > 0:
                logger.info(f"Retry {attempt}: Fetching remote decisions to merge...")
                remote_decisions = _fetch_remote_decisions(token, file_path)
                if remote_decisions:
                    decisions_content = _merge_decisions(remote_decisions, decisions_content)
            
            # Convert decisions to JSON string
            json_content = json.dumps(decisions_content, indent=2, ensure_ascii=False)
            
            # Commit via API
            commit_msg = f"Update decisions: {moves_count} moves - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            success = commit_file_via_api(
                token=token,
                file_path=file_path,
                content=json_content,
                commit_message=commit_msg,
                sha=file_sha
            )
            
            if success:
                return True, "✅ Gespeichert & zu GitHub gepusht!"
            else:
                # Check if it's a SHA conflict (422)
                # GitHub returns 422 when SHA doesn't match
                logger.warning(f"Commit failed on attempt {attempt + 1}, retrying...")
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return False, "⚠️ Lokal gespeichert (GitHub Konflikt nach mehreren Versuchen)"
                    
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                continue
            else:
                return False, f"⚠️ Lokal gespeichert (Fehler: {str(e)[:50]})"
    
    return False, "⚠️ Lokal gespeichert (Maximale Versuche erreicht)"


def _fetch_remote_decisions(token: str, file_path: str) -> Optional[dict]:
    """Fetch current decisions.json from GitHub API.
    
    Args:
        token: GitHub token
        file_path: Path to decisions.json
        
    Returns:
        Decisions dict if successful, None otherwise
    """
    import base64
    
    url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            content_b64 = data.get("content", "")
            content = base64.b64decode(content_b64).decode("utf-8")
            return json.loads(content)
        else:
            logger.warning(f"Could not fetch remote decisions: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching remote decisions: {e}")
        return None


def _merge_decisions(remote: dict, local: dict) -> dict:
    """Merge remote and local decisions (union of both).
    
    Args:
        remote: Decisions from GitHub
        local: Local decisions to save
        
    Returns:
        Merged decisions dict
    """
    merged = {
        "moves": [],
        "deletions": [],
        "last_updated": datetime.now().isoformat()
    }
    
    # Create sets of file IDs for deduplication
    move_ids = set()
    delete_ids = set()
    
    # Add all remote moves
    for move in remote.get("moves", []):
        file_id = move.get("file_id")
        if file_id and file_id not in move_ids:
            merged["moves"].append(move)
            move_ids.add(file_id)
    
    # Add all remote deletions
    for deletion in remote.get("deletions", []):
        file_id = deletion.get("file_id")
        if file_id and file_id not in delete_ids:
            merged["deletions"].append(deletion)
            delete_ids.add(file_id)
    
    # Add local moves (overwrite remote if same file_id)
    for move in local.get("moves", []):
        file_id = move.get("file_id")
        if file_id:
            # Remove existing entry for this file
            merged["moves"] = [m for m in merged["moves"] if m.get("file_id") != file_id]
            merged["moves"].append(move)
    
    # Add local deletions (overwrite remote if same file_id)
    for deletion in local.get("deletions", []):
        file_id = deletion.get("file_id")
        if file_id:
            merged["deletions"] = [d for d in merged["deletions"] if d.get("file_id") != file_id]
            merged["deletions"].append(deletion)
    
    logger.info(f"Merged decisions: {len(merged['moves'])} moves, {len(merged['deletions'])} deletions")
    return merged


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
