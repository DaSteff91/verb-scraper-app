"""
Application Factory Module.

This module contains the function to create and configure the Flask application.
"""

import logging
from typing import cast

from flask import Flask

from .config import Config
from .extensions import db

__version__ = "0.1.0"


def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Initialize the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Cast types to satisfy Pylance "UnknownMemberType"
    # We use app.config directly and cast the results
    log_level = cast(int, app.config["LOG_LEVEL"])
    log_format = cast(str, app.config["LOG_FORMAT"])

    # 2. Configure Logging
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger(__name__)
    logger.info("Initializing Verb Scraper v%s", __version__)

    # 3. Use type: ignore for Flask-SQLAlchemy's dynamic methods
    db.init_app(app)  # type: ignore

    with app.app_context():
        # noqa: F401 stops "Unused Import" warnings
        # type: ignore stops Pylance from complaining about missing .models
        from .models import verb  # noqa: F401 # type: ignore

        logger.debug("Creating database tables if they don't exist...")

        db.create_all()  # type: ignore
        logger.info("Database synchronized.")

    @app.route("/")
    def index() -> str:
        """Root route to verify the server is up."""
        logger.info("Root index reached")
        return f"<h1>Verb Scraper v{__version__}</h1><p>The server is running. Go to <a href='/hello'>/hello</a></p>"

    @app.route("/hello")
    def hello() -> str:
        """Simple test route."""
        # Use a local logger to avoid "unused" warnings for the outer logger if needed
        logging.getLogger(__name__).info("Hello endpoint reached")
        return f"Hello! Verb Scraper v{__version__} is running."

    # Return the app - Pylance should see this as type 'Flask'
    return app
