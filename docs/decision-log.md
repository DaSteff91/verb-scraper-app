# Decision Log

This file records why specific implementation choices were made, especially where intent is not obvious from the code diff alone.

## 2026-06-02 - Unified single/multi scrape form

### Context

- The UI needed to support both single-verb scraping and multi-verb batch scraping from one unchanged form.
- A bug caused some single-verb runs to show duplicate results.

### Decisions

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
