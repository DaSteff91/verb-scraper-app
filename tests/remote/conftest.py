"""
Configuration for Remote API Testing.

This module provides fixtures for interacting with a deployed instance
of the Portuguese Conjugation Scraper API.
"""

import os
import pytest
from typing import Dict


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
