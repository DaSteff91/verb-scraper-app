# AGENTS Guide

## Purpose
This repository hosts a Flask-based Portuguese conjugation scraper with both:
- a web UI for interactive lookups and batch jobs
- an authenticated REST API for programmatic scraping and retrieval

The app validates grammar inputs, stores normalized conjugation data in SQLite via SQLAlchemy, and supports CSV output (including Anki-friendly formatting).

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Create `.env` with at least `SECRET_KEY`, `API_KEY`, and `LOG_LEVEL`.
4. Run `python run.py`.

## High-Value Paths
- `src/__init__.py`: Flask app factory, DB init, seed flow, blueprint registration
- `src/routes/main.py`: UI routes
- `src/routes/api.py`: API v1 routes (`/verbs`, `/scrape`, `/batch`, `/health`)
- `src/services/`: core logic (scraping, validation, auth, exporting, verb manager)
- `src/models/`: normalized DB schema
- `tests/`: unit, integration, hardening, and remote contract tests
- `scripts/api_tools/bulk_importer.py`: standalone API-driven bulk workflow

## Agent Working Rules
- Prefer small, isolated changes and keep tests green.
- Do not commit `.env`, databases, or generated CSV exports.
- Preserve existing route and payload contracts unless explicitly asked to break them.
- Keep type hints and validation behavior aligned with current patterns.

## Local Validation Commands
- `pytest`
- `pytest -m "not online"` (offline-friendly subset)
- `python run.py` (manual sanity check)

## Commit and Release Conventions (Observed)
- Human commits mostly follow Conventional Commit-like subjects:
  - `feat(scope): ...`
  - `fix(scope): ...`
  - `test(scope): ...`
- Scope text is often descriptive and can be long; message body is frequently concise and purpose-oriented.
- Release/version commits are generated automatically (for example `1.23.3`) by semantic-release/commitizen tooling.
- Keep future commit messages compatible with semantic version automation.

## Suggested Commit Message Template
Use this shape for manual commits:
- `fix(api): prevent invalid batch payloads from starting background jobs`
- `feat(exporter): add deterministic CSV ordering for stable imports`

Focus on "why this change matters", not only the file list.
