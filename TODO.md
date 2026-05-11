# TODO
- [ ] Fix supplier auxiliary creation to mirror customer behavior:
  - [ ] Ordinary supplier auxiliary: base ledger **4011**, account_name `Supplier: {name}`
  - [ ] VAT supplier auxiliary: base ledger **44210**, account_name `VAT Supplier: {name}`
  - [ ] Ensure auxiliaries map to `/auxiliary` JOIN (uses `auxiliary.auxiliary_id = Ledger.AccountNumber`).
  - [ ] If supplier already exists, skip auxiliary creation (no duplicates).
- [ ] Critical-path test:
  - [ ] Create supplier via `/suppliers`, verify `/auxiliary` shows both 4011 + 44210 rows with correct ledger_name/account_name.
  - [ ] Re-save same supplier and ensure no duplicate auxiliary rows.
