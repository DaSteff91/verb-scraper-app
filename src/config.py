"""
Configuration settings for the Flask Application.

This module loads environment variables and defines the Config class
used to initialize the Flask app context.
"""

import os
import logging
from pathlib import Path


class Config:
    """
    Base configuration class.
    """

    # Security
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or "dev-key-please-change"

    # Database - Absolute Path Logic
    # 1. Get the directory where config.py lives
    # 2. Go up one level to the project root
    # 3. Target the instance folder
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    INSTANCE_PATH: Path = BASE_DIR / "instance"

    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{INSTANCE_PATH / 'app.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Logging
    LOG_LEVEL: int = logging.DEBUG
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
