# ScanSnap Organizer

Eine Streamlit-App zum Organisieren deiner ScanSnap-Dokumente.

## Setup

1. Repo auf GitHub pushen
2. [Streamlit Cloud](https://streamlit.io/cloud) verbinden
3. App starten

## Workflow

1. Du wählst in der App für jede Datei einen Zielordner
2. Klickst auf "Verschieben"
3. Entscheidungen werden automatisch in Git gespeichert
4. Die Verschiebungen werden in OneDrive ausgeführt

## Projektstruktur

```
dokumenten-workflow/
├── streamlit_app.py           # Einstiegspunkt (nur 85 Zeilen)
├── app/
│   ├── __init__.py
│   ├── config.py              # Konfiguration, Konstanten, Typen
│   ├── auth.py                # Passwort-Schutz
│   ├── data_service.py        # JSON Laden/Speichern
│   ├── git_service.py         # Git-Auto-Commit
│   ├── utils.py               # Hilfsfunktionen (Thumbnail-Suche)
│   └── ui/
│       ├── __init__.py
│       └── components.py      # UI-Komponenten
├── data/
│   ├── files.json             # Liste aller Dateien
│   └── decisions.json         # Deine Entscheidungen
└── thumbnails/                # Thumbnails (aus OneDrive)
```

## Architektur

- **Modulare Struktur**: Klare Trennung von UI, Daten und Business-Logik
- **Typisierung**: `TypedDict` für alle Datenstrukturen
- **Logging**: Strukturierte Logs statt print-Statements
- **Fehlerbehandlung**: Spezifische Exceptions statt `except:`
- **Konfiguration**: Alle Konstanten in `config.py`
