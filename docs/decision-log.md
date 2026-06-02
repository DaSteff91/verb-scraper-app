# Decision Log

This file records why specific implementation choices were made, especially where intent is not obvious from the code diff alone.

## 2026-06-02 - Unified single/multi scrape form

### Context (In-page UX)

- The UI needed to support both single-verb scraping and multi-verb batch scraping from one unchanged form.
- A bug caused some single-verb runs to show duplicate results.

### Decisions (In-page UX)

- **Use explicit dual actions on the same form (`Scrape Now` and `Add to Cart`)**
  - Why: removes coupling between behavior and a global toggle state.
  - Why: makes intent obvious per click and avoids accidental mode state confusion.

- **Keep shopping cart behavior and payload contract untouched**
  - Why: existing downstream routes (`/batch-scrape`, `/results-batch`, `/export-batch`) already work and are tested.
  - Why: lowers regression risk by changing only the action trigger path, not the cart data shape.

- **Remove duplicate hidden `tense` input and keep dynamic hidden lists**
  - Why: duplicate hidden form fields were a likely source of duplicated submitted tenses.
  - Why: hidden fields should mirror selection state exactly once per value.

- **Add backend dedupe guard in `index` POST flow**
  - Why: frontend controls should prevent duplicates, but backend must still be resilient to malformed or repeated payload entries.
  - Why: set-backed dedupe on `(verb, mode, tense)` ensures idempotent task construction.

- **Preserve current redirect/results behavior for single scrape**
  - Why: existing UX and tests expect redirect into the grouped results page, so this avoids unnecessary behavior churn.

- **Add defensive `action=cart` handling server-side**
  - Why: carting is a client-side queue operation; if posted to `/`, the route should not scrape silently.
  - Why: explicit warning keeps behavior understandable and protects against unexpected clients.

### Test strategy

- Added test coverage for:
  - visible dual-action controls on index page
  - duplicate tense submission dedupe behavior
  - defensive handling for `action=cart` on `/`
- Rationale: these tests directly lock the refactor contract and the duplicate regression fix.

## 2026-06-02 - In-page scrape summary UX

### Context

- Redirecting to a separate summary page after scraping interrupted repeated lookup flow.
- Product direction requested an intrinsic continue-scraping experience on the landing page.

### Decisions

- **Adopt async in-page scrape (`/scrape-summary`) instead of primary redirect UX**
  - Why: removes context-switch friction and keeps users in the same interaction surface.
  - Why: allows immediate incremental updates to session summary without reload.

- **Remove explicit `Add to Cart` CTA from landing-page primary actions**
  - Why: one primary action reduces decision overhead and keeps flow focused on scrape intent.
  - Why: session-level accumulation still supports multi-item workflows without extra queueing step.

- **Use collapsed-by-default `Scrape Summary` with minimal status message**
  - Why: progressive disclosure keeps the form dominant and avoids overwhelming first-time users.
  - Why: users can expand details only when needed while still seeing immediate success/failure feedback.

- **Preserve existing export contracts while moving UX to single page**
  - Why: reusing `/export` and `/export-batch` minimizes backend churn and regression risk.
  - Why: enables in-page downloads without introducing new CSV APIs.

## 2026-06-02 - Multi-verb input on landing form

### Context (Multi-verb input)

- The landing-page scrape input should accept a comma-separated list of verbs (e.g. `sentir, comer, ser`) in addition to single verbs.
- The submit button label was updated as part of the unified UX, and the input/button height needed to visually match on desktop.

### Decisions (Multi-verb input)

- **Parse comma-separated verbs in `InputValidator.parse_verbs`**
  - Why: keeps validation logic centralized and ensures every token is still checked against the existing verb whitelist.
  - Why: enables consistent behavior for both the HTML form POST flow and the in-page `/scrape-summary` endpoint.

- **Generate tasks for every `verb × mode × tense` combination using existing backend batch orchestration**
  - Why: minimizes regression risk by reusing `VerbManager.process_batch` and its dedupe behavior.

- **Update landing-page UI copy + button label**
  - Why: the placeholder and hint communicate multi-verb capability.
  - Why: the primary action text becomes `Scrape`.

- **Align input and submit button height**
  - Why: `fs-3` / `form-control-lg` on the input caused the input to be taller than the button.
  - Why: CSS on `.scrape-verb-row` enforces a matching minimum height.

## 2026-06-02 - Semantic release branch attachment in CI

### Context (Semantic release CI)

- The release workflow is triggered via `workflow_run` and checks out `head_sha` from the completed CI run.
- `python-semantic-release` requires an attached branch to match release configuration; detached HEAD aborts release-group selection.

### Decisions (Semantic release CI)

- **Keep checkout pinned to tested commit SHA, then attach that commit to the triggering branch**
  - Why: preserves release safety by operating on the exact commit validated by CI.
  - Why: satisfies semantic-release branch matching without switching to an unverified branch tip.

- **Add explicit git preflight diagnostics before running semantic-release**
  - Why: makes detached-head vs branch mismatch obvious from logs without guesswork.
  - Why: supports faster root-cause analysis for future release incidents.

- **Run semantic-release with verbose logging**
  - Why: exposes branch/release-group resolution details directly in CI logs.
