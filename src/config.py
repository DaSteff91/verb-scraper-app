"""
Configuration settings for the Flask Application.

This module loads environment variables and defines the Config class
used to initialize the Flask app context.
"""

import os
import logging
from pathlib import Path
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

    # Database - Absolute Path Logic
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    INSTANCE_PATH: Path = BASE_DIR / "instance"

    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{INSTANCE_PATH / 'app.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Logging
    LOG_LEVEL: int = logging.DEBUG
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
