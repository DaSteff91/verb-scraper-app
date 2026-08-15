"""
Configuration settings for the Flask Application.

This module loads environment variables and defines the Config class
used to initialize the Flask app context.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Base configuration class.
    """

    # Security
    _secret = os.environ.get("SECRET_KEY")

    if not _secret:
        raise ValueError("No SECRET_KEY set for the application.")

    SECRET_KEY: str = _secret

    _api_key = os.environ.get("API_KEY")

    if not _api_key:
        raise ValueError("No API_KEY set for the application.")

    API_KEY: str = _api_key

    # Database - Absolute Path Logic
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    INSTANCE_PATH: Path = BASE_DIR / "instance"

    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{INSTANCE_PATH / 'app.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # timeout: wait on locks; check_same_thread=False for gthread + batch threads
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        "connect_args": {"timeout": 30, "check_same_thread": False},
    }

    # Logging
    _log_level_raw = os.environ.get("LOG_LEVEL", "INFO").strip()
    if _log_level_raw.isdigit():
        _resolved_log_level: int = int(_log_level_raw)
    else:
        _resolved_log_level = logging.getLevelNamesMapping().get(
            _log_level_raw.upper(), logging.INFO
        )
    LOG_LEVEL: int = _resolved_log_level
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
