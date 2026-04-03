"""Git operations for auto-committing decisions."""

import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def commit_decisions(moves_count: int) -> bool:
    """Auto-commit decisions to Git.
    
    Args:
        moves_count: Number of move decisions for the commit message
        
    Returns:
        True if commit succeeded, False otherwise
        
    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    try:
        # Stage decisions file
        result = subprocess.run(
            ["git", "add", "data/decisions.json"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug(f"Git add output: {result.stdout}")
        
        # Commit
        commit_msg = f"Update decisions: {moves_count} moves"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Git commit successful: {commit_msg}")
        logger.debug(f"Git commit output: {result.stdout}")
        
        # Push
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Git push successful")
        logger.debug(f"Git push output: {result.stdout}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.cmd}")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error("Git executable not found")
        raise


def save_and_commit(moves_count: int) -> tuple[bool, str]:
    """Save and commit with proper error handling.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        if commit_decisions(moves_count):
            return True, "✅ Gespeichert & gepusht!"
    except subprocess.CalledProcessError:
        return False, "⚠️ Lokal gespeichert"
    except Exception as e:
        logger.exception("Unexpected error during git commit")
        return False, f"⚠️ Lokal gespeichert"
