"""Main Streamlit application."""

import streamlit as st
from datetime import datetime

from app.auth import require_auth
from app.data_service import (
    load_files,
    load_decisions,
    save_decisions,
    get_processed_file_ids,
)
from app.git_service import save_and_commit
from app.ui.components import (
    render_file_card,
    render_sidebar,
    render_filters,
    render_progress,
    render_empty_state,
)
from app.config import FileInfo

# Page configuration
st.set_page_config(
    page_title="ScanSnap Organizer",
    layout="wide",
)


# Authentication
require_auth()


# Title
st.title("📄 ScanSnap Document Organizer")
st.markdown("Organisiere deine Dokumente - Thumbnails werden von Tim bereitgestellt")


# Load data
@st.cache_data
def get_cached_files():
    return load_files()


@st.cache_data
def get_cached_decisions():
    return load_decisions()


files = get_cached_files()
decisions = get_cached_decisions()


# Progress bar
render_progress(files, decisions)


# Filters
show_completed, batch_size = render_filters()


# Filter files to display
processed_ids = get_processed_file_ids(decisions)

if show_completed:
    display_files = files
else:
    display_files = [f for f in files if f["id"] not in processed_ids]


# Handle decision callback
def on_decision(file: FileInfo, action: str, data: dict | None) -> None:
    """Handle a decision (move or delete)."""
    timestamp = datetime.now().isoformat()
    
    if action == "delete":
        decisions["deletions"].append({
            "file_id": file["id"],
            "file_name": file["name"],
            "decided_at": timestamp,
        })
    elif action == "move" and data:
        decisions["moves"].append({
            "file_id": file["id"],
            "file_name": file["name"],
            "to_folder": data["to_folder"],
            "main_folder": data["main_folder"],
            "sub_folder": data["sub_folder"],
            "decided_at": timestamp,
        })
    
    # Save decisions
    save_decisions(decisions)
    
    # Try to commit
    success, message = save_and_commit(len(decisions["moves"]))
    if success:
        st.success(message)
    else:
        st.warning(message)
    
    st.rerun()


# Display files
st.markdown("---")

if not display_files:
    render_empty_state()
else:
    for file in display_files[:batch_size]:
        render_file_card(file, decisions, on_decision)


# Sidebar
if render_sidebar(files, decisions):
    st.rerun()
