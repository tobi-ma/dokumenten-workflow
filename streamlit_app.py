import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="ScanSnap Organizer", layout="wide")

# Load data
@st.cache_data
def load_files():
    """Load file list from JSON"""
    data_file = "data/files.json"
    if os.path.exists(data_file):
        with open(data_file) as f:
            return json.load(f)
    return []

@st.cache_data
def load_decisions():
    """Load existing decisions"""
    if os.path.exists("data/decisions.json"):
        with open("data/decisions.json") as f:
            return json.load(f)
    return {"moves": [], "deletions": [], "last_updated": None}

# Save decisions
def save_decisions(decisions):
    os.makedirs("data", exist_ok=True)
    decisions["last_updated"] = datetime.now().isoformat()
    with open("data/decisions.json", "w") as f:
        json.dump(decisions, f, indent=2)

# Folders
FOLDERS = [
    "Rechnungen",
    "Verträge", 
    "Versicherungen",
    "Gesundheit",
    "Finanzen",
    "Steuern",
    "Behörden",
    "Kita/Schule",
    "Vereine",
    "Dokumente",
    "Sonstiges",
    "⚠️ Löschen"
]

# Main UI
st.title("📄 ScanSnap Document Organizer")
st.markdown("Organisiere deine 169 ScanSnap-Dokumente")

# Load data
files = load_files()
decisions = load_decisions()

# Progress
completed = len(decisions.get("moves", [])) + len(decisions.get("deletions", []))
progress = completed / len(files) if files else 0

st.progress(progress, text=f"Fortschritt: {completed}/{len(files)} ({progress:.1%})")

# Filter options
col1, col2 = st.columns([3, 1])
with col1:
    show_completed = st.checkbox("Erledigte anzeigen", value=False)
with col2:
    batch_size = st.selectbox("Batch-Größe", [5, 10, 20], index=1)

# Get pending files
moved_ids = {m["file_id"] for m in decisions.get("moves", [])}
deleted_ids = {d["file_id"] for d in decisions.get("deletions", [])}
processed_ids = moved_ids | deleted_ids

if show_completed:
    display_files = files
else:
    display_files = [f for f in files if f["id"] not in processed_ids]

# Show files
st.markdown("---")

if not display_files:
    st.success("🎉 Alle Dateien sind organisiert!")
else:
    for i, file in enumerate(display_files[:batch_size], 1):
        with st.container():
            cols = st.columns([1, 3, 2, 2])
            
            # Number and status
            with cols[0]:
                st.markdown(f"**#{file.get('index', '?')}**")
                if file["id"] in moved_ids:
                    st.success("✓")
                elif file["id"] in deleted_ids:
                    st.error("🗑️")
            
            # File info
            with cols[1]:
                st.markdown(f"**{file['name'][:40]}**")
                st.caption(f"📅 {file.get('date', 'unbekannt')}")
                
                # Thumbnail if available
                thumb_path = f".thumbnails/{file['id']}_medium.jpg"
                if os.path.exists(thumb_path):
                    st.image(thumb_path, width=150)
                else:
                    st.info("🖼️ Kein Thumbnail")
            
            # Suggested folder
            with cols[2]:
                st.markdown(f"📁 **{file.get('suggested', 'Dokumente')}**")
            
            # Action
            with cols[3]:
                if file["id"] not in processed_ids:
                    selected = st.selectbox(
                        "Verschieben nach...",
                        [""] + FOLDERS,
                        key=f"select_{file['id']}"
                    )
                    
                    if selected:
                        if selected == "⚠️ Löschen":
                            decisions["deletions"].append({
                                "file_id": file["id"],
                                "file_name": file["name"],
                                "decided_at": datetime.now().isoformat()
                            })
                        else:
                            decisions["moves"].append({
                                "file_id": file["id"],
                                "file_name": file["name"],
                                "to_folder": selected,
                                "decided_at": datetime.now().isoformat()
                            })
                        save_decisions(decisions)
                        st.rerun()
                else:
                    # Show current decision
                    for m in decisions.get("moves", []):
                        if m["file_id"] == file["id"]:
                            st.success(f"→ {m['to_folder']}")
                    for d in decisions.get("deletions", []):
                        if d["file_id"] == file["id"]:
                            st.error("🗑️ Zur Löschung")
        
        st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 Status")
    
    st.metric("Erledigt", f"{completed}/{len(files)}")
    st.metric("Zu verschieben", len(decisions.get("moves", [])))
    st.metric("Zu löschen", len(decisions.get("deletions", [])))
    
    if st.button("💾 Als Git-Commit vorbereiten"):
        # Show JSON for copy
        st.code(json.dumps(decisions, indent=2), language="json")
        st.success("Kopiere dieses JSON und sende es mir!")
    
    if st.button("🔄 Cache leeren"):
        st.cache_data.clear()
        st.rerun()
