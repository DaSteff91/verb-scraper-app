"""
Flask Extensions Module.

This module initializes the extensions used by the application
to avoid circular imports.
"""

from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()
