from connection import connection


def get_next_auxiliary(account_base):
    """
    Generates the next sequential auxiliary ID for a given base account.
    Example: account_base = "4111" returns "4111.000001"
    """
    try:
        data = []
        sql = "SELECT number FROM auxiliary WHERE number LIKE ? ORDER BY number DESC"
        connection.contogetrows_with_params(sql, data, (f"{account_base}.%",))
        
        if data and data[0][0]:
            last_number = data[0][0]
            parts = last_number.split('.')
            if len(parts) == 2 and parts[1].isdigit():
                next_seq = int(parts[1]) + 1
                return f"{account_base}.{next_seq:06d}"
        
        return f"{account_base}.000001"
    except Exception as e:
        print(f"Error generating auxiliary for {account_base}: {e}")
        import time
        return f"{account_base}.{int(time.time() * 1000) % 1000000:06d}"


def register_auxiliary(auxiliary_number, account_name):
    """Registers the generated auxiliary in the database"""
    try:
        sql = "INSERT INTO auxiliary (account_name, number, update_date, status) VALUES (?, ?, GETDATE(), 1)"
        connection.insertingtodatabase(sql, (account_name, auxiliary_number))
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
    auxiliary_number: The main auxiliary number (e.g. 4011.000001)
    """
    try:
        if reference_type == 'Supplier':
            base_ledger = '44210'
            account_name_prefix = "VAT Supplier"
        else:
            base_ledger = '44270'
            account_name_prefix = "VAT Customer"
            
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
            connection.insertingtodatabase(
                "INSERT INTO auxiliary (ledger_id, number, account_name, status) VALUES (?, ?, ?, 1)",
                (ledger_id, vat_acct, f"{account_name_prefix}: {entity_name}")
            )
        return vat_acct
    except Exception as e:
        print(f"Error ensuring VAT auxiliary: {e}")
        return f"{base_ledger}.000001" if 'base_ledger' in locals() else "44210.000001"


def _normalize_lines(lines):
    """
    Normalize accounting lines to list-of-dicts format.

    Accepted formats:
      1. List of dicts: [{'account': '4111.000001', 'debit': 100, 'credit': 0}, ...]
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
            aux_id    = line.get('account', '')
            base_acct = aux_id.split('.')[0] if '.' in str(aux_id) else str(aux_id)

            connection.insertingtodatabase(line_sql, (
                jv_id,
                base_acct,
                aux_id,
                float(line.get('debit',  0)),
                float(line.get('credit', 0))
            ))

        return jv_id

    except Exception as e:
        print(f"Error saving accounting transaction: {e}")
        raise e


def show_transactions_dialog(reference_type=None, reference_id=None, account_number=None, from_date=None, to_date=None):
    """
    Opens a dialog showing accounting transactions for a given reference or account,
    including Date, Reference, Account, Remark, Debit, Credit, and Running Balance.
    """
    from nicegui import ui

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-5xl p-6'):
        ui.label('Accounting Transactions Ledger').classes('text-xl font-bold mb-4')

        data = []
        sql = """
        SELECT t.jv_id, t.transaction_date, t.reference_type, t.reference_id,
               l.account_number, l.auxiliary_id, l.debit, l.credit, t.description
        FROM accounting_transactions t
        INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        WHERE 1=1
        """
        params = []
        if reference_type and reference_id:
            sql += " AND t.reference_type = ? AND t.reference_id = ?"
            params.extend([reference_type, str(reference_id)])
        elif account_number:
            sql += " AND (l.auxiliary_id = ? OR l.account_number = ?)"
            params.extend([account_number, account_number])

        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)

        sql += " ORDER BY t.jv_id ASC, l.account_number ASC"

        connection.contogetrows_with_params(sql, data, tuple(params))

        rows = []
        total_debit  = 0.0
        total_credit = 0.0
        running_balance = 0.0

        for r in data:
            debit  = float(r[6] or 0)
            credit = float(r[7] or 0)
            total_debit  += debit
            total_credit += credit
            running_balance += debit - credit

            rows.append({
                'jv_id':   r[0],
                'date':    str(r[1]).split(' ')[0] if r[1] else '',
                'ref':     f"{r[2]} #{r[3]}",
                'account': str(r[5] or r[4] or ''),
                'remark':  str(r[8] or ''),
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
        sql = """
        SELECT t.transaction_date, t.reference_type, t.reference_id, t.description,
               l.debit, l.credit
        FROM accounting_transactions t
        INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        WHERE (l.auxiliary_id = ? OR l.account_number = ?)
        """
        params = [account_number, account_number]

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
        sql = """
        SELECT t.transaction_date, t.reference_type, t.reference_id, t.description,
               l.account_number, l.auxiliary_id, l.debit, l.credit,
               SUM(l.debit - l.credit) OVER (ORDER BY t.jv_id ROWS UNBOUNDED PRECEDING) as Balance
        FROM accounting_transactions t
        INNER JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        WHERE (l.auxiliary_id = ? OR l.account_number = ?)
        """
        params = [account_number, account_number]
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
    """Generate hierarchical trial balance PDF like statement format."""
    from nicegui import ui
    from reports import Reports
    try:
        tree_data = Reports.fetch_hierarchical_trial_balance(ledger_prefix, from_date, to_date)
        import base64
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        title = f"Hierarchical Trial Balance - Ledger {ledger_prefix}"
        elements.append(Paragraph(title, styles['Heading1']))
        if from_date or to_date:
            period = f"Period: {from_date or 'All'} to {to_date or 'Today'}"
            elements.append(Paragraph(period, styles['Normal']))
        elements.append(Spacer(1, 12))

        grand_debit = grand_credit = 0

        # Hierarchical tree summary table
        tree_table_data = [['Level', 'Code', 'Name', 'Debit', 'Credit', 'Balance']]
        for row in tree_data:
            indent = '  ' * (row['level'] - 1)
            tree_table_data.append([
                str(row['level']),
                f"{indent}{row['code']}",
                row['name'],
                f"{row['total_debit']:,.2f}",
                f"{row['total_credit']:,.2f}",
                f"{row['balance']:+,.2f}"
            ])
            grand_debit += row['total_debit']
            grand_credit += row['total_credit']

        tree_table_data.append(['', 'GRAND TOTALS', '', f"{grand_debit:,.2f}", f"{grand_credit:,.2f}", f"{grand_debit-grand_credit:,.2f}"])

        tbl = Table(tree_table_data, colWidths=[30, 80, 200, 80, 80, 80])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(tbl)

        # Detailed transactions for leaf nodes
        for row in tree_data:
            if row['has_details'] and row['children_count'] == 0:  # Leaf with txns
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(f"Detailed Transactions - {row['code']} {row['name']}", styles['Heading2']))
                details = Reports.fetch_account_details(row['code'], from_date, to_date)
                if details:
                    detail_data = [['Date', 'Reference', 'Debit', 'Credit', 'Balance']] + [
                        [d['Date'], d['Reference'], f"{d['Debit']:,.2f}", f"{d['Credit']:,.2f}", f"{d['Balance']:,.2f}"] 
                        for d in details
                    ]
                    detail_tbl = Table(detail_data)
                    detail_tbl.setStyle(TableStyle([
                        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black)
                    ]))
                    elements.append(detail_tbl)

        if abs(grand_debit - grand_credit) < 0.01:
            elements.append(Paragraph("✅ BALANCED", styles['Heading2']))
        else:
            elements.append(Paragraph("⚠️ OUT OF BALANCE", styles['Heading2']))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        pdf_url = f"data:application/pdf;base64,{pdf_b64}"

        with ui.dialog() as pdf_dialog:
            with ui.card().classes('w-screen h-screen p-0 m-0'):
                with ui.row().classes('p-4 bg-primary'):
                    ui.label(f"Hierarchical Trial Balance - {ledger_prefix}").classes('text-white text-xl font-bold')
                    ui.button('Close', on_click=pdf_dialog.close, icon='close').classes('ml-auto text-white')
                ui.html(f'<iframe src="{pdf_url}" style="width:100%;height:calc(100vh-80px);border:none;"></iframe>')
        pdf_dialog.open()
    except Exception as e:
        ui.notify(f"PDF Error: {e}", color='negative')
