"""
Application Factory Module.

This module contains the function to create and configure the Flask application.
"""

import logging
from typing import cast

from flask import Flask

from src.config import Config
from src.extensions import db

__version__ = "1.17.1"


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
    logger.info("Initializing Verb Scraper v%s", __version__)

    # 3. Use type: ignore for Flask-SQLAlchemy's dynamic methods
    db.init_app(app)  # type: ignore

    with app.app_context():
        from src.models import verb  # noqa: F401 # type: ignore

        logger.debug("Creating database tables if they don't exist...")

        db.create_all()  # type: ignore
        logger.info("Database synchronized.")
        logger.info("Verb Scraper v%s initialized.", __version__)

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
