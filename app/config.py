"""App configuration and constants."""

from typing import TypedDict

# File paths
DATA_DIR = "data"
FILES_JSON = f"{DATA_DIR}/files.json"
DECISIONS_JSON = f"{DATA_DIR}/decisions.json"
THUMBNAILS_DIR = "thumbnails"

# UI Options
DELETE_OPTION = "⚠️ Löschen"
MAIN_FOLDER_OPTION = "(Hauptordner)"
NEW_FOLDER_OPTION = "+ Neuen Unterordner anlegen"

# Hierarchical folder structure from OneDrive ScanSnap
FOLDER_STRUCTURE: dict[str, list[str]] = {
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
    "Versicherungen": [
        "Auto ADAC",
        "Auto Haftpflicht",
        "BU Claudi",
        "BU Tobi",
        "Hausrat",
        "Privathaftpflicht",
        "Rechtsschutz",
        "Risikoleben",
        "TK",
    ],
    "Verträge": [],
}

# Flat list for main folders
ALL_FOLDERS: list[str] = list(FOLDER_STRUCTURE.keys())


# Type definitions
class FileInfo(TypedDict):
    id: str
    name: str
    date: str
    index: int
    suggested: str


class MoveDecision(TypedDict):
    file_id: str
    file_name: str
    to_folder: str
    main_folder: str
    sub_folder: str | None
    decided_at: str


class DeleteDecision(TypedDict):
    file_id: str
    file_name: str
    decided_at: str


class Decisions(TypedDict):
    moves: list[MoveDecision]
    deletions: list[DeleteDecision]
    last_updated: str | None
