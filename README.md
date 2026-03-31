# ScanSnap Organizer

Eine Streamlit-App zum Organisieren deiner ScanSnap-Dokumente.

## Setup

1. Repo auf GitHub pushen
2. [Streamlit Cloud](https://streamlit.io/cloud) verbinden
3. App starten

## Workflow

1. Du wählst in der App für jede Datei einen Zielordner
2. Klickst auf "Als Git-Commit vorbereiten"
3. Kopierst das JSON und schickst es mir
4. Ich führe die Verschiebungen in OneDrive aus

## Struktur

```
scansnap-app/
├── streamlit_app.py      # Haupt-App
├── data/
│   ├── files.json        # Liste aller 169 Dateien
│   └── decisions.json    # Deine Entscheidungen
└── .thumbnails/          # Thumbnails (werden aus OneDrive geladen)
```
