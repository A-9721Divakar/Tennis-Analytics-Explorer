"""Central configuration for the Tennis Analytics project.

Settings are resolved in this order:
1. Environment variables (also loaded from a local ``.env`` file)
2. Streamlit secrets (``.streamlit/secrets.toml`` locally, or the Secrets
   panel on Streamlit Community Cloud)
3. Sensible defaults (SQLite database, ``trial`` API access level)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

load_dotenv(BASE_DIR / ".env")

API_BASE_URL = "https://api.sportradar.com/tennis"

# Dataset name -> endpoint path (relative to /tennis/{access_level}/v3/{language}/).
# Kept in one place so a path change on Sportradar's side is a one-line fix.
ENDPOINTS = {
    "competitions": "competitions.json",
    "complexes": "complexes.json",
    "rankings": "double_competitors_rankings.json",
}


def get_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return a setting from the environment or Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:  # Streamlit is optional for CLI usage
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # noqa: BLE001 - secrets file may simply not exist
        pass
    return default


def get_database_url() -> str:
    """Return a SQLAlchemy URL. Defaults to a local SQLite file."""
    url = get_setting("DATABASE_URL")
    if not url:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(DATA_DIR / 'tennis.db').as_posix()}"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("mysql://"):
        url = "mysql+pymysql://" + url[len("mysql://"):]
    return url


def get_api_settings() -> dict:
    """Return Sportradar API settings."""
    return {
        "api_key": get_setting("SPORTRADAR_API_KEY"),
        "access_level": get_setting("SPORTRADAR_ACCESS_LEVEL", "trial"),
        "language": get_setting("SPORTRADAR_LANGUAGE", "en"),
        "request_delay": float(get_setting("SPORTRADAR_REQUEST_DELAY", "1.2")),
    }
