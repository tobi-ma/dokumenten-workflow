"""Main Streamlit application."""

import streamlit as st
from datetime import datetime

# from app.auth import require_auth
from app.data_service import (
    load_files,
    load_decisions,
    save_decisions,
    get_processed_file_ids,
)
from app.ui.components import (
    render_file_card,
    render_sidebar,
    render_filters,
    render_progress,
    render_empty_state,
    render_pending_changes,
)
from app.config import FileInfo

# Page configuration
st.set_page_config(
    page_title="ScanSnap Organizer",
    layout="wide",
)


# Authentication disabled for development
# require_auth()


# Title
st.title("📄 ScanSnap Document Organizer")
st.markdown("Organisiere deine Dokumente - Thumbnails werden von Tim bereitgestellt")


# Initialize session state for pending decisions
if "pending_moves" not in st.session_state:
    st.session_state.pending_moves = []
if "pending_deletions" not in st.session_state:
    st.session_state.pending_deletions = []


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
pending_ids = {m["file_id"] for m in st.session_state.pending_moves} | {d["file_id"] for d in st.session_state.pending_deletions}
all_processed = processed_ids | pending_ids

if show_completed:
    display_files = files
else:
    display_files = [f for f in files if f["id"] not in all_processed]


# Handle decision callback - only adds to session state, no commit
def on_decision(file: FileInfo, action: str, data: dict | None) -> None:
    """Handle a decision (move or delete) - stores in session state only."""
    timestamp = datetime.now().isoformat()
    
    if action == "delete":
        st.session_state.pending_deletions.append({
            "file_id": file["id"],
            "file_name": file["name"],
            "decided_at": timestamp,
        })
        st.info(f"🗑️ **{file['name'][:30]}** zum Löschen vorgemerkt")
    elif action == "move" and data:
        # Build display name (with new filename if changed)
        display_name = data.get("new_file_name") or file["name"]
        st.session_state.pending_moves.append({
            "file_id": file["id"],
            "file_name": file["name"],
            "to_folder": data["to_folder"],
            "main_folder": data["main_folder"],
            "sub_folder": data["sub_folder"],
            "decided_at": timestamp,
            "new_file_name": data.get("new_file_name"),  # None if not changed
        })
        st.info(f"📁 **{display_name[:30]}** → {data['to_folder']} vorgemerkt")
    
    st.rerun()


# Display files
st.markdown("---")

# Filter files to display
processed_ids = get_processed_file_ids(decisions)
pending_ids = {m["file_id"] for m in st.session_state.pending_moves} | {d["file_id"] for d in st.session_state.pending_deletions}
all_processed = processed_ids | pending_ids

if show_completed:
    display_files = files
else:
    display_files = [f for f in files if f["id"] not in all_processed]


if not display_files:
    render_empty_state()
else:
    for file in display_files[:batch_size]:
        render_file_card(file, decisions, on_decision)


# Sidebar with pending changes and send button
pending_count = len(st.session_state.pending_moves) + len(st.session_state.pending_deletions)
send_triggered = render_sidebar(
    files,
    decisions,
    pending_count,
    st.session_state.pending_moves,
    st.session_state.pending_deletions
)

if send_triggered:
    # Clear pending after successful send
    st.session_state.pending_moves = []
    st.session_state.pending_deletions = []
    st.cache_data.clear()
    st.rerun()
