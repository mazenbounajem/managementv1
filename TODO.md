# TODO - Clean unused pages

## Step 1: Gather used routes/modules
- [x] Verified entry points: `main.py` (imports page routes) and `app.py` (registers many `@ui.page` routes).
- [x] Verified dashboard route: `tabbed_dashboard.py` registers `@ui.page('/tabbed-dashboard')` and uses module content functions via `content_map`.

## Step 2: Identify unused “page” code
- [x] Scanned for NiceGUI routes (`@ui.page('/...')`).
- [x] Confirmed `images/*` python files are NOT imported as `images.*` anywhere in the repo (only `images/*.png` icon paths exist in code).

## Step 3: Deletion plan (safe candidates)
- [x] Delete duplicate/unused UI modules under `images/` (all `images/*.py`), keeping only non-code assets (png/json/etc).
  - Rationale: no `images.*` imports found; runtime uses top-level modules (e.g. `ledgerui.py`, `login_page.py`, etc.) not `images/*` duplicates.

## Step 4: Validate
- [x] Verified `images/` no longer contains any `.py` files (only assets like `.png` plus `__pycache__/`).
- [ ] Start the app and navigate to main pages to confirm no routes break.
- [ ] Fix any import errors if any “images/*.py” were referenced dynamically.
