"""
Global Pytest Configuration and Fixtures.

This module defines the fixtures required for testing the Flask application,
including the app instance, database setup, mock data loaders and a deployed instance of the Verb Scraper API.
"""

from pathlib import Path
from typing import Generator, Dict

import pytest
from flask import Flask
from flask.testing import FlaskClient

from src import create_app
from src.config import Config
from src.extensions import db as _db


class TestConfig(Config):
    """
    Configuration overrides for testing.
    """

    TESTING = True
    # Use an in-memory database for speed and isolation
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Disable CSRF or other security if needed for simple testing
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """
    Create and configure a fresh Flask application instance for each test.

    Yields:
        Flask: The configured test application.
    """
    app = create_app(TestConfig)

    # Establish an application context before running the tests
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """
    A test client for the application.

    Args:
        app: The current Flask application fixture.

    Returns:
        FlaskClient: An object to simulate browser requests.
    """
    return app.test_client()


@pytest.fixture
def sample_html() -> Generator[callable, None, None]:
    """
    Provides a helper function to load HTML samples from the disk.

    Returns:
        callable: A function that takes a filename and returns the content.
    """

    def _load_sample(filename: str) -> str:
        base_path = Path(__file__).parent / "samples"
        file_path = base_path / filename
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    return _load_sample


@pytest.fixture(scope="session")
def api_config() -> Dict[str, str]:
    """
    Provides the base URL and API Key for remote testing.

    Expected environment variables:
    - TEST_API_URL: e.g., 'https://conjugator.kite-engineer.de'
    - TEST_API_KEY: The secure token configured on the server.
    """
    base_url = os.getenv("TEST_API_URL", "http://localhost:5050").rstrip("/")
    api_key = os.getenv("TEST_API_KEY")

    if not api_key:
        pytest.fail("Environment variable 'TEST_API_KEY' is not set.")

    return {"base_url": base_url, "api_key": api_key, "v1_prefix": f"{base_url}/api/v1"}


@pytest.fixture(scope="session")
def auth_header(api_config: Dict[str, str]) -> Dict[str, str]:
    """Provides the standard authentication header for API requests."""
    return {"X-API-KEY": api_config["api_key"]}
