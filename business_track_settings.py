"""
Centralized helper module for Business Track account mappings.

Reads the saved mapping from business_track_settings.json and exposes
helper functions that return the correct ledger account based on VAT status.

Mapping grid layout (12 rows × 2 columns per tab):
  Row 0 = Local Sales/Purchase Value       → col 0 = VAT, col 1 = Non-VAT
  Row 4 = Return Value                     → col 0 = VAT, col 1 = Non-VAT
  Row 8 = Export/Import Value              → col 0 = VAT, col 1 = Non-VAT
"""

import json
import os

SETTINGS_FILE = 'business_track_settings.json'

# Defaults used when no mapping is configured
_DEFAULT_SALES_ACCOUNT = '7011.000001'
_DEFAULT_PURCHASE_ACCOUNT = '6011.000001'


def _load_mapping():
    """Load the mapping dict from the JSON settings file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _get_account(tab, row, col, default):
    """
    Retrieve a specific account from the mapping grid.
    tab: 'sales' or 'purchase'
    row: grid row index (0-11)
    col: 0 = VAT column, 1 = Non-VAT column
    """
    mapping = _load_mapping()
    if mapping and tab in mapping:
        try:
            value = mapping[tab][row][col]
            if value:
                return value
        except (IndexError, KeyError):
            pass
    return default


# ── Sales ────────────────────────────────────────────────────────────────────

def get_sales_account(has_vat: bool) -> str:
    """Return the revenue account for a sale (VAT vs Non-VAT)."""
    col = 0 if has_vat else 1
    return _get_account('sales', 0, col, _DEFAULT_SALES_ACCOUNT)


def get_sales_return_account(has_vat: bool) -> str:
    """Return the revenue account for a sales return (VAT vs Non-VAT)."""
    col = 0 if has_vat else 1
    return _get_account('sales', 4, col, _DEFAULT_SALES_ACCOUNT)


# ── Purchases ────────────────────────────────────────────────────────────────

def get_purchase_account(has_vat: bool) -> str:
    """Return the expense account for a purchase (VAT vs Non-VAT)."""
    col = 0 if has_vat else 1
    return _get_account('purchase', 0, col, _DEFAULT_PURCHASE_ACCOUNT)


def get_purchase_return_account(has_vat: bool) -> str:
    """Return the expense account for a purchase return (VAT vs Non-VAT)."""
    col = 0 if has_vat else 1
    return _get_account('purchase', 4, col, _DEFAULT_PURCHASE_ACCOUNT)
