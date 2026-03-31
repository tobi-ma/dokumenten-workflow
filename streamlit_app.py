import streamlit as st
import json
import os
import requests
from datetime import datetime
import hmac

st.set_page_config(page_title="ScanSnap Organizer", layout="wide")

# --- OneDrive Integration ---
def get_onedrive_headers():
    """Get auth headers from secrets"""
    if "onedrive_token" not in st.secrets:
        return None
    return {"Authorization": f"Bearer {st.secrets['onedrive_token']}"}

def load_files_from_onedrive():
    """Fetch file list from OneDrive"""
    headers = get_onedrive_headers()
    if not headers:
        return None, "Kein OneDrive Token konfiguriert"
    
    try:
        url = "https://graph.microsoft.com/v1.0/me/drive/root:/ScanSnap:/children"
        resp = requests.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            items = resp.json().get('value', [])
            files = []
            for item in items:
                if not item.get('folder'):
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'date': item.get('lastModifiedDateTime', '')[:10],
                        'suggested': classify_file(item['name']),
                        'index': len(files) + 1
                    })
            return files, None
        elif resp.status_code == 401:
            return None, "Token abgelaufen - Tim muss Token erneuern"
        else:
            return None, f"Fehler: {resp.status_code}"
    except Exception as e:
        return None, str(e)

def get_thumbnail_url(file_id):
    """Get thumbnail URL from OneDrive"""
    headers = get_onedrive_headers()
    if not headers:
        return None
    
    try:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/thumbnails/0/medium"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json().get('url')
    except:
        pass
    return None

def classify_file(filename):
    """Classify document based on filename"""
    fn = filename.lower()
    import re
    patterns = [
        (r'rechnung|invoice', 'Rechnungen'),
        (r'vertrag|contract|bhw', 'Verträge'),
        (r'kündigung', 'Wichtig'),
        (r'versicherung', 'Versicherungen'),
        (r'arzt|kranken|medical', 'Gesundheit'),
        (r'gehalt|lohn', 'Finanzen'),
        (r'bank|konto', 'Finanzen'),
        (r'bescheid|behörde', 'Behörden'),
        (r'steuer|finanzamt', 'Steuern'),
    ]
    for pattern, folder in patterns:
        if re.search(pattern, fn):
            return folder
    if re.search(r'20\d{2}', fn):
        return 'Dokumente'
    return 'Sonstiges'

# --- Password Protection ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["auth"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Passwort", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 Falsches Passwort")
    return False

if not check_password():
    st.stop()

# Load data
@st.cache_data(ttl=300)
def load_files():
    """Load files from OneDrive or fallback to local JSON"""
    # Try OneDrive first
    od_files, error = load_files_from_onedrive()
    if od_files:
        return od_files
    
    # Fallback to local JSON
    st.warning(f"⚠️ OneDrive nicht verfügbar: {error}" if error else "⚠️ Offline-Modus")
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
    """Save decisions and auto-commit to GitHub"""
    os.makedirs("data", exist_ok=True)
    decisions["last_updated"] = datetime.now().isoformat()
    with open("data/decisions.json", "w") as f:
        json.dump(decisions, f, indent=2)
    
    # Auto-commit to GitHub
    try:
        import subprocess
        subprocess.run(["git", "add", "data/decisions.json"], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Update decisions: {len(decisions.get('moves', []))} moves, {len(decisions.get('deletions', []))} deletions"],
            check=True, capture_output=True
        )
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        st.success("✅ Änderungen gespeichert & zu GitHub gepusht!")
    except Exception as e:
        st.warning(f"⚠️ Lokal gespeichert, aber Push fehlgeschlagen: {e}")
        st.info("💡 Sag Tim Bescheid, dass er manuell pullen soll!")

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
                
                # Thumbnail
            with cols[1]:
                st.markdown(f"**{file['name'][:40]}**")
                st.caption(f"📅 {file.get('date', 'unbekannt')}")
                
                # Try to get thumbnail from OneDrive
                thumb_url = get_thumbnail_url(file['id'])
                if thumb_url:
                    st.image(thumb_url, width=150)
                else:
                    # Fallback to local
                    thumb_path = f"thumbnails/{file['id']}_medium.jpg"
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
