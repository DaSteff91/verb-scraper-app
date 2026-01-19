"""
Authentication Service.

Provides decorators and utilities for securing API endpoints.
"""

import logging
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import current_app, jsonify, request

# Initialize logger
logger = logging.getLogger(__name__)

# Type variable for the decorated function
F = TypeVar("F", bound=Callable[..., Any])


def require_api_key(f: F) -> F:
    """
    Decorator to ensure a valid API key is provided in the request headers.

    Checks the 'X-API-KEY' header against the configured master key.

    Args:
        f: The function to be decorated.

    Returns:
        The decorated function or a 401 response if authentication fails.
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        api_key = request.headers.get("X-API-KEY")
        master_key = current_app.config.get("API_KEY")

        if not api_key or api_key != master_key:
            # Security Log: Record failed access attempts with source IP
            logger.warning(
                "Unauthorized API access attempt from IP: %s. Path: %s",
                request.remote_addr,
                request.path,
            )
            return jsonify({"error": "Unauthorized: Invalid or missing API Key"}), 401

        # Debug Log: Trace successful API usage
        logger.debug("API Key authenticated successfully for %s", request.path)
        return f(*args, **kwargs)

    return cast(F, decorated_function)
