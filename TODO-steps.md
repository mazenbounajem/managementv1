# Hierarchical Trial Balance Implementation TODO

Status: **IN PROGRESS** 0/14 (main TODO.md at 0/12, +validation)

## Approved Plan Steps (from Phase 1 → 5)

### Phase 1: Data Layer (reports.py)
- [x] **1.1** Create `fetch_hierarchical_trial_balance(ledger_prefix, from_date=None, to_date=None)` in reports.py
  - Recursive CTE for Ledger tree under prefix
  - Aggregate debit/credit from lines/auxiliary
  - Build nested dict structure with children/transactions
- [x] **1.2** Test function (e.g., prefix='701')

### Phase 2: PDF Generation (accounting_helpers.py)
- [x] **2** Implement `print_hierarchical_trial_balance_pdf(prefix, from_date, to_date)`

- [ ] **3-6** ReportLab: Header, hierarchical indented table, leaf details, totals/balance check

### Phase 3: Modern UI (reports_ui.py / modern_reports_ui.py)
- [ ] **7** Add `'hierarchical_trial_balance'` to report select options
- [ ] **8** Ledger prefix input + autocomplete (Ledger.AccountNumber)
- [ ] **9** aggrid treeData display
- [ ] **10** Print PDF button (iframe dialog)

### Phase 4: Quick Access Buttons
- [x] **11** ledgerui.py: Button on row → `print_hierarchical_trial_balance_pdf(row.AccountNumber)`
- [x] **12** auxiliaryui.py: Button → prefix from row.number

### Phase 5: Validation
- [ ] **13** Test: prefix="701" → hierarchy + PDF
- [ ] **14** All complete → update TODO.md → attempt_completion

**Next Step: 1.1 - Implement fetch function in reports.py**

