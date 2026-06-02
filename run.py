"""
Main entry point for the Portuguese Conjugation Scraper application.

This script initializes the Flask app using the factory pattern
and starts the development server.
"""

from pathlib import Path
import sys


def _ensure_local_venv_site_packages() -> None:
    """
    Ensure project-local virtualenv packages are importable.

    Some environments launch Python through wrappers where the interpreter
    starts but omits the local `.venv` site-packages from `sys.path`.
    This keeps `python3 run.py` resilient by adding the expected local paths
    before importing third-party dependencies.
    """
    project_root: Path = Path(__file__).resolve().parent
    py_version: str = f"python{sys.version_info.major}.{sys.version_info.minor}"

    candidate_paths: list[Path] = [
        project_root / ".venv" / "lib" / py_version / "site-packages",
        project_root / ".venv" / "Lib" / "site-packages",
    ]

    for candidate in candidate_paths:
        if candidate.exists():
            candidate_str: str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)


_ensure_local_venv_site_packages()

from flask import Flask
from src import create_app

# Initialize the application instance
app: Flask = create_app()

if __name__ == "__main__":
    # Running with debug=True enables hot-reloading and better error messages
    app.run(debug=True)
