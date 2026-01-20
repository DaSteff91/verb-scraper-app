"""
Lean Health Check Probe.
...
"""

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
    url: str = "http://127.0.0.1:5050/api/v1/health"
    timeout: int = 5

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
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
