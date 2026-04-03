import streamlit as st
import json
import os
from datetime import datetime
import subprocess

st.set_page_config(page_title="ScanSnap Organizer", layout="wide")

# --- Password Protection ---
def check_password():
    """Returns True if the user had the correct password."""
    
    # Get password from secrets
    try:
        correct_password = st.secrets.get("auth", {}).get("password", "")
        if not correct_password:
            # Fallback: Kein Passwort = direkter Zugriff
            return True
    except:
        return True  # Keine Secrets = direkter Zugriff
    
    def password_entered():
        entered = st.session_state.get("password", "")
        if entered == correct_password:
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Passwort", type="password", on_change=password_entered, key="password")
    if st.session_state.get("password_correct") is False:
        st.error("😕 Falsches Passwort")
    return False

if not check_password():
    st.stop()

st.success("✅ Passwort korrekt! App lädt...")

# --- Data Loading ---
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

def save_decisions(decisions):
    """Save decisions and auto-commit to GitHub"""
    os.makedirs("data", exist_ok=True)
    decisions["last_updated"] = datetime.now().isoformat()
    with open("data/decisions.json", "w") as f:
        json.dump(decisions, f, indent=2)
    
    # Auto-commit to GitHub
    try:
        subprocess.run(["git", "add", "data/decisions.json"], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Update decisions: {len(decisions.get('moves', []))} moves"],
            check=True, capture_output=True
        )
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        st.success("✅ Gespeichert & gepusht!")
    except Exception as e:
        st.warning(f"⚠️ Lokal gespeichert")

# Hierarchical folder structure from OneDrive ScanSnap
FOLDER_STRUCTURE = {
    "Archiv Arbeit": [],
    "Ärzte Krankenhaus etc": ["Laborbefunde", "Zahnarzt"],
    "Banken": [],
    "Bedienungsanleitungen & Produktinformationsblätter": [],
    "Cards": [],
    "Finanzamt & Steuererklärung": ["Lohnsteuerbescheinigungen"],
    "Gehaltsabrechnungen": [],
    "Gutscheine": [],
    "Impfen etc": [],
    "Kinder Erinnerungen": [],
    "Kita & Schule": [],
    "Kontakte": [],
    "Musik": [],
    "Offizielle Schreiben": [],
    "Photos": [],
    "Receipts": [],
    "Rechnungen": ["Saturn"],
    "Selbstständigkeit": ["Gewerbeanmeldung"],
    "Sprachen": [],
    "Verschiedenes": [],
    "Versicherungen": ["Auto ADAC", "Auto Haftpflicht", "BU Claudi", "BU Tobi", "Hausrat", "Privathaftpflicht", "Rechtsschutz", "Risikoleben", "TK"],
    "Verträge": [],
}

# Flat list for main folders
ALL_FOLDERS = list(FOLDER_STRUCTURE.keys())

# Helper function to get full path
def get_folder_path(main_folder, sub_folder=None):
    """Returns the full path for OneDrive"""
    if sub_folder and sub_folder != "(Hauptordner)":
        return f"{main_folder}/{sub_folder}"
    return main_folder

# Main UI
st.title("📄 ScanSnap Document Organizer")
st.markdown("Organisiere deine Dokumente - Thumbnails werden von Tim bereitgestellt")

files = load_files()
decisions = load_decisions()

# Progress
completed = len(decisions.get("moves", [])) + len(decisions.get("deletions", []))
progress = completed / len(files) if files else 0
st.progress(progress, text=f"Fortschritt: {completed}/{len(files)} ({progress:.1%})")

# Filter
col1, col2 = st.columns([3, 1])
with col1:
    show_completed = st.checkbox("Erledigte anzeigen", value=False)
with col2:
    batch_size = st.selectbox("Anzahl", [5, 10, 20], index=1)

# Get files to show
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
    st.success("🎉 Alle Dateien organisiert!")
else:
    for i, file in enumerate(display_files[:batch_size], 1):
        with st.container():
            cols = st.columns([1, 4, 2, 2])
            
            with cols[0]:
                st.markdown(f"**#{file.get('index', '?')}**")
            
            with cols[1]:
                st.markdown(f"**{file['name'][:50]}**")
                st.caption(f"📅 {file.get('date', 'unbekannt')}")
                
                # Thumbnail - priority: PyMuPDF (page1) > OneDrive large > OneDrive medium
                # Thumbnails exist with both '!' and '_' as separator, check both
                file_id_clean = file['id'].replace('!', '_')
                file_id_raw = file['id']
                thumb_candidates = [
                    f"thumbnails/{file_id_clean}_page1.jpg",
                    f"thumbnails/{file_id_raw}_page1.jpg",
                    f"thumbnails/{file_id_clean}_large.jpg",
                    f"thumbnails/{file_id_raw}_large.jpg",
                    f"thumbnails/{file_id_clean}_medium.jpg",
                    f"thumbnails/{file_id_raw}_medium.jpg",
                ]
                
                thumb_path = next((t for t in thumb_candidates if os.path.exists(t)), None)
                if thumb_path:
                    st.image(thumb_path, width=400)
                else:
                    st.info("🖼️ Kein Thumbnail vorhanden")
            
            with cols[2]:
                st.markdown(f"📁 **{file.get('suggested', 'Dokumente')}**")
            
            with cols[3]:
                if file["id"] not in processed_ids:
                    # First dropdown: Main folder
                    main_folder = st.selectbox(
                        "Hauptordner...",
                        [""] + ALL_FOLDERS + ["⚠️ Löschen"],
                        key=f"main_{file['id']}"
                    )
                    
                    # Second dropdown: Subfolder (if main selected and has subfolders)
                    sub_folder = None
                    if main_folder and main_folder in FOLDER_STRUCTURE and main_folder != "⚠️ Löschen":
                        subfolders = FOLDER_STRUCTURE[main_folder]
                        if subfolders:
                            sub_options = ["(Hauptordner)"] + subfolders + ["+ Neuen Unterordner anlegen"]
                            sub_folder = st.selectbox(
                                "Unterordner...",
                                sub_options,
                                key=f"sub_{file['id']}"
                            )
                            
                            # Handle new subfolder creation
                            if sub_folder == "+ Neuen Unterordner anlegen":
                                new_folder = st.text_input(
                                    "Name des neuen Unterordners:",
                                    key=f"new_{file['id']}"
                                )
                                if new_folder:
                                    sub_folder = new_folder
                    
                    # Confirm button
                    if main_folder and st.button("✅ Verschieben", key=f"btn_{file['id']}"):
                        if main_folder == "⚠️ Löschen":
                            decisions["deletions"].append({
                                "file_id": file["id"],
                                "file_name": file["name"],
                                "decided_at": datetime.now().isoformat()
                            })
                        else:
                            target_path = get_folder_path(main_folder, sub_folder)
                            decisions["moves"].append({
                                "file_id": file["id"],
                                "file_name": file["name"],
                                "to_folder": target_path,
                                "main_folder": main_folder,
                                "sub_folder": sub_folder,
                                "decided_at": datetime.now().isoformat()
                            })
                        save_decisions(decisions)
                        st.rerun()
                else:
                    for m in decisions.get("moves", []):
                        if m["file_id"] == file["id"]:
                            st.success(f"→ {m['to_folder']}")
        
        st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 Status")
    st.metric("Erledigt", f"{completed}/{len(files)}")
    st.metric("Verschieben", len(decisions.get("moves", [])))
    st.metric("Löschen", len(decisions.get("deletions", [])))
    
    if st.button("🔄 Status aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.info("💡 Thumbnails werden von Tim bereitgestellt und automatisch aktualisiert.")
