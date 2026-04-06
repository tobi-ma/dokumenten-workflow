"""App configuration and constants."""

from pathlib import Path
from typing import TypedDict

# File paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FILES_JSON = DATA_DIR / "files.json"
DECISIONS_JSON = DATA_DIR / "decisions.json"
FOLDER_STRUCTURE_JSON = DATA_DIR / "folder_structure.json"
FILE_SUMMARIES_JSON = DATA_DIR / "file_summaries.json"
THUMBNAILS_DIR = BASE_DIR / "thumbnails"

# UI Options
DELETE_OPTION = "⚠️ Löschen"
MAIN_FOLDER_OPTION = "(Hauptordner)"
NEW_FOLDER_OPTION = "+ Neuen Unterordner anlegen"

# Hierarchical folder structure - recursive format with 'subfolders'
DEFAULT_FOLDER_STRUCTURE: dict[str, dict] = {
    "Archiv Arbeit": {"subfolders": {}},
    "Ärzte Krankenhaus etc": {"subfolders": {"Laborbefunde": {"subfolders": {}}, "Zahnarzt": {"subfolders": {}}}},
    "Banken": {"subfolders": {}},
    "Bedienungsanleitungen & Produktinformationsblätter": {"subfolders": {}},
    "Cards": {"subfolders": {}},
    "Finanzamt & Steuererklärung": {"subfolders": {"Lohnsteuerbescheinigungen": {"subfolders": {}}}},
    "Gehaltsabrechnungen": {"subfolders": {}},
    "Gutscheine": {"subfolders": {}},
    "Impfen etc": {"subfolders": {}},
    "Kinder Erinnerungen": {"subfolders": {}},
    "Kita & Schule": {"subfolders": {}},
    "Kontakte": {"subfolders": {}},
    "Musik": {"subfolders": {}},
    "Offizielle Schreiben": {"subfolders": {}},
    "Photos": {"subfolders": {}},
    "Receipts": {"subfolders": {}},
    "Rechnungen": {"subfolders": {"Saturn": {"subfolders": {}}}},
    "Selbstständigkeit": {"subfolders": {"Gewerbeanmeldung": {"subfolders": {}}}},
    "Sprachen": {"subfolders": {}},
    "Verschiedenes": {"subfolders": {}},
    "Versicherungen": {"subfolders": {
        "Auto ADAC": {"subfolders": {}},
        "Auto Haftpflicht": {"subfolders": {}},
        "BU Claudi": {"subfolders": {}},
        "BU Tobi": {"subfolders": {}},
        "Hausrat": {"subfolders": {}},
        "Privathaftpflicht": {"subfolders": {}},
        "Rechtsschutz": {"subfolders": {}},
        "Risikoleben": {"subfolders": {}},
        "TK": {"subfolders": {}},
    }},
    "Verträge": {"subfolders": {}},
}

# Flat list for main folders (populated dynamically)
ALL_FOLDERS: list[str] = []


# Type definitions
class FileInfo(TypedDict):
    id: str
    name: str
    date: str
    index: int
    suggested: str


class MoveDecision(TypedDict):
    """A decision to move a file."""
    file_id: str
    file_name: str
    to_folder: str
    main_folder: str
    sub_folder: str | None
    decided_at: str
    new_file_name: str | None  # Optional: neuer Dateiname falls geändert


class DeleteDecision(TypedDict):
    file_id: str
    file_name: str
    decided_at: str


class Decisions(TypedDict):
    moves: list[MoveDecision]
    deletions: list[DeleteDecision]
    last_updated: str | None


class FolderNode(TypedDict, total=False):
    """Recursive folder node with optional subfolders."""
    subfolders: dict[str, "FolderNode"]


class FolderStructure(TypedDict):
    _comment: str
    last_updated: str | None
    root_path: str
    folders: dict[str, FolderNode]


class FileSummary(TypedDict, total=False):
    """Summary of a file's content from OCR/analysis."""
    summary: str
    keywords: list[str]
    page_count: int
    ocr_text: str | None
    suggested_filename: str | None  # KI-Vorschlag für neuen Dateinamen


class FileSummaries(TypedDict):
    """Container for all file summaries."""
    _comment: str
    last_updated: str | None
    summaries: dict[str, FileSummary]
