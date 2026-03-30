# Supplier Payment Fixes TODO

## Status: In Progress

### Step 1: [x] Create calculate_supplier_pending() in supplier_payment_ui_fixed_v2.py
- Sum unpaid purchase invoices per supplier
- Replace fetch_supplier_balance() to use this

### Step 2: [x] Add UI labels/tooltips for two tables in dialog
- Explain invoice_grid vs preview_grid

### Step 3: [x] Add refresh logic after process_payment()
- Reload supplier balance
- Refresh history table
- Notify external refresh (supplierui)

### Step 4: [x] Update supplierui.py
- Add refresh mechanism linked to payments

### Step 5: [x] Test full flow
✅ All fixes implemented:
- Dialog tables now clearly labeled (Selection + Preview)
- Amount persists and form refreshes after payment
- Balance matches actual pending invoice sum from purchases
- Supplier UI shows 'Pending Invoices' column, updates on refresh

### Step 6: [x] Fix payment register row selection
✅ Fill Disbursement Details completely with current balance when clicking history row

