"""Data persistence layer for files and decisions."""

import json
import os
import logging
from datetime import datetime

from app.config import FILES_JSON, DECISIONS_JSON, DATA_DIR, Decisions, FileInfo

logger = logging.getLogger(__name__)


def load_files() -> list[FileInfo]:
    """Load file list from JSON.
    
    Returns empty list if file doesn't exist or is invalid.
    """
    if not os.path.exists(FILES_JSON):
        logger.warning(f"Files JSON not found: {FILES_JSON}")
        return []
    
    try:
        with open(FILES_JSON, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.error(f"Invalid files data format: expected list, got {type(data)}")
                return []
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse files JSON: {e}")
        return []
    except OSError as e:
        logger.error(f"Failed to read files JSON: {e}")
        return []


def load_decisions() -> Decisions:
    """Load existing decisions from JSON.
    
    Returns default empty decisions if file doesn't exist or is invalid.
    """
    if not os.path.exists(DECISIONS_JSON):
        logger.info(f"Decisions file not found, starting fresh: {DECISIONS_JSON}")
        return {
            "moves": [],
            "deletions": [],
            "last_updated": None,
        }
    
    try:
        with open(DECISIONS_JSON, encoding="utf-8") as f:
            data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict):
                logger.error(f"Invalid decisions format: expected dict, got {type(data)}")
                return {"moves": [], "deletions": [], "last_updated": None}
            
            return {
                "moves": data.get("moves", []),
                "deletions": data.get("deletions", []),
                "last_updated": data.get("last_updated"),
            }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse decisions JSON: {e}")
        return {"moves": [], "deletions": [], "last_updated": None}
    except OSError as e:
        logger.error(f"Failed to read decisions JSON: {e}")
        return {"moves": [], "deletions": [], "last_updated": None}


def save_decisions(decisions: Decisions) -> None:
    """Save decisions with timestamp.
    
    Creates data directory if it doesn't exist.
    Raises OSError if write fails.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    decisions["last_updated"] = datetime.now().isoformat()
    
    try:
        with open(DECISIONS_JSON, "w", encoding="utf-8") as f:
            json.dump(decisions, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved decisions: {len(decisions['moves'])} moves, {len(decisions['deletions'])} deletions")
    except OSError as e:
        logger.error(f"Failed to write decisions JSON: {e}")
        raise


def get_decision_stats(decisions: Decisions) -> tuple[int, int, int]:
    """Get statistics about decisions.
    
    Returns (completed_count, moves_count, deletions_count)
    """
    moves_count = len(decisions.get("moves", []))
    deletions_count = len(decisions.get("deletions", []))
    completed = moves_count + deletions_count
    return completed, moves_count, deletions_count


def get_processed_file_ids(decisions: Decisions) -> set[str]:
    """Get set of all processed file IDs (moved or deleted)."""
    moved_ids = {m["file_id"] for m in decisions.get("moves", [])}
    deleted_ids = {d["file_id"] for d in decisions.get("deletions", [])}
    return moved_ids | deleted_ids
