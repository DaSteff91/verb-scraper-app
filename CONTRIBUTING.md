# Contributing

Thank you for improving the Portuguese Conjugation Scraper.

## Branching Strategy

- `main` is the stable release branch.
- `dev` is the integration branch for ongoing work.
- Feature and fix work should be done in short-lived branches from `dev`:
  - `feature/<short-name>`
  - `fix/<short-name>`

Expected flow:
1. `feature/*` or `fix/*` -> PR to `dev`
2. `dev` stabilization -> PR to `main`

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Required Checks Before Opening a PR

```bash
black --check .
ruff check .
mypy src
pytest -m "not online"
```

If your change impacts deployment or external API behavior, also run relevant remote checks.

## Commit Message Convention

Use Conventional Commit style when possible:
- `feat(scope): ...`
- `fix(scope): ...`
- `test(scope): ...`
- `docs(scope): ...`
- `chore(scope): ...`

Keep commit messages intent-focused (why), not just file-focused (what).

## Pull Request Expectations

- Keep PRs small and focused.
- Include a clear test plan.
- Call out API contract changes explicitly.
- Update docs (`README.md`, `AGENTS.md`, this file) if behavior or workflow changes.

## Definition of Done

A change is done when all items below are true:
- CI checks are green (format, lint, type-check, tests).
- API behavior is backward compatible, or breaking changes are clearly documented.
- New behavior is covered by tests (or test-gap rationale is stated in PR).
- Documentation is updated when user-facing behavior or workflows change.
- No secrets, local databases, or generated exports are committed.

## Agent Guidance

If you are using Cursor agents, also follow `AGENTS.md` for repository-specific coding and testing patterns.
