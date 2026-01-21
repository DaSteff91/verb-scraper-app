"""
Lean Health Check Probe.

A lightweight script used by Docker to verify the application's internal
health. Uses only Python standard libraries to maintain a minimal footprint
consistent with the project's ultra-lean requirements.
"""

import os
import sys
import urllib.request
from typing import NoReturn


def check_health() -> NoReturn:
    """
    Performs an internal HTTP request to the diagnostic health endpoint.

    Queries the local Gunicorn instance. Exits with code 0 if the status
    is healthy (200 OK), otherwise exits with code 1 to signal an
    unhealthy state to the Docker engine.
    """
    # Use 127.0.0.1 to stay strictly inside the container loopback
    url: str = "http://127.0.0.1:5050/api/v1/health"
    api_key: str = os.environ.get("API_KEY", "")
    timeout: int = 5

    headers = {"X-API-KEY": api_key, "User-Agent": "HealthCheckProbe/1.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                # Silent success - no logging needed
                sys.exit(0)
            else:
                # Infrastructure messaging on failure
                sys.stderr.write(
                    f"Health check failed: Server returned {response.getcode()}\n"
                )
                sys.exit(1)

    except Exception as e:
        # Infrastructure messaging on crash
        sys.stderr.write(f"Health check failed: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    check_health()
