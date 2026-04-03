"""Utility functions."""

import os
import logging
from app.config import THUMBNAILS_DIR, MAIN_FOLDER_OPTION

logger = logging.getLogger(__name__)


def get_folder_path(main_folder: str, sub_folder: str | None = None) -> str:
    """Returns the full path for a folder selection.
    
    Args:
        main_folder: The main folder name
        sub_folder: Optional subfolder name
        
    Returns:
        Full path string like "main/sub" or just "main"
    """
    if sub_folder and sub_folder != MAIN_FOLDER_OPTION:
        return f"{main_folder}/{sub_folder}"
    return main_folder


def find_thumbnail(file_id: str) -> str | None:
    """Find thumbnail path for a file.
    
    Checks multiple naming conventions:
    - Cleaned ID (replacing ! with _)
    - Raw ID as-is
    - Different suffixes: _page1.jpg, _large.jpg, _medium.jpg
    
    Priority: _page1 > _large > _medium
    
    Args:
        file_id: The file ID to find thumbnail for
        
    Returns:
        Path to thumbnail if found, None otherwise
    """
    file_id_clean = file_id.replace("!", "_")
    file_id_raw = file_id
    
    # Priority order for suffixes
    suffixes = ["_page1.jpg", "_large.jpg", "_medium.jpg"]
    
    for suffix in suffixes:
        # Check cleaned ID first
        path = f"{THUMBNAILS_DIR}/{file_id_clean}{suffix}"
        if os.path.exists(path):
            logger.debug(f"Found thumbnail: {path}")
            return path
        
        # Then raw ID
        path = f"{THUMBNAILS_DIR}/{file_id_raw}{suffix}"
        if os.path.exists(path):
            logger.debug(f"Found thumbnail: {path}")
            return path
    
    logger.debug(f"No thumbnail found for {file_id}")
    return None


def calculate_progress(completed: int, total: int) -> float:
    """Calculate progress percentage.
    
    Returns 0 if total is 0 to avoid division by zero.
    """
    return completed / total if total > 0 else 0.0
