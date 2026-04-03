"""UI components for the document organizer."""

import logging

import streamlit as st

from app.config import (
    DELETE_OPTION,
    MAIN_FOLDER_OPTION,
    NEW_FOLDER_OPTION,
    FileInfo,
    Decisions,
    FileSummary,
)
from app.utils import get_folder_path, find_thumbnail
from app.data_service import (
    get_decision_stats, 
    get_processed_file_ids,
    get_all_folders,
    get_subfolders,
    get_file_summary,
)

logger = logging.getLogger(__name__)

# UI Constants
NEW_MAIN_FOLDER_OPTION = "+ Neuen Hauptordner erstellen"


def render_file_card(
    file: FileInfo,
    decisions: Decisions,
    on_decision: callable,
) -> None:
    """Render a single file card with thumbnail, summary and folder selector.
    
    Args:
        file: File information
        decisions: Current decisions state
        on_decision: Callback when a decision is made (file_id, action, data)
    """
    processed_ids = get_processed_file_ids(decisions)
    summary = get_file_summary(file["id"])
    
    with st.container():
        cols = st.columns([1, 4, 2, 2])
        
        with cols[0]:
            st.markdown(f"**#{file.get('index', '?')}**")
        
        with cols[1]:
            st.markdown(f"**{file['name'][:50]}**")
            st.caption(f"📅 {file.get('date', 'unbekannt')}")
            
            # Thumbnail and summary side by side
            thumb_path = find_thumbnail(file["id"])
            if thumb_path or summary:
                thumb_col, summary_col = st.columns([1, 1])
                
                with thumb_col:
                    if thumb_path:
                        st.image(thumb_path, use_container_width=True)
                    else:
                        st.info("�️ Kein Thumbnail")
                
                with summary_col:
                    if summary:
                        st.markdown(f"**{summary.get('summary', '')}**")
                        if summary.get('keywords'):
                            st.caption(f"🏷️ {', '.join(summary['keywords'][:5])}")
                        if summary.get('page_count'):
                            st.caption(f"📄 {summary['page_count']} Seiten")
                    else:
                        st.caption("📝 Keine Zusammenfassung")
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
    """Render folder selection with unlimited nesting levels."""
    all_folders = get_all_folders()
    
    # Main folder selection
    main_folder = st.selectbox(
        "Hauptordner...",
        [""] + all_folders + [NEW_MAIN_FOLDER_OPTION, DELETE_OPTION],
        key=f"main_{file['id']}",
    )
    
    # Handle new main folder creation
    if main_folder == NEW_MAIN_FOLDER_OPTION:
        new_main = st.text_input(
            "Name des neuen Hauptordners:",
            key=f"new_main_{file['id']}",
        )
        if new_main:
            main_folder = new_main
    
    # Build path progressively
    selected_path = []
    if main_folder and main_folder not in (DELETE_OPTION, NEW_MAIN_FOLDER_OPTION, ""):
        selected_path = [main_folder]
        
        # Check if this is a known folder with subfolders
        is_known = main_folder in all_folders
        
        # Keep adding subfolder selectors as long as there are subfolders or user wants to create one
        level = 0
        while True:
            current_subfolders = get_subfolders(selected_path) if is_known else []
            
            # Options for this level
            options = [MAIN_FOLDER_OPTION]
            if current_subfolders:
                options.extend(current_subfolders)
            options.append(NEW_FOLDER_OPTION)
            
            # Show dropdown for this level
            sub_choice = st.selectbox(
                f"{'Unterordner' if level == 0 else 'Unterunterordner'}...",
                options,
                key=f"sub_{level}_{file['id']}",
            )
            
            if sub_choice == MAIN_FOLDER_OPTION:
                # Stop here, use current path
                break
            elif sub_choice == NEW_FOLDER_OPTION:
                # Create new folder at this level
                new_name = st.text_input(
                    f"Name des neuen {'Unterordners' if level == 0 else 'Unterunterordners'}:",
                    key=f"new_sub_{level}_{file['id']}",
                )
                if new_name:
                    selected_path.append(new_name)
                break
            else:
                # Selected existing subfolder, go deeper
                selected_path.append(sub_choice)
                level += 1
                
                # Check if there are deeper levels
                deeper_subfolders = get_subfolders(selected_path) if is_known else []
                if not deeper_subfolders:
                    # No deeper levels available, but user can still add more
                    continue
    
    # Confirm button
    if main_folder and st.button("✅ Verschieben", key=f"btn_{file['id']}"):
        if main_folder == DELETE_OPTION:
            on_decision(file, "delete", None)
        else:
            # Build target path
            if len(selected_path) == 1:
                # Just main folder
                target_path = selected_path[0]
                sub_folder = None
            else:
                # Main + subfolders
                target_path = "/".join(selected_path)
                sub_folder = "/".join(selected_path[1:]) if len(selected_path) > 1 else None
            
            on_decision(file, "move", {
                "to_folder": target_path,
                "main_folder": selected_path[0] if selected_path else main_folder,
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


def render_sidebar(
    files: list[FileInfo],
    decisions: Decisions,
    pending_count: int = 0,
    pending_moves: list | None = None,
    pending_deletions: list | None = None
) -> bool:
    """Render sidebar with status, controls, and pending changes.

    Args:
        files: List of all files
        decisions: Current decisions from storage
        pending_count: Number of pending (not yet committed) decisions
        pending_moves: List of pending move decisions
        pending_deletions: List of pending delete decisions

    Returns:
        True if refresh/send was triggered
    """
    from datetime import datetime

    pending_moves = pending_moves or []
    pending_deletions = pending_deletions or []

    with st.sidebar:
        st.header("📊 Status")

        completed, moves_count, deletions_count = get_decision_stats(decisions)
        total_completed = completed + pending_count

        st.metric("Erledigt", f"{total_completed}/{len(files)}")
        st.metric("Verschieben", moves_count + len(pending_moves))
        st.metric("Löschen", deletions_count + len(pending_deletions))

        st.markdown("---")

        # Pending changes section
        if pending_count > 0:
            st.subheader(f"📤 {pending_count} ausstehend")

            # Show list of pending items
            with st.expander("Anzeigen", expanded=False):
                for move in pending_moves:
                    st.caption(f"📁 {move['file_name'][:30]}...")
                for deletion in pending_deletions:
                    st.caption(f"🗑️ {deletion['file_name'][:30]}...")

            # Send button in sidebar
            if st.button("🚀 Alle senden", type="primary", use_container_width=True):
                # Perform the send action
                from app.data_service import save_decisions
                from app.git_service import save_and_commit

                # Merge pending with existing decisions
                updated_decisions = {
                    "moves": list(decisions.get("moves", [])) + pending_moves,
                    "deletions": list(decisions.get("deletions", [])) + pending_deletions,
                    "last_updated": datetime.now().isoformat(),
                }

                # Save locally first
                save_decisions(updated_decisions)

                # Try to commit to GitHub
                try:
                    success, message = save_and_commit(len(updated_decisions["moves"]))
                    if success:
                        st.success("✅ Gesendet!")
                        # Clear pending by modifying session state (caller should rerun)
                        return True
                    else:
                        st.warning(message)
                        return True  # Still trigger rerun to show updated state
                except Exception as e:
                    st.error(f"⚠️ Fehler: {e}")
                    return True

            st.markdown("---")

        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.cache_data.clear()
            return True

        st.markdown("---")
        
        # Show folder structure info
        from app.data_service import load_folder_structure, load_file_summaries
        import os
        from app.config import FOLDER_STRUCTURE_JSON, FILE_SUMMARIES_JSON
        
        folder_count = len(load_folder_structure())
        st.caption(f"📁 {folder_count} Ordner geladen")
        
        if os.path.exists(FOLDER_STRUCTURE_JSON):
            import json
            with open(FOLDER_STRUCTURE_JSON) as f:
                data = json.load(f)
                if data.get("last_updated"):
                    st.caption(f"🕐 Ordner-Stand: {data['last_updated'][:10]}")
        
        # Show file summaries info
        summary_count = len(load_file_summaries())
        st.caption(f"📝 {summary_count} Zusammenfassungen geladen")
        
        if os.path.exists(FILE_SUMMARIES_JSON):
            import json
            with open(FILE_SUMMARIES_JSON) as f:
                data = json.load(f)
                if data.get("last_updated"):
                    st.caption(f"🕐 Zusammenfassungen-Stand: {data['last_updated'][:10]}")
        
        st.markdown("---")
        st.info("💡 Thumbnails und Zusammenfassungen werden von Tim bereitgestellt.")
        
        return False


def render_pending_changes(pending_moves: list, pending_deletions: list) -> bool:
    """Render pending changes section with send button.
    
    Args:
        pending_moves: List of pending move decisions
        pending_deletions: List of pending delete decisions
        
    Returns:
        True if send button was clicked
    """
    total_pending = len(pending_moves) + len(pending_deletions)
    
    if total_pending == 0:
        return False
    
    with st.container():
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(f"📤 **{total_pending} Entscheidungen** bereit zum Senden")
            
            # Show details in expander
            with st.expander("Details anzeigen"):
                for move in pending_moves:
                    st.caption(f"📁 {move['file_name'][:40]} → {move['to_folder']}")
                for deletion in pending_deletions:
                    st.caption(f"🗑️ {deletion['file_name'][:40]}")
        
        with col2:
            return st.button("🚀 Alle senden", type="primary", use_container_width=True)
    
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
