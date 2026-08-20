"""
Application Configuration and Path Resolution Module.
Ensures offline-first, Windows application-data location separation.
"""

import sys
import os
from pathlib import Path

APP_NAME = "SmartClinicalLab"
APP_VERSION = "1.0.0"

def get_app_dir() -> Path:
    """
    Returns appropriate application data directory depending on OS.
    Windows: %LOCALAPPDATA%\\SmartClinicalLab
    Linux/macOS fallback: ~/.local/share/SmartClinicalLab
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            app_dir = Path(base) / APP_NAME
        else:
            app_dir = Path.home() / "AppData" / "Local" / APP_NAME
    else:
        app_dir = Path.home() / ".local" / "share" / APP_NAME

    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def get_db_path() -> Path:
    return get_app_dir() / "smart_lab.db"

def get_backups_dir() -> Path:
    b_dir = get_app_dir() / "backups"
    b_dir.mkdir(parents=True, exist_ok=True)
    return b_dir

def get_reports_dir() -> Path:
    r_dir = get_app_dir() / "reports"
    r_dir.mkdir(parents=True, exist_ok=True)
    return r_dir

def get_logs_dir() -> Path:
    l_dir = get_app_dir() / "logs"
    l_dir.mkdir(parents=True, exist_ok=True)
    return l_dir

def get_assets_dir() -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent.parent
    assets_path = base_path / "assets"
    assets_path.mkdir(parents=True, exist_ok=True)
    return assets_path
