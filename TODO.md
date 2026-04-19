# Hierarchical Trial Balance Implementation (Like Statement of Account)

Status: **IN PROGRESS** 0/12

## Phase 1: Data Layer (reports.py)
- [ ] 1. Implement `fetch_hierarchical_trial_balance(ledger_prefix, from_date, to_date)`
  - Recursive CTE: Ledger tree under prefix (AccountNumber LIKE prefix + '%')
  - Join auxiliary WHERE number LIKE level_code + '.%'
  - Window SUM(debit/credit) OVER (PARTITION BY account_tree ORDER BY txn_date)
  - Nested structure: [{'code': '701', 'name': 'Sales', 'debit': 10000, 'credit': 9000, 'balance': 1000, 'level': 1, 'children': [...], 'transactions': []}]

## Phase 2: PDF Generation (accounting_helpers.py)
- [ ] 2. `print_hierarchical_trial_balance_pdf(prefix, from_date, to_date)`
- [ ] 3. ReportLab: Header w/ period/prefix
- [ ] 4. Hierarchical table (indented code/name, totals)
- [ ] 5. Expandable detail sections for leaves (Date/Ref/Debit/Credit/Balance)
- [ ] 6. Grand totals + balance check

## Phase 3: Modern UI (modern_reports_ui.py)
- [ ] 7. Add `'hierarchical_trial_balance'` to select options
- [ ] 8. Ledger prefix input + autocomplete from Ledger.AccountNumber
- [ ] 9. aggrid treeData display
- [ ] 10. Print PDF button (iframe dialog like current)

## Phase 4: Quick Access Buttons
- [ ] 11. ledgerui.py: Button on row select → print_hierarchical_trial_balance_pdf(row.AccountNumber)
- [ ] 12. auxiliaryui.py: Similar button

## Phase 5: Validation
- [ ] 13. Test: prefix="701", dates → full hierarchy + leaf details + PDF
- [ ] 14. ✅ All steps → attempt_completion

**Next Step: Phase 1.1 - Add fetch function to reports.py**

