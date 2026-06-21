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

---

# TODO - Multi-currency (USD + L.L) + stable profit

## Step 1: DB migrations (ALTER TABLE)
- [ ] Add `currency_id`, `fx_rate_used`, and `*_usd` columns to:
  - `sale_items`
  - `purchase_items`
- [ ] Ensure `price_cost_date_history` stores currency context (or migrate to *_usd)
- [ ] Add missing supplier currency balance:
  - `suppliers.balance_ll`

## Step 2: Repository/service refactor (save-time correctness)
- [ ] Update sale posting logic:
  - compute line amounts in transaction currency
  - convert using fx_rate_used captured from `sales.currency_id`
  - store profit in USD fields (stable)
- [ ] Update purchase posting logic (refactor similarly)
- [ ] Update price/cost history insertion so it doesn’t break when exchange rates change

## Step 3: Update UI + product storage
- [ ] Align product pricing inputs to store both currencies (USD + L.L)
- [ ] Align customer/supplier screens to store their currency balances correctly

## Step 4: Profit analytics + reports
- [ ] Refactor `reports.py` / `reports_ui.py` / any profit queries to use `profit_usd` (not recalculated with latest exchange rates)

## Step 5: Verification
- [ ] Create sale in USD for a product with L.L price -> profit_usd matches expectations
- [ ] Create sale in L.L for the same product -> profit_usd matches expectations (no dependency on exchange_rate changes)
- [ ] Run a sale update/edit and ensure history/profit recomputation works

## Step 6: Smoke test
- [ ] Start app and verify currency dropdowns load
- [ ] Navigate to sales, purchases, and profit analysis pages without errors
