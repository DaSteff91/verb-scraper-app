"""
Global Pytest Configuration and Fixtures.

This module defines the fixtures required for testing the Flask application,
including the app instance, database setup, and mock data loaders.
"""

from pathlib import Path
from typing import Generator

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
