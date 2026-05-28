from connection import connection


def get_next_auxiliary(account_base):
    """
    Generates the next sequential auxiliary number for a given base ledger code.

    Expected stored formats in auxiliary.number:
      - "base.suffix" (recommended, e.g. "4011.000001")
      - Sometimes "base.<int>" (e.g. "4011.1")

    Always returns: "{account_base}.{next_seq}" (suffix increment only).
    """
    try:
        data = []

        # Scope strictly to the requested base so we only increment within that base.
        sql = """
            SELECT number
            FROM auxiliary
            WHERE number LIKE ?
        """
        base_prefix = f"{str(account_base).strip()}."
        connection.contogetrows_with_params(sql, data, (base_prefix + '%',))

        max_seq = 0
        base_str = str(account_base).strip()

        for (num,) in data:
            if num is None:
                continue
            s = str(num).strip()

            # Only accept base.suffix rows for this base
            if '.' not in s:
                continue
            b, suffix = s.split('.', 1)
            if str(b).strip() != base_str:
                continue

            suffix = str(suffix).strip()
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

        next_seq = max_seq + 1
        return f"{base_str}.{next_seq:06d}"
    except Exception as e:
        print(f"Error generating auxiliary for {account_base}: {e}")
        import time
        return f"{account_base}.{int(time.time() * 1000) % 1000000:06d}"


def register_auxiliary(auxiliary_number, account_name):
    """Registers the generated auxiliary in the database."""
    try:
        base_ledger = str(auxiliary_number).split('.')[0] if '.' in str(auxiliary_number) else str(auxiliary_number)

        # UI `auxiliaryui.py` joins using:
        #   LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
        # So `auxiliary.auxiliary_id` must contain the ledger AccountNumber (e.g. "4111").
        sql = """
            INSERT INTO auxiliary (auxiliary_id, account_name, number, update_date, status)
            VALUES (?, ?, ?, GETDATE(), 1)
        """
        connection.insertingtodatabase(sql, (base_ledger, account_name, auxiliary_number))
        return True
    except Exception as e:
        print(f"Error registering auxiliary {auxiliary_number}: {e}")
        return False


def ensure_vat_auxiliary(reference_type, entity_id, entity_name, auxiliary_number):
    """
    Ensures a specific VAT auxiliary account exists for a supplier or customer.

    reference_type: 'Supplier' or 'Customer'
    entity_id: ID in the respective table
    entity_name: Name of supplier/customer
    auxiliary_number: The main auxiliary number (e.g. 4111.000001 or 4011.000001)

    Behavior:
    - For customers:
        - ordinary aux: 4111.<suffix> => "Customer: <name>"
        - vat aux on sales: 44270.<suffix> => "VAT Customer: <name>"
    - For suppliers:
        - ordinary aux: 4011.<suffix> => "Supplier: <name>" (fallback)
        - vat aux: 44210.<suffix> => "VAT Supplier: <name>"
    """
    try:
        if reference_type == 'Supplier':
            base_ledger = '44210'
            account_name_prefix = "VAT Supplier"
        else:
            base_ledger = '44270'
            account_name_prefix = "VAT Customer"

        # IMPORTANT: always keep the same suffix sequence as the ordinary auxiliary
        # e.g. auxiliary_number=1 => vat number=1
        suffix = str(auxiliary_number).split('.')[-1] if '.' in str(auxiliary_number) else str(auxiliary_number)
        vat_acct = f"{base_ledger}.{suffix}"

        # Check if exists
        exists = []
        connection.contogetrows("SELECT id FROM auxiliary WHERE number = ?", exists, params=[vat_acct])
        if not exists:
            # Get Ledger ID
            ledger_data = []
            connection.contogetrows("SELECT Id FROM Ledger WHERE AccountNumber = ?", ledger_data, params=[base_ledger])
            if not ledger_data:
                print(f"ERROR: Ledger {base_ledger} not found")
                return vat_acct

            ledger_id = ledger_data[0][0]
            # UI `auxiliaryui.py` joins using: LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
            # So we must write the ledger AccountNumber into auxiliary.auxiliary_id (not ledger_id).
            connection.insertingtodatabase(
                "INSERT INTO auxiliary (auxiliary_id, number, account_name, status) VALUES (?, ?, ?, 1)",
                (base_ledger, vat_acct, f"{account_name_prefix}: {entity_name}")
            )
        return vat_acct
    except Exception as e:
        print(f"Error ensuring VAT auxiliary: {e}")
        return f"{base_ledger}.000001" if 'base_ledger' in locals() else "44210.000001"


def _try_update_auxiliary_number(table_name, entity_id, auxiliary_number):
    """
    Attempts to persist auxiliary_number into the given entity table.
    If the column doesn't exist in DB schema yet, silently ignore.
    """
    try:
        connection.insertingtodatabase(
            f"UPDATE {table_name} SET auxiliary_number = ? WHERE id = ?",
            (auxiliary_number, entity_id)
        )
        return True
    except Exception:
        return False


def ensure_customer_auxiliary(customer_id, customer_name=None, fallback_account_number='4111'):
    """
    Ensures customers.auxiliary_number exists and that the auxiliary row exists.
    Returns auxiliary_number string like '4111.000001'.
    """
    try:
        res = []
        connection.contogetrows(
            "SELECT auxiliary_number, customer_name FROM customers WHERE id = ?",
            res, params=[customer_id]
        )
        existing_aux = res[0][0] if res and res[0] else None
        name = customer_name or (res[0][1] if res and res[0] and res[0][1] else None) or f"Customer {customer_id}"

        if existing_aux and str(existing_aux).strip():
            return str(existing_aux).strip()

        new_aux = get_next_auxiliary(fallback_account_number)

        # Ensure auxiliary exists in auxiliary table
        exists = []
        connection.contogetrows("SELECT id FROM auxiliary WHERE number = ?", exists, params=[new_aux])
        if not exists:
            # Find ledger
            ledger_data = []
            connection.contogetrows(
                "SELECT Id FROM Ledger WHERE AccountNumber = ?",
                ledger_data, params=[fallback_account_number]
            )
            if ledger_data and ledger_data[0][0]:
                ledger_id = ledger_data[0][0]
                # UI `auxiliaryui.py` joins using: LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
                # So we must write the ledger AccountNumber into auxiliary.auxiliary_id (not ledger_id).
                connection.insertingtodatabase(
                    "INSERT INTO auxiliary (auxiliary_id, number, account_name, status) VALUES (?, ?, ?, 1)",
                    (fallback_account_number, new_aux, f"Customer: {name}")
                )
            else:
                # If ledger not found, still return the computed aux; accounting may fail later
                return new_aux

        _try_update_auxiliary_number('customers', customer_id, new_aux)
        return new_aux
    except Exception as e:
        print(f"Error ensuring customer auxiliary: {e}")
        return get_next_auxiliary(fallback_account_number)


def ensure_supplier_auxiliary(supplier_id, supplier_name=None, fallback_account_number='4011'):
    """
    Ensures suppliers.auxiliary_number exists and that the auxiliary row exists.
    Returns auxiliary_number string like '4011.000001'.

    Notes:
    - `/auxiliary` UI joins using: LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
      So we must insert base ledger AccountNumber into auxiliary.auxiliary_id (not ledger_id).
    """
    try:
        res = []
        connection.contogetrows(
            "SELECT auxiliary_number, name FROM suppliers WHERE id = ?",
            res, params=[supplier_id]
        )
        existing_aux = res[0][0] if res and res[0] else None
        name = supplier_name or (res[0][1] if res and res[0] and res[0][1] else None) or f"Supplier {supplier_id}"

        # If supplier already has auxiliary_number, keep it and do not create new auxiliaries.
        if existing_aux and str(existing_aux).strip():
            return str(existing_aux).strip()

        new_aux = get_next_auxiliary(fallback_account_number)

        # Only create the auxiliary row if it's missing.
        exists = []
        connection.contogetrows(
            "SELECT id FROM auxiliary WHERE number = ?",
            exists, params=[new_aux]
        )
        if not exists:
            # Ensure ledger exists (for referential integrity / mapping correctness)
            ledger_data = []
            connection.contogetrows(
                "SELECT Id FROM Ledger WHERE AccountNumber = ?",
                ledger_data, params=[fallback_account_number]
            )
            if not ledger_data:
                return new_aux

            connection.insertingtodatabase(
                "INSERT INTO auxiliary (auxiliary_id, number, account_name, status) VALUES (?, ?, ?, 1)",
                (fallback_account_number, new_aux, f"Supplier: {name}")
            )

        _try_update_auxiliary_number('suppliers', supplier_id, new_aux)
        return new_aux
    except Exception as e:
        print(f"Error ensuring supplier auxiliary: {e}")
        return get_next_auxiliary(fallback_account_number)


def _normalize_lines(lines):
    """
    Normalize accounting lines to list-of-dicts format.

    Accepted formats:
      1. List of dicts:
         - {'account': '4111.000001', 'debit': 100, 'credit': 0}
         - optionally {'auxiliary_id': <int>} to force auxiliary id
      2. Old tuple format from salesui: [(aux, acct, debit, credit, desc), ...]
         where aux may be None and acct may be None (only one is set).
    """
    normalized = []
    for line in lines:
        if isinstance(line, dict):
            normalized.append(line)
        elif isinstance(line, (list, tuple)):
            # (aux_number, account_number, debit, credit, remark)
            aux_num  = line[0] if len(line) > 0 else None
            acct_num = line[1] if len(line) > 1 else None
            debit    = float(line[2]) if len(line) > 2 and line[2] is not None else 0.0
            credit   = float(line[3]) if len(line) > 3 and line[3] is not None else 0.0
            # Use aux_number if provided, otherwise the plain account number
            account  = aux_num if aux_num else (acct_num if acct_num else '')
            normalized.append({'account': account, 'debit': debit, 'credit': credit})
        else:
            print(f"Unknown line format, skipping: {line}")
    return normalized


def _resolve_auxiliary_id(auxiliary_number_or_id):
    """
    Resolve a provided auxiliary number (e.g. '4111.000001') into auxiliary.id (INT).

    If the input is already an int-like value, return it as-is.
    If not found / not resolvable, return None.
    """
    if auxiliary_number_or_id is None:
        return None

    # If already an int (or int-like string), treat as id
    if isinstance(auxiliary_number_or_id, int):
        return auxiliary_number_or_id

    s = str(auxiliary_number_or_id).strip()
    if not s:
        return None

    # If looks like an integer id, accept it
    try:
        if s.isdigit():
            return int(s)
    except Exception:
        pass

    # Otherwise assume it's an auxiliary "number" like '4111.000001'
    try:
        res = []
        connection.contogetrows("SELECT id FROM auxiliary WHERE number = ?", res, params=[s])
        if res and res[0][0]:
            return res[0][0]
    except Exception:
        pass

    return None


def save_accounting_transaction(reference_type, reference_id, lines, description=None, notes=None):
    """
    Saves a double-entry journal voucher.

    Args:
        reference_type: e.g. "Sale", "Purchase", "Receipt", "Payment"
        reference_id:   invoice number or DB id
        lines:          list of dicts OR list of tuples (see _normalize_lines)
        description:    optional text description of the transaction
        notes:          ignored (kept for backward compatibility)
    """
    try:
        lines = _normalize_lines(lines)

        total_debit  = sum(float(l.get('debit',  0)) for l in lines)
        total_credit = sum(float(l.get('credit', 0)) for l in lines)

        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(
                f"Accounting mismatch: Debits ({total_debit:.2f}) != Credits ({total_credit:.2f})"
            )

        desc_text = description or f"{reference_type} {reference_id}"

        # Clean up existing transactions for this reference to prevent duplicates on update
        if reference_type and reference_id:
            existing_jvs = []
            connection.contogetrows(
                "SELECT jv_id FROM accounting_transactions WHERE reference_type = ? AND reference_id = ?",
                existing_jvs,
                (str(reference_type), str(reference_id))
            )
            for jv in existing_jvs:
                jv_to_del = jv[0]
                connection.deleterow("DELETE FROM accounting_transaction_lines WHERE jv_id = ?", (jv_to_del,))
                connection.deleterow("DELETE FROM accounting_transactions WHERE jv_id = ?", (jv_to_del,))

        header_sql = """
        INSERT INTO accounting_transactions (reference_type, reference_id, description, transaction_date)
        VALUES (?, ?, ?, GETDATE());
        """
        connection.insertingtodatabase(header_sql, (str(reference_type), str(reference_id), desc_text))

        data_id = []
        connection.contogetrows("SELECT MAX(jv_id) FROM accounting_transactions", data_id)

        if not data_id or not data_id[0][0]:
            raise Exception("Failed to retrieve new JV ID")

        jv_id = data_id[0][0]

        for line in lines:
            line_sql = """
            INSERT INTO accounting_transaction_lines (jv_id, account_number, auxiliary_id, debit, credit)
            VALUES (?, ?, ?, ?, ?)
            """
            aux_ref  = line.get('account', '')
            aux_ref_str = '' if aux_ref is None else str(aux_ref).strip()

            base_acct = aux_ref_str.split('.')[0] if '.' in aux_ref_str else aux_ref_str

            # Allow explicit override: some callers want auxiliary_id from auxiliary table directly
            # (e.g. cash caisse selection should use auxiliary.id, not a hardcoded suffix).
            explicit_aux_id = line.get('auxiliary_id', None)
            if explicit_aux_id is not None:
                resolved_aux_id = int(explicit_aux_id)
            else:
                # Convert auxiliary number -> auxiliary.id (INT) if possible
                resolved_aux_id = _resolve_auxiliary_id(aux_ref_str)

            connection.insertingtodatabase(line_sql, (
                jv_id,
                base_acct,
                resolved_aux_id,
                float(line.get('debit',  0)),
                float(line.get('credit', 0))
            ))

        return jv_id

    except Exception as e:
        print(f"Error saving accounting transaction: {e}")
        raise e


def show_transactions_dialog(
    reference_type=None,
    reference_id=None,
    account_number=None,
    from_date=None,
    to_date=None,
    include_jv_journal_voucher_lines: bool = False,
):
    """
    Opens a dialog showing accounting transactions for a given reference or account,
    including Date, Reference, Account, Remark, Debit, Credit, and Running Balance.
    """
    from nicegui import ui

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-5xl p-6'):
        ui.label('Accounting Transactions Ledger').classes('text-xl font-bold mb-4')

        data = []
        sql = """
        SELECT
               t.jv_id,
               t.transaction_date,
               t.reference_type,
               t.reference_id,
               l.account_number,
               l.auxiliary_id,
               aux.number as auxiliary_number,
               aux.account_name as auxiliary_name,
               l.debit,
               l.credit,
               t.description,
               ldr.Name_en as ledger_name
        FROM accounting_transactions t
        INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        LEFT JOIN auxiliary aux ON l.auxiliary_id = aux.id
        LEFT JOIN Ledger ldr ON l.account_number = ldr.AccountNumber
        WHERE 1=1
        """
        params = []
        if reference_type and reference_id:
            # Show only the primary JV for this reference.
            # NOTE: do NOT include linked 'Sale Receipt' / 'Purchase Payment' JVs here —
            # the primary Sale/Purchase JV already contains the cash (5300) debit line.
            # Including the receipt/payment JV as well doubles the cash amount in totals.
            sql += " AND t.reference_type = ? AND t.reference_id = ?"
            params.extend([reference_type, str(reference_id)])
        elif account_number:
            # Filter by either:
            # - exact auxiliary/ledger account number match
            # - or prefix match when caller passes base like '5300' (treat as '5300.%')
            acc_str = str(account_number).strip()

            # If account_number looks like a full auxiliary number (e.g. 5314.000001),
            # resolve it to auxiliary.id (INT) to safely compare with l.auxiliary_id.
            resolved_aux_id = _resolve_auxiliary_id(account_number) if '.' in acc_str else None

            if '.' not in acc_str:
                # Caller likely passed a suffix only (e.g. '000001').
                # Then match any full account that ends with '.<suffix>'.
                suffix = acc_str
                sql += """
                    AND (
                        aux.number = ?
                        OR l.account_number = ?
                        OR l.account_number LIKE '%.' + ? -- any base.<suffix>
                    )
                """
                params.extend([suffix, suffix, suffix])
            else:
                # Full auxiliary number case
                base = acc_str.split('.')[0]
                if resolved_aux_id is not None:
                    # Tight match: for a resolved full auxiliary view, filter strictly by auxiliary_id.
                    # This guarantees that totals reconcile for the exact auxiliary subset.
                    sql += """
                        AND (
                            l.auxiliary_id = ?
                        )
                    """
                    params.extend([
                        resolved_aux_id,
                    ])
                else:
                    # Fallback when aux.number can't be resolved to aux.id
                    sql += """
                        AND (
                            aux.number = ?
                            OR l.account_number = ?
                            OR aux.number LIKE ? + '.%' -- base like '5300'
                            OR l.account_number LIKE ? + '.%'
                        )
                    """
                    params.extend([
                        acc_str,
                        acc_str,
                        base,
                        base,
                    ])

        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)

        sql += " ORDER BY t.jv_id ASC, l.account_number ASC"

        connection.contogetrows_with_params(sql, data, tuple(params))

        # Optional: also include Journal Voucher lines stored in journal_voucher/journal_voucher_items
        # (used by auxiliaryui view). Default is OFF to avoid duplicates in ledgerui.
        jv_data = []
        if include_jv_journal_voucher_lines and account_number:
            acc_str = str(account_number).strip()
            resolved_aux_id = _resolve_auxiliary_id(account_number) if '.' in acc_str else None

            jv_sql = """
                SELECT
                    v.NumberId as jv_id,
                    v.[Date] as transaction_date,
                    v.SubTypeId,
                    v.Entry as reference_type,
                    v.ManualReference as reference_id,
                    l.AccountNumber as account_number,
                    i.AuxiliaryId as auxiliary_id,
                    a.number as auxiliary_number,
                    a.account_name as auxiliary_name,
                    i.Debit as debit,
                    i.Credit as credit,
                    i.Remark as remark,
                    l.Name_en as ledger_name
                FROM journal_voucher v
                INNER JOIN journal_voucher_items i ON v.NumberId = i.VoucherId
                LEFT JOIN auxiliary a ON a.id = i.AuxiliaryId
                LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
                WHERE 1=1
            """
            jv_params = []
            if '.' not in acc_str:
                # suffix-only: match any auxiliary.number ending with '.<suffix>'
                suffix = acc_str
                jv_sql += " AND a.number LIKE '%.' + ?"
                jv_params.append(suffix)
            else:
                # full auxiliary number: strict match by auxiliary.number (preferred)
                jv_sql += " AND a.number = ?"
                jv_params.append(acc_str)
                if resolved_aux_id is not None:
                    # additionally allow strict auxiliary_id match if available
                    jv_sql = jv_sql.replace("WHERE 1=1", "WHERE 1=1 AND (i.AuxiliaryId = ? OR a.number = ?)", 1)
                    jv_params = [resolved_aux_id, acc_str]

            if from_date:
                jv_sql += " AND CAST(v.[Date] AS DATE) >= ?"
                jv_params.append(from_date)
            if to_date:
                jv_sql += " AND CAST(v.[Date] AS DATE) <= ?"
                jv_params.append(to_date)

            jv_sql += " ORDER BY v.NumberId ASC, l.AccountNumber ASC, i.Id ASC"
            connection.contogetrows_with_params(jv_sql, jv_data, tuple(jv_params))

        rows = []
        total_debit  = 0.0
        total_credit = 0.0
        running_balance = 0.0

        # Combine primary accounting data and optional JV data.
        # We normalize both to the same index layout used below.
        combined = []
        combined.extend(data)
        combined.extend(jv_data)

        # Note: combined rows should follow the SELECT column order:
        # accounting_transactions query: debit at [8], credit at [9], aux.number at [6], aux.name at [7], desc at [10], ledger_name at [11].
        # JV query above returns:
        # [0]=jv_id, [1]=date, [4]=reference_id, [5]=account_number, [6]=auxiliary_id, [7]=aux.number, [8]=aux.name, [9]=debit, [10]=credit, [11]=remark, [12]=ledger_name
        # To reuse existing rendering logic, we map JV row to an equivalent tuple.
        normalized = []
        normalized.extend(combined)

        if jv_data:
            # Append normalized JV tuples matching the accounting query shape:
            # [0]=jv_id, [1]=date, [2]=reference_type, [3]=reference_id, [4]=account_number, [5]=auxiliary_id,
            # [6]=aux.number, [7]=aux.account_name, [8]=debit, [9]=credit, [10]=description, [11]=ledger_name
            for jr in jv_data:
                normalized.append((
                    jr[0], jr[1], jr[3], jr[4], jr[5], jr[6],
                    jr[7], jr[8], jr[9], jr[10], jr[11], jr[12]
                ))

        for r in normalized:
            debit  = float(r[8] or 0)
            credit = float(r[9] or 0)
            total_debit  += debit
            total_credit += credit
            running_balance += debit - credit

            # Column mapping:
            # r[6]  = aux.number        (e.g. "5300.000001" or suffix-only "000001")
            # r[7]  = aux.account_name  (e.g. "Caisse Cash LBP", may be NULL)
            # r[10] = t.description
            # r[11] = ldr.Name_en       (Ledger name for the base account, e.g. "Caisse" for 5300)
            aux_number = r[6]
            aux_name   = r[7]
            ledger_name = r[11]

            base_account = str(r[4] or '').strip()
            aux_number_str = ''
            if aux_number is not None and str(aux_number).strip():
                aux_number_str = str(aux_number).strip()
                # If aux.number is suffix-only (no dot), prefix it with the base ledger code
                if '.' not in aux_number_str and base_account:
                    aux_number_str = f"{base_account}.{aux_number_str}"

            # Resolve the best display name:
            # Priority: aux.account_name -> Ledger.Name_en -> bare account number
            display_name = ''
            if aux_name and str(aux_name).strip():
                display_name = str(aux_name).strip()
            elif ledger_name and str(ledger_name).strip():
                display_name = str(ledger_name).strip()

            # Format: "Name (auxiliary_number)" or just "Name" / "number"
            if display_name:
                if aux_number_str:
                    account_display = f"{display_name} ({aux_number_str})"
                elif base_account:
                    account_display = f"{display_name} ({base_account})"
                else:
                    account_display = display_name
            else:
                account_display = aux_number_str or base_account or ''

            remark = str(r[10] or '')
            rows.append({
                'jv_id':   r[0],
                'date':    str(r[1]).split(' ')[0] if r[1] else '',
                'ref':     f"{r[2]} #{r[3]}",
                'account': str(account_display),
                'remark':  remark,
                'debit':   f"{debit:,.2f}"  if debit  else '',
                'credit':  f"{credit:,.2f}" if credit else '',
                'balance': f"{running_balance:,.2f}",
            })

        if not rows:
            ui.label('No accounting transactions found for this record.').classes('text-gray-500 italic')
        else:
            ui.table(
                columns=[
                    {'name': 'jv_id',   'label': 'JV',      'field': 'jv_id',   'align': 'left', 'sortable': True},
                    {'name': 'date',    'label': 'Date',     'field': 'date',    'align': 'left'},
                    {'name': 'ref',     'label': 'Reference','field': 'ref',     'align': 'left'},
                    {'name': 'account', 'label': 'Account',  'field': 'account', 'align': 'left'},
                    {'name': 'remark',  'label': 'Remark',   'field': 'remark',  'align': 'left'},
                    {'name': 'debit',   'label': 'Debit',    'field': 'debit',   'align': 'right'},
                    {'name': 'credit',  'label': 'Credit',   'field': 'credit',  'align': 'right'},
                    {'name': 'balance', 'label': 'Balance',  'field': 'balance', 'align': 'right'},
                ],
                rows=rows,
                pagination=20
            ).classes('w-full mb-4')

            with ui.row().classes('w-full justify-end font-bold items-center gap-4 bg-gray-100 dark:bg-gray-800 p-2 rounded'):
                ui.label(f'Total Debit: {total_debit:,.2f}').style('color: var(--q-positive);')
                ui.label(f'Total Credit: {total_credit:,.2f}').style('color: var(--q-negative);')
                balance_label = f'Balance: {(total_debit - total_credit):,.2f}'
                ui.label(balance_label)
                if abs(total_debit - total_credit) < 0.01:
                    ui.icon('check_circle', color='positive').tooltip('Balanced')
                else:
                    ui.icon('error', color='negative').tooltip('Unbalanced')

        # Extra: allocation breakdown for document settlements (Sales Return / Purchase Return)
        # This is what you need to see: which Receipt/Payment IDs were applied and with which values.
        try:
            if reference_type == "Sale Return" and reference_id is not None:
                allocations = []
                sql = """
                    SELECT
                        crd.payment_id,
                        cr.payment_date,
                        cr.payment_method,
                        cr.amount,
                        COALESCE(crd.settlement_amount_display, crd.settlement_amount)
                    FROM customer_receipt_details crd
                    JOIN customer_receipt cr ON cr.id = crd.payment_id
                    WHERE crd.source_type = 'Return' AND crd.source_id = ?
                    ORDER BY cr.payment_date ASC, crd.payment_id ASC
                """
                connection.contogetrows_with_params(sql, allocations, (int(reference_id),))

                if allocations:
                    ui.label('--- Allocation Breakdown (Customer Receipts -> This Sale Return) ---').classes('text-lg font-bold mt-6 mb-2')
                    ui.table(
                        columns=[
                            {'name': 'payment_id', 'label': 'Receipt ID', 'field': 'payment_id', 'align': 'left'},
                            {'name': 'payment_date', 'label': 'Date', 'field': 'payment_date', 'align': 'left'},
                            {'name': 'payment_method', 'label': 'Method', 'field': 'payment_method', 'align': 'left'},
                            {'name': 'amount', 'label': 'Receipt Amount', 'field': 'amount', 'align': 'right'},
                            {'name': 'settlement_amount', 'label': 'Applied Settlement', 'field': 'settlement_amount', 'align': 'right'},
                        ],
                        rows=[
                            {
                                'payment_id': r[0],
                                'payment_date': str(r[1]).split(' ')[0] if r[1] else '',
                                'payment_method': r[2],
                                'amount': f"{float(r[3]):,.2f}",
                                'settlement_amount': f"{float(r[4]):,.2f}",
                            }
                            for r in allocations
                        ],
                        pagination=20,
                    ).classes('w-full mb-4')
            elif reference_type == "Purchase Return" and reference_id is not None:
                allocations = []
                sql = """
                    SELECT
                        spd.payment_id,
                        sp.payment_date,
                        sp.payment_method,
                        sp.amount,
                        spd.settlement_amount
                    FROM supplier_payment_details spd
                    JOIN supplier_payment sp ON sp.id = spd.payment_id
                    WHERE spd.source_type = 'Return' AND spd.source_id = ?
                    ORDER BY sp.payment_date ASC, spd.payment_id ASC
                """
                connection.contogetrows_with_params(sql, allocations, (int(reference_id),))

                if allocations:
                    ui.label('--- Allocation Breakdown (Supplier Payments -> This Purchase Return) ---').classes('text-lg font-bold mt-6 mb-2')
                    ui.table(
                        columns=[
                            {'name': 'payment_id', 'label': 'Payment ID', 'field': 'payment_id', 'align': 'left'},
                            {'name': 'payment_date', 'label': 'Date', 'field': 'payment_date', 'align': 'left'},
                            {'name': 'payment_method', 'label': 'Method', 'field': 'payment_method', 'align': 'left'},
                            {'name': 'amount', 'label': 'Payment Amount', 'field': 'amount', 'align': 'right'},
                            {'name': 'settlement_amount', 'label': 'Applied Settlement', 'field': 'settlement_amount', 'align': 'right'},
                        ],
                        rows=[
                            {
                                'payment_id': r[0],
                                'payment_date': str(r[1]).split(' ')[0] if r[1] else '',
                                'payment_method': r[2],
                                'amount': f"{float(r[3]):,.2f}",
                                'settlement_amount': f"{float(r[4]):,.2f}",
                            }
                            for r in allocations
                        ],
                        pagination=20,
                    ).classes('w-full mb-4')
        except Exception as e:
            ui.notify(f'Allocation breakdown load error: {e}', color='warning')

        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Close', on_click=dialog.close).props('flat')

    dialog.open()


def print_account_statement(account_number, from_date=None, to_date=None):
    """
    Generate and display a PDF statement of account for the given auxiliary/account number.
    Shows: Date, Remark, Debit, Credit, Running Balance plus totals.
    """
    from nicegui import ui
    try:
        import base64
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO

        data = []

        # Avoid SQL Server nvarchar->int conversion errors:
        # l.auxiliary_id is INT, so if caller passes an auxiliary number like '4111.000001'
        # we should resolve it to auxiliary.id first before binding to auxiliary_id.
        resolved_aux_id = None
        if account_number is not None:
            resolved_aux_id = _resolve_auxiliary_id(account_number)

        # Build statement query safely depending on whether we could resolve aux.id (INT)
        if resolved_aux_id is not None:
            sql = """
            SELECT t.transaction_date, t.reference_type, t.reference_id, t.description,
                   l.debit, l.credit
            FROM accounting_transactions t
            INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            WHERE (l.auxiliary_id = ? OR l.account_number = ?)
            """
            params = [resolved_aux_id, account_number]
        else:
            sql = """
            SELECT t.transaction_date, t.reference_type, t.reference_id, t.description,
                   l.debit, l.credit
            FROM accounting_transactions t
            INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            WHERE (l.account_number = ?)
            """
            params = [account_number]

        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)

        sql += " ORDER BY t.jv_id ASC"
        connection.contogetrows_with_params(sql, data, tuple(params))

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=40, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"Statement of Account: {account_number}", styles['Heading1']))
        if from_date or to_date:
            period = f"Period: {from_date or 'Beginning'} — {to_date or 'Today'}"
            elements.append(Paragraph(period, styles['Normal']))
        elements.append(Spacer(1, 12))

        table_data = [['Date', 'Remark', 'Debit', 'Credit', 'Balance']]
        total_debit  = 0.0
        total_credit = 0.0
        running_bal  = 0.0

        for r in data:
            date_str = str(r[0]).split(' ')[0] if r[0] else ''
            remark   = str(r[3] or f"{r[1]} #{r[2]}")
            debit    = float(r[4] or 0)
            credit   = float(r[5] or 0)
            total_debit  += debit
            total_credit += credit
            running_bal  += debit - credit

            table_data.append([
                date_str,
                remark,
                f"{debit:,.2f}"   if debit  else '-',
                f"{credit:,.2f}"  if credit else '-',
                f"{running_bal:,.2f}",
            ])

        # Totals row
        table_data.append([
            'TOTAL', '',
            f"{total_debit:,.2f}",
            f"{total_credit:,.2f}",
            f"{(total_debit - total_credit):,.2f}",
        ])

        available_width = A4[0] - 60
        col_widths = [
            available_width * 0.12,
            available_width * 0.40,
            available_width * 0.16,
            available_width * 0.16,
            available_width * 0.16,
        ]

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND',  (0, 0), (-1, 0),  colors.HexColor('#3b3b6b')),
            ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.white),
            ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, 0),  9),
            ('ALIGN',       (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN',       (0, 0), (1, -1),  'LEFT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f8')]),
            ('BACKGROUND',  (0, -1), (-1, -1), colors.HexColor('#d0d0e8')),
            ('FONTNAME',    (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID',        (0, 0), (-1, -1),  0.5, colors.grey),
            ('FONTSIZE',    (0, 1), (-1, -1),  8),
            ('TOPPADDING',  (0, 0), (-1, -1),  4),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ]))

        elements.append(tbl)
        doc.build(elements)

        pdf_bytes  = buffer.getvalue()
        buffer.close()
        pdf_b64    = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_url    = f"data:application/pdf;base64,{pdf_b64}"

        with ui.dialog() as pdf_dialog:
            with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
                with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 border-b'):
                    ui.label(f'Statement: {account_number}').classes('text-xl font-bold')
                    ui.button('✕ Close', on_click=pdf_dialog.close).classes('bg-red-500 text-white px-4 py-2 rounded')
                ui.html(
                    f'<iframe src="{pdf_url}" width="100%" height="100%" '
                    f'style="border:none;min-height:calc(100vh - 80px);"></iframe>'
                ).classes('w-full flex-1')
        pdf_dialog.open()

    except Exception as e:
        from nicegui import ui
        ui.notify(f'Error generating statement: {e}', color='negative')
        print(f'Statement error: {e}')


def export_ledger_csv(account_number=None, from_date=None, to_date=None):
    """Export ledger transactions to CSV for Excel"""
    from io import BytesIO
    import csv
    try:
        data = []

        resolved_aux_id = None
        if account_number is not None:
            resolved_aux_id = _resolve_auxiliary_id(account_number)

        if resolved_aux_id is not None:
            sql = """
            SELECT t.transaction_date, t.reference_type, t.reference_id, t.description,
                   l.account_number, l.auxiliary_id, l.debit, l.credit,
                   SUM(l.debit - l.credit) OVER (ORDER BY t.jv_id ROWS UNBOUNDED PRECEDING) as Balance
            FROM accounting_transactions t
            INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            WHERE (l.auxiliary_id = ? OR l.account_number = ?)
            """
            params = [resolved_aux_id, account_number]
        else:
            sql = """
            SELECT t.transaction_date, t.reference_type, t.reference_id, t.description,
                   l.account_number, l.auxiliary_id, l.debit, l.credit,
                   SUM(l.debit - l.credit) OVER (ORDER BY t.jv_id ROWS UNBOUNDED PRECEDING) as Balance
            FROM accounting_transactions t
            INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            WHERE (l.account_number = ?)
            """
            params = [account_number]
        if from_date: params.append(from_date)
        if to_date: params.append(to_date)
        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
        sql += " ORDER BY t.transaction_date, t.jv_id"
        connection.contogetrows_with_params(sql, data, tuple(params))
        
        headers = ['Date', 'Reference Type', 'Ref ID', 'Description', 'Account', 'Aux ID', 'Debit', 'Credit', 'Balance']
        output = BytesIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in data:
            writer.writerow(row)
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"CSV export error: {e}")
        return None


def print_trial_balance(from_date=None, to_date=None):
    """Generate PDF Trial Balance report"""
    from nicegui import ui
    from reports import Reports
    try:
        trial_data = Reports.fetch_trial_balance(from_date, to_date)
        import base64
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("TRIAL BALANCE", styles['Title']))
        if from_date or to_date:
            period = f"Period: {from_date or 'All'} to {to_date or 'Current'}"
            elements.append(Paragraph(period, styles['Heading2']))
        elements.append(Spacer(1, 12))

        table_data = [['Account Number', 'Account Name', 'Debit', 'Credit', 'Balance']]
        total_debit, total_credit = 0, 0
        for row in trial_data:
            debit = float(row['Total Debit'])
            credit = float(row['Total Credit'])
            balance = float(row['Net Balance'])
            total_debit += debit
            total_credit += credit
            table_data.append([
                str(row['Account Number']),
                str(row['Account Name']),
                f"{debit:,.2f}",
                f"{credit:,.2f}",
                f"{balance:+,.2f}"
            ])
        # Totals
        table_data.append(['', 'TOTALS', f"{total_debit:,.2f}", f"{total_credit:,.2f}", f"{total_debit-total_credit:,.2f}"])

        tbl = Table(table_data, colWidths=[80, 200, 80, 80, 80])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))

        elements.append(tbl)
        if abs(total_debit - total_credit) > 0.01:
            elements.append(Paragraph("⚠️ TRIAL BALANCE OUT OF BALANCE!", styles['Heading3']))
        else:
            elements.append(Paragraph("✅ TRIAL BALANCE BALANCES", styles['Heading3']))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        pdf_url = f"data:application/pdf;base64,{pdf_b64}"

        with ui.dialog() as pdf_dialog:
            with ui.card().classes('w-screen h-screen p-0 m-0'):
                with ui.row().classes('p-4 bg-primary'):
                    ui.label("Trial Balance PDF").classes('text-white text-xl font-bold')
                    ui.button('Close', on_click=pdf_dialog.close, icon='close').classes('ml-auto text-white')
                ui.html(f'<iframe src="{pdf_url}" style="width:100%;height:calc(100vh-80px);border:none;"></iframe>')
        pdf_dialog.open()
    except Exception as e:
        ui.notify(f"PDF Error: {e}", color='negative')


def print_hierarchical_trial_balance_pdf(ledger_prefix, from_date=None, to_date=None):
    """Generate and display hierarchical trial balance PDF."""
    from nicegui import ui
    from reports import Reports
    import base64
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from io import BytesIO

    try:
        tree_data = Reports.fetch_hierarchical_trial_balance(ledger_prefix, from_date, to_date)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Header
        title = Paragraph(f"Hierarchical Trial Balance<br/><font size=12>Ledger Prefix: {ledger_prefix}</font>", styles['Heading1'])
        story.append(title)
        if from_date or to_date:
            period = Paragraph(f"Period: {from_date or 'Beginning'} to {to_date or 'Today'}", styles['Normal'])
            story.append(period)
        story.append(Spacer(1, 20))

        # Flatten tree for table with indentation
        table_data = [['Level', 'Code', 'Name', 'Debit', 'Credit', 'Balance']]
        grand_debit = grand_credit = 0

        def flatten_tree(node, indent='', is_root=True):
            nonlocal grand_debit, grand_credit
            display_level = node['level'] if node['level'] != 99 else 'Aux'
            table_data.append([
                display_level,
                indent + node['code'],
                node['name'][:40] + '...' if len(node['name']) > 40 else node['name'],
                f"{node['debit']:,.2f}",
                f"{node['credit']:,.2f}",
                f"{node['balance']:+,.2f}"
            ])
            if is_root:
                grand_debit += node['debit']
                grand_credit += node['credit']
            
            for child in node['children']:
                flatten_tree(child, indent + '  ', is_root=False)
            
            # Add transaction summary for leaves (only if they are auxiliary or leaf ledger)
            if node['transactions'] and (node['level'] == 99 or not node['children']):
                story.append(Spacer(1, 6))
                details_title = Paragraph(f"Transactions - {node['code']} {node['name']}", styles['Heading2'])
                story.append(details_title)
                
                txn_table = [['Date', 'Reference', 'Debit', 'Credit', 'Balance']]
                for txn in node['transactions'][:20]:  # Limit
                    txn_table.append([
                        txn['Date'],
                        txn['Reference'][:30],
                        f"{txn['Debit']:,.2f}",
                        f"{txn['Credit']:,.2f}",
                        f"{txn['Balance']:,.2f}"
                    ])
                txn_tbl = Table(txn_table, colWidths=[60, 140, 70, 70, 70])
                txn_tbl.setStyle(TableStyle([
                    ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('FONTSIZE', (0,0), (-1,-1), 8)
                ]))
                story.append(txn_tbl)

        for root in tree_data:
            flatten_tree(root, is_root=True)

        # Grand totals
        story.append(Spacer(1, 12))
        totals_data = [['', 'GRAND TOTALS', '', f"{grand_debit:,.2f}", f"{grand_credit:,.2f}", f"{grand_debit-grand_credit:+,.2f}"]]
        totals_tbl = Table(totals_data, colWidths=[30, 80, 200, 80, 80, 80])
        totals_tbl.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('ALIGN', (3,0), (-1,0), 'RIGHT'),
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white)
        ]))
        story.append(totals_tbl)

        # Balance check
        if abs(grand_debit - grand_credit) < 0.01:
            story.append(Paragraph("✅ Trial Balance is Balanced", styles['Heading2']))
        else:
            story.append(Paragraph("⚠️ Trial Balance Out of Balance!", styles['Heading2']))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        pdf_url = f"data:application/pdf;base64,{pdf_b64}"

        with ui.dialog() as dialog:
            with ui.card().classes('w-screen h-screen max-w-none max-h-none rounded-none p-0'):
                with ui.row().classes('p-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white justify-between items-center'):
                    ui.label(f"Hierarchical Trial Balance - {ledger_prefix}").classes('text-xl font-bold flex-1')
                    ui.button(icon='close', on_click=dialog.close, color='white')
                ui.html(f'<iframe src="{pdf_url}" style="border:none; width:100%; height:calc(100vh - 64px);"></iframe>')
        dialog.open()

    except Exception as e:
        ui.notify(f"Error generating PDF: {str(e)}", color='negative')
        print(f"PDF generation error: {e}")


def format_auxiliary_number_display(full_aux_number: str, ledger_name: str | None = None) -> str:
    """
    Display helper used by UI dropdowns/grids to show:
      <ledger_name> (<full_aux_number>)
    Example:
      "Cash LBP (5300.000001)"
    """
    full_aux_number = str(full_aux_number or '').strip()
    ledger_name = (str(ledger_name).strip() if ledger_name else '').strip()

    if ledger_name:
        return f"{ledger_name} ({full_aux_number})" if full_aux_number else ledger_name
    return full_aux_number


def _get_auxiliary_id_and_full_number_for_ledger_base(ledger_base: str):
    """
    Reuse an existing auxiliary row for a ledger base (e.g. '5300', '7111', '6011').

    Returns: (auxiliary_id_int, full_aux_number_str)
    Picks TOP 1 from `auxiliary` matching:
      - auxiliary_id = ledger_base
      - number LIKE '<ledger_base>.%'
    Ordered by auxiliary.id DESC (reuse any existing suffix).
    """
    base = str(ledger_base).strip()
    try:
        rows = []
        connection.contogetrows(
            """
            SELECT TOP 1 a.id, a.number
            FROM auxiliary a
            WHERE a.auxiliary_id = ?
              AND a.number LIKE ? + '.%'
            ORDER BY a.id DESC
            """,
            rows,
            params=[base, base]
        )
        if rows:
            aux_id = rows[0][0]
            full_num = rows[0][1]
            return int(aux_id), str(full_num)

        # If none exists, do NOT guess suffix by incrementing.
        # Create exactly suffix "1" for this base (e.g. 5300.1), matching the UI suffix format.
        default_full_number = f"{base}.1"

        # Find ledger exists for this base
        ledger_data = []
        connection.contogetrows(
            "SELECT Id FROM Ledger WHERE AccountNumber = ?",
            ledger_data,
            params=[base]
        )
        if not ledger_data:
            return None, default_full_number

        connection.insertingtodatabase(
            """
            INSERT INTO auxiliary (auxiliary_id, number, account_name, update_date, status)
            VALUES (?, ?, ?, GETDATE(), 1)
            """,
            (base, default_full_number, default_full_number)
        )
        # Re-fetch inserted id
        rows2 = []
        connection.contogetrows(
            "SELECT TOP 1 id FROM auxiliary WHERE auxiliary_id = ? AND number = ?",
            rows2,
            params=[base, default_full_number]
        )
        aux_id = rows2[0][0] if rows2 else None
        return (int(aux_id), default_full_number) if aux_id is not None else (None, default_full_number)
    except Exception as e:
        print(f"Error resolving auxiliary for base {ledger_base}: {e}")
        return None, f"{base}.000001"


def ensure_caisse_auxiliary(auxiliary_number='5300.000001', account_name='Caisse Cash LBP'):
    """
    Ensures the caisse/treasury auxiliary exists and returns the *full* auxiliary number.

    IMPORTANT:
    - For base like '5300' we must reuse existing 5300.* auxiliary rows (any suffix)
      rather than generating a new one.
    - If none exists, create exactly '<base>.000001' (no incrementing beyond that).
    """
    try:
        base_ledger = str(auxiliary_number).split('.')[0] if '.' in str(auxiliary_number) else str(auxiliary_number).strip()

        # Reuse existing auxiliary row for this base if any.
        aux_id, full_num = _get_auxiliary_id_and_full_number_for_ledger_base(base_ledger)
        if full_num:
            # If newly created, try to set a nicer account_name (best-effort).
            if aux_id is not None:
                try:
                    connection.insertingtodatabase(
                        "UPDATE auxiliary SET account_name = ? WHERE id = ?",
                        (account_name, aux_id)
                    )
                except Exception:
                    pass
            return full_num

        return str(auxiliary_number)
    except Exception as e:
        print(f"Error ensuring caisse auxiliary {auxiliary_number}: {e}")
        return auxiliary_number


def ensure_bank_auxiliary(auxiliary_number='51210.000001', account_name='Banque Cash LBP'):
    """
    Ensures the bank auxiliary exists and returns the *full* auxiliary number.

    IMPORTANT:
    - For base like '51210' we must reuse existing 51210.* auxiliary rows (any suffix)
      rather than generating a new one.
    - If none exists, create a default full number via the existing helper:
      base.1 (or base.000001 fallback on errors).
    """
    try:
        base_ledger = str(auxiliary_number).split('.')[0] if '.' in str(auxiliary_number) else str(auxiliary_number).strip()

        aux_id, full_num = _get_auxiliary_id_and_full_number_for_ledger_base(base_ledger)
        if full_num:
            if aux_id is not None:
                try:
                    connection.insertingtodatabase(
                        "UPDATE auxiliary SET account_name = ? WHERE id = ?",
                        (account_name, aux_id)
                    )
                except Exception:
                    pass
            return full_num

        return str(auxiliary_number)
    except Exception as e:
        print(f"Error ensuring bank auxiliary {auxiliary_number}: {e}")
        return auxiliary_number


def get_full_customer_aux_number(customer_id, customer_name=None, fallback_account_number='4111'):
    """
    Returns the full receivable auxiliary number for a customer:
      4111.<suffix>

    This is the exact number format expected by VAT close logic when it zeroes by auxiliary_id.
    """
    return ensure_customer_auxiliary(
        customer_id,
        customer_name=customer_name,
        fallback_account_number=fallback_account_number
    )


def get_full_supplier_aux_number(supplier_id, supplier_name=None, fallback_account_number='4011'):
    """
    Returns the full payable auxiliary number for a supplier:
      4011.<suffix>
    """
    return ensure_supplier_auxiliary(
        supplier_id,
        supplier_name=supplier_name,
        fallback_account_number=fallback_account_number
    )


def get_full_vat_customer_aux_number(customer_id, customer_name=None, auxiliary_number=None):
    """
    Returns the full VAT collected auxiliary number for a customer:
      44270.<suffix>

    suffix is derived from the provided customer auxiliary_number (4111.<suffix>)
    or computed/ensured if auxiliary_number is not given.
    """
    if auxiliary_number is None:
        auxiliary_number = ensure_customer_auxiliary(customer_id, customer_name=customer_name, fallback_account_number='4111')
    return ensure_vat_auxiliary('Customer', customer_id, customer_name, auxiliary_number)


def get_full_vat_supplier_aux_number(supplier_id, supplier_name=None, auxiliary_number=None):
    """
    Returns the full VAT deductible auxiliary number for a supplier:
      44210.<suffix>

    suffix is derived from the provided supplier auxiliary_number (4011.<suffix>)
    or computed/ensured if auxiliary_number is not given.
    """
    if auxiliary_number is None:
        auxiliary_number = ensure_supplier_auxiliary(supplier_id, supplier_name=supplier_name, fallback_account_number='4011')
    return ensure_vat_auxiliary('Supplier', supplier_id, supplier_name, auxiliary_number)


def get_full_caisse_aux_number(auxiliary_number='5300.000001', account_name='Caisse Cash LBP'):
    """
    Returns the full cash (caisse) auxiliary number (base 5300).
    """
    return ensure_caisse_auxiliary(auxiliary_number=auxiliary_number, account_name=account_name)


def get_full_bank_aux_number(auxiliary_number='51210.000001', account_name='Banque Cash LBP'):
    """
    Returns the full bank auxiliary number (base 51210).
    """
    return ensure_bank_auxiliary(auxiliary_number=auxiliary_number, account_name=account_name)
