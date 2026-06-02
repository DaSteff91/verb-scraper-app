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
- Follow `CONTRIBUTING.md` for branch flow and required validation commands.

## Decision Log Usage (Mandatory)

- Before implementing or reviewing work, read `docs/decision-log.md` to understand prior rationale and trade-offs.
- Treat the decision log as implementation intent: prefer solutions that stay aligned with recorded decisions unless the user requests a change.
- When you intentionally deviate from a logged decision, document the new rationale in `docs/decision-log.md` in the same session.
- For non-obvious choices, add a concise "why" entry to `docs/decision-log.md` so future agents inherit context.

## Python Code Standards (Repository-Observed)

- Use module-level docstrings that explain intent and system role, not only syntax details.
- Use explicit typing broadly (`-> None`, concrete variable annotations, `Dict[str, Any]`, `Optional[...]`).
- Keep imports grouped by standard library, third-party, then local `src.*` modules.
- Keep route handlers and service methods small and staged with numbered comments for major phases (`# 1.`, `# 2.`) where useful.
- Prefer defensive validation early with explicit error returns instead of deep nesting.
- Use `logging` with lazy interpolation (`logger.info("... %s", value)`) instead of f-strings in log calls.
- Use clear orchestration naming in services (`get_or_create_*`, `process_batch`, `seed_*`) and keep DB write paths wrapped with rollback-safe `try/except`.
- Preserve existing Flask + SQLAlchemy style (`query.filter_by(...).first()`, `db.session.get(...)`, app context handling for threaded/background work).

## Testing Standards (Repository-Observed)

- Tests should include short docstrings describing scenario and expected behavior.
- Prefer Arrange/Act/Assert flow, often with lightweight numbered step comments.
- Keep test names behavior-first (`test_api_batch_full_lifecycle`, `test_export_csv_route_no_data`).
- Use `requests_mock` for scraper upstream simulation and keep payloads realistic.
- Assert both status/contract and critical payload content (not just status codes).
- For asynchronous behavior, use bounded polling loops with clear retry limits instead of unbounded waits.

## Local Validation Commands

- `pytest`
- `pytest -m "not online"` (offline-friendly subset)
- `python run.py` (manual sanity check)
- `black --check .`
- `ruff check .`
- `mypy src`

## Branching Workflow

- `main` is stable and release-oriented.
- `dev` is integration-first for feature/fix work.
- Agents should prefer `feature/*` -> `dev` and avoid direct `main` changes unless explicitly requested.

## Shared Definition of Done

- CI quality checks pass (format, lint, type-check, tests).
- API contract changes are validated and documented.
- README/contributor/agent docs are updated when workflows or behavior change.
- No sensitive or local runtime artifacts are committed.

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
