"""UI components for the document organizer."""

import logging
from datetime import datetime

import streamlit as st

from app.config import (
    ALL_FOLDERS,
    DELETE_OPTION,
    MAIN_FOLDER_OPTION,
    NEW_FOLDER_OPTION,
    FOLDER_STRUCTURE,
    FileInfo,
    Decisions,
    MoveDecision,
    DeleteDecision,
)
from app.utils import get_folder_path, find_thumbnail
from app.data_service import get_decision_stats, get_processed_file_ids

logger = logging.getLogger(__name__)


def render_file_card(
    file: FileInfo,
    decisions: Decisions,
    on_decision: callable,
) -> None:
    """Render a single file card with thumbnail and folder selector.
    
    Args:
        file: File information
        decisions: Current decisions state
        on_decision: Callback when a decision is made (file_id, action, data)
    """
    processed_ids = get_processed_file_ids(decisions)
    
    with st.container():
        cols = st.columns([1, 4, 2, 2])
        
        with cols[0]:
            st.markdown(f"**#{file.get('index', '?')}**")
        
        with cols[1]:
            st.markdown(f"**{file['name'][:50]}**")
            st.caption(f"📅 {file.get('date', 'unbekannt')}")
            
            # Thumbnail
            thumb_path = find_thumbnail(file["id"])
            if thumb_path:
                st.image(thumb_path, width=400)
            else:
                st.info("🖼️ Kein Thumbnail vorhanden")
        
        with cols[2]:
            st.markdown(f"📁 **{file.get('suggested', 'Dokumente')}**")
        
        with cols[3]:
            if file["id"] not in processed_ids:
                _render_folder_selector(file, on_decision)
            else:
                _render_completed_status(file, decisions)
        
        st.markdown("---")


def _render_folder_selector(file: FileInfo, on_decision: callable) -> None:
    """Render folder selection dropdowns for a file."""
    # Main folder dropdown
    main_folder = st.selectbox(
        "Hauptordner...",
        [""] + ALL_FOLDERS + [DELETE_OPTION],
        key=f"main_{file['id']}",
    )
    
    # Subfolder dropdown (if main selected and has subfolders)
    sub_folder = None
    if main_folder and main_folder in FOLDER_STRUCTURE and main_folder != DELETE_OPTION:
        subfolders = FOLDER_STRUCTURE[main_folder]
        if subfolders:
            sub_options = [MAIN_FOLDER_OPTION] + subfolders + [NEW_FOLDER_OPTION]
            sub_folder = st.selectbox(
                "Unterordner...",
                sub_options,
                key=f"sub_{file['id']}",
            )
            
            # Handle new subfolder creation
            if sub_folder == NEW_FOLDER_OPTION:
                new_folder = st.text_input(
                    "Name des neuen Unterordners:",
                    key=f"new_{file['id']}",
                )
                if new_folder:
                    sub_folder = new_folder
    
    # Confirm button
    if main_folder and st.button("✅ Verschieben", key=f"btn_{file['id']}"):
        if main_folder == DELETE_OPTION:
            on_decision(file, "delete", None)
        else:
            target_path = get_folder_path(main_folder, sub_folder)
            on_decision(file, "move", {
                "to_folder": target_path,
                "main_folder": main_folder,
                "sub_folder": sub_folder,
            })


def _render_completed_status(file: FileInfo, decisions: Decisions) -> None:
    """Render status for already processed files."""
    for move in decisions.get("moves", []):
        if move["file_id"] == file["id"]:
            st.success(f"→ {move['to_folder']}")
            return
    for deletion in decisions.get("deletions", []):
        if deletion["file_id"] == file["id"]:
            st.error("🗑️ Zum Löschen markiert")
            return


def render_sidebar(files: list[FileInfo], decisions: Decisions) -> bool:
    """Render sidebar with status and controls.
    
    Returns:
        True if refresh was requested
    """
    with st.sidebar:
        st.header("📊 Status")
        
        completed, moves_count, deletions_count = get_decision_stats(decisions)
        
        st.metric("Erledigt", f"{completed}/{len(files)}")
        st.metric("Verschieben", moves_count)
        st.metric("Löschen", deletions_count)
        
        if st.button("🔄 Status aktualisieren"):
            st.cache_data.clear()
            return True
        
        st.markdown("---")
        st.info("💡 Thumbnails werden von Tim bereitgestellt und automatisch aktualisiert.")
        
        return False


def render_filters() -> tuple[bool, int]:
    """Render filter controls.
    
    Returns:
        Tuple of (show_completed, batch_size)
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        show_completed = st.checkbox("Erledigte anzeigen", value=False)
    with col2:
        batch_size = st.selectbox("Anzahl", [5, 10, 20], index=1)
    
    return show_completed, batch_size


def render_progress(files: list[FileInfo], decisions: Decisions) -> None:
    """Render progress bar."""
    completed, _, _ = get_decision_stats(decisions)
    progress = completed / len(files) if files else 0
    st.progress(progress, text=f"Fortschritt: {completed}/{len(files)} ({progress:.1%})")


def render_empty_state() -> None:
    """Render empty state when all files are organized."""
    st.success("🎉 Alle Dateien organisiert!")
