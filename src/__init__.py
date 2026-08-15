"""
Application Factory Module.

This module contains the function to create and configure the Flask application.
"""

import logging
from typing import Any, cast

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from src.config import Config
from src.extensions import db

__version__ = "1.24.3"


@event.listens_for(Engine, "connect")
def _configure_sqlite_connection(
    dbapi_connection: Any, _connection_record: Any
) -> None:
    """
    Apply SQLite pragmas that improve concurrent scrape + healthcheck behavior.
    """
    # This app is SQLite-only; skip non-sqlite DBAPI modules defensively.
    module_name = type(dbapi_connection).__module__
    if "sqlite" not in module_name:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Initialize the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Cast types to satisfy Pylance "UnknownMemberType"
    log_level = cast(int, app.config["LOG_LEVEL"])
    log_format = cast(str, app.config["LOG_FORMAT"])

    # 2. Configure Logging
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger(__name__)
    logger.info("Initializing Portuguese Conjugation Scraper v%s", __version__)

    # 3. Use type: ignore for Flask-SQLAlchemy's dynamic methods
    db.init_app(app)  # type: ignore

    with app.app_context():
        from src.models import verb  # noqa: F401 # type: ignore

        logger.debug("Creating database tables if they don't exist...")

        db.create_all()  # type: ignore
        logger.info("Database synchronized.")
        logger.info("Portuguese Conjugation Scraper v%s initialized.", __version__)

        from src.services.verb_manager import VerbManager

        VerbManager().seed_default_data()

        logger.info("Database synchronized and seeded.")

    from src.routes.main import main_bp

    app.register_blueprint(main_bp)

    from src.routes.api import api_bp

    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_version() -> dict[str, str]:
        return dict(version=__version__)

    return app
