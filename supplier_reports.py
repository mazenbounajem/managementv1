"""
supplier_reports.py
===================
Mirror of customer_reports.py but for suppliers.

Reports:
  1. Supplier Transactions    – all purchases per supplier
  2. Statement of Account     – debit/credit running balance
  3. Purchases & Returns      – purchases vs. purchase returns
  4. Global Supplier Balance  – all suppliers outstanding
"""

from nicegui import ui
from datetime import date
from connection import connection
from io import BytesIO
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def _q(sql, params=None):
    rows = []
    connection.contogetrows(sql, rows, params) if params else connection.contogetrows(sql, rows)
    return rows


def _company():
    try:
        info = connection.get_company_info()
        return info.get('company_name', 'Company') if info else 'Company'
    except Exception:
        return 'Company'


def _ts():
    return TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#3a1a5e')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f0ff')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#bbaacc')),
        ('FONTSIZE',       (0, 1), (-1, -1), 7.5),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',     (0, 0), (-1, -1), 4),
    ])


def _build(elements, landscape_mode=False):
    buf = BytesIO()
    ps  = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(buf, pagesize=ps,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    doc.build(elements)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def _show(b64, title):
    import base64
    from pdf_viewer_helper import show_pdf_modal
    pdf_bytes = base64.b64decode(b64.encode("utf-8"))
    show_pdf_modal(pdf_bytes, filename=f'{title.replace(" ", "_")}.pdf', title=title)


def _hdr(name, fd, td):
    s = getSampleStyleSheet()
    ts = ParagraphStyle('t', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    ss = ParagraphStyle('s', parent=s['Normal'],   fontSize=9,
                        textColor=colors.grey, spaceAfter=8)
    return [Paragraph(f"{_company()} — {name}", ts),
            Paragraph(f"Period: {fd}  to  {td}", ss),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#3a1a5e')),
            Spacer(1, 6*mm)]


def _totrow(ts_obj, idx):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#1a0d33'))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


def report_supplier_transactions(fd, td):
    sql = """
        SELECT s.name, p.invoice_number,
               CONVERT(varchar(10), p.purchase_date, 23),
               p.subtotal, ISNULL(p.total_vat,0), p.final_total,
               p.payment_method, p.payment_status
        FROM purchases p
        INNER JOIN suppliers s ON s.id = p.supplier_id
        WHERE CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        ORDER BY s.name, p.purchase_date
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No transactions.', color='warning'); return
    elements = _hdr('Supplier Transactions', fd, td)
    hdr = ['Supplier', 'Invoice', 'Date', 'HT', 'VAT', 'TTC', 'Method', 'Status']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        st = str(r[7] or '')
        data.append([str(r[0]), str(r[1]), str(r[2]),
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}",
                     f"${float(r[5] or 0):.2f}", str(r[6] or ''), st])
        if st.lower() == 'pending':
            ts_obj.add('TEXTCOLOR', (7, i), (7, i), colors.red)
    data.append(['TOTAL', '', '',
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}",
                 f"${sum(float(r[5] or 0) for r in rows):.2f}", '', ''])
    _totrow(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.16, .12, .10, .10, .08, .10, .10, .10]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Supplier Transactions')


def report_supplier_statement(fd, td):
    sql = """
        SELECT s.name,
               CONVERT(varchar(10), p.purchase_date, 23),
               p.invoice_number,
               p.final_total AS debit,
               ISNULL(
                   (SELECT SUM(sp.amount)
                    FROM supplier_payments sp
                    WHERE sp.supplier_id = s.id
                      AND CONVERT(date, sp.payment_date) = CONVERT(date, p.purchase_date)
                      AND CONVERT(date, sp.payment_date) >= ?
                      AND CONVERT(date, sp.payment_date) <= ?), 0) AS credit
        FROM purchases p
        INNER JOIN suppliers s ON s.id = p.supplier_id
        WHERE CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        ORDER BY s.name, p.purchase_date
    """
    rows = _q(sql, (fd, td, fd, td))
    if not rows: ui.notify('No statement data.', color='warning'); return
    elements = _hdr('Statement of Account — Suppliers', fd, td)
    hdr = ['Supplier', 'Date', 'Invoice', 'Debit', 'Credit', 'Balance']
    data = [hdr];  ts_obj = _ts()
    running = {}
    for i, r in enumerate(rows, 1):
        sup = str(r[0])
        deb = float(r[3] or 0);  cred = float(r[4] or 0)
        running[sup] = running.get(sup, 0) + deb - cred
        bal = running[sup]
        data.append([sup, str(r[1] or ''), str(r[2] or ''),
                     f"${deb:.2f}", f"${cred:.2f}", f"${bal:.2f}"])
        if bal > 0: ts_obj.add('TEXTCOLOR', (5, i), (5, i), colors.red)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.22, .12, .14, .14, .14, .14]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Supplier Statement')


def report_supplier_purchases_returns(fd, td):
    sql = """
        SELECT s.name,
               SUM(p.final_total) AS total_purchases,
               ISNULL(
                   (SELECT SUM(pr.total_amount)
                    FROM purchase_returns pr
                    WHERE pr.supplier_id = s.id
                      AND CONVERT(date, pr.return_date) >= ?
                      AND CONVERT(date, pr.return_date) <= ?), 0) AS total_returns,
               SUM(p.final_total) -
               ISNULL(
                   (SELECT SUM(pr.total_amount)
                    FROM purchase_returns pr
                    WHERE pr.supplier_id = s.id
                      AND CONVERT(date, pr.return_date) >= ?
                      AND CONVERT(date, pr.return_date) <= ?), 0) AS net_purchases
        FROM purchases p
        INNER JOIN suppliers s ON s.id = p.supplier_id
        WHERE CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        GROUP BY s.name
        ORDER BY net_purchases DESC
    """
    rows = _q(sql, (fd, td, fd, td, fd, td))
    if not rows: ui.notify('No data.', color='warning'); return
    elements = _hdr('Purchases & Returns per Supplier', fd, td)
    hdr = ['Supplier', 'Total Purchases', 'Total Returns', 'Net Purchases']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), f"${float(r[1] or 0):.2f}",
                     f"${float(r[2] or 0):.2f}", f"${float(r[3] or 0):.2f}"])
    data.append(['TOTAL',
                 f"${sum(float(r[1] or 0) for r in rows):.2f}",
                 f"${sum(float(r[2] or 0) for r in rows):.2f}",
                 f"${sum(float(r[3] or 0) for r in rows):.2f}"])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.40, .20, .20, .20]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Purchases & Returns')


def report_global_supplier_balance(fd, td):
    sql = """
        SELECT s.name, s.phone,
               ISNULL(s.balance, 0) AS balance_ll,
               ISNULL(s.balance_usd, 0) AS balance_usd,
               ISNULL(
                   (SELECT SUM(p.final_total)
                    FROM purchases p
                    WHERE p.supplier_id = s.id AND p.payment_status = 'pending'), 0) AS pending
        FROM suppliers s
        WHERE s.is_active = 1
        ORDER BY pending DESC, s.name
    """
    rows = _q(sql)
    if not rows: ui.notify('No suppliers.', color='warning'); return
    elements = _hdr('Global Supplier Balance', fd, td)
    hdr = ['Supplier', 'Phone', 'Balance LL', 'Balance USD', 'Pending Invoices']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1] or ''),
                     f"L.L. {float(r[2] or 0):,.0f}",
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}"])
    data.append(['TOTAL', '',
                 f"L.L. {sum(float(r[2] or 0) for r in rows):,.0f}",
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}"])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = landscape(A4)[0] - 30*mm
    cw = [avail*w for w in [.35, .15, .18, .15, .17]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Global Supplier Balance')


# ── PER‑SUPPLIER STATEMENT ─────────────────────────────────────────────────

def report_single_supplier_statement(fd, td, supplier_id, supplier_name):
    """Per-supplier statement: opening balance + purchases + returns + payments with running balance.

    Cash purchases appear as both debit (Purchase) and credit (Cash) — immediate settlement.
    On-account purchases appear as debit only until settled via return or payment.

    Supplier payments are allocated via supplier_payment_details, which reduces
    purchases.total_amount. We add back settled amounts to show original invoice values.
    """
    has_details = False
    try:
        r = _q("SELECT TOP 1 1 FROM supplier_payment_details")
        has_details = bool(r)
    except:
        pass

    if has_details:
        settle_clause = (
            "+ COALESCE((SELECT SUM(settlement_amount) FROM supplier_payment_details"
            " WHERE source_type = 'Purchase' AND source_id = purchases.id), 0)"
        )
    else:
        settle_clause = ""

    opening = 0.0
    if has_details:
        open_rows = _q("""
            SELECT
                ISNULL((SELECT SUM(ISNULL(total_amount, 0)) FROM purchases
                         WHERE supplier_id = ? AND payment_status = 'pending'
                           AND CONVERT(date, purchase_date) < CONVERT(date, ?)), 0)
                + COALESCE((SELECT SUM(settlement_amount) FROM supplier_payment_details
                            WHERE source_type = 'Purchase' AND source_id IN (
                                SELECT id FROM purchases WHERE supplier_id = ?
                                AND payment_status = 'pending'
                                AND CONVERT(date, purchase_date) < CONVERT(date, ?)
                            )), 0)
                - ISNULL((SELECT SUM(ISNULL(total_amount, 0)) FROM purchase_returns
                           WHERE supplier_id = ?
                             AND CONVERT(date, purchase_date) < CONVERT(date, ?)), 0)
                - ISNULL((SELECT SUM(ISNULL(amount, 0)) FROM supplier_payment
                           WHERE supplier_id = ?
                             AND CONVERT(date, payment_date) < CONVERT(date, ?)), 0)
        """, (supplier_id, fd, supplier_id, fd, supplier_id, fd, supplier_id, fd))
    else:
        open_rows = _q("""
            SELECT
                ISNULL((SELECT SUM(ISNULL(total_amount, 0)) FROM purchases
                         WHERE supplier_id = ? AND payment_status = 'pending'
                           AND CONVERT(date, purchase_date) < CONVERT(date, ?)), 0)
                - ISNULL((SELECT SUM(ISNULL(total_amount, 0)) FROM purchase_returns
                           WHERE supplier_id = ?
                             AND CONVERT(date, purchase_date) < CONVERT(date, ?)), 0)
                - ISNULL((SELECT SUM(ISNULL(amount, 0)) FROM supplier_payment
                           WHERE supplier_id = ?
                             AND CONVERT(date, payment_date) < CONVERT(date, ?)), 0)
        """, (supplier_id, fd, supplier_id, fd, supplier_id, fd))
    if open_rows:
        opening = float(open_rows[0][0])

    txns = _q(f"""
        SELECT tx_date, ref, tx_type, debit, credit FROM (
            -- All purchases are debits — add back settled amounts to show original invoice
            SELECT CONVERT(date, purchase_date) as tx_date, invoice_number as ref,
                   'Purchase' as tx_type, total_amount {settle_clause} as debit, 0 as credit
            FROM purchases WHERE supplier_id = ?
              AND CONVERT(date, purchase_date) >= ? AND CONVERT(date, purchase_date) <= ?

            UNION ALL

            -- Cash purchases settled immediately → matching credit
            SELECT CONVERT(date, purchase_date), invoice_number,
                   'Cash', 0, total_amount {settle_clause}
            FROM purchases WHERE supplier_id = ? AND payment_status = 'completed'
              AND payment_method = 'Cash'
              AND CONVERT(date, purchase_date) >= ? AND CONVERT(date, purchase_date) <= ?

            UNION ALL

            -- Returns are credits
            SELECT CONVERT(date, purchase_date), 'Ret-' + CAST(id AS NVARCHAR(20)),
                   'Return', 0, total_amount
            FROM purchase_returns WHERE supplier_id = ?
              AND CONVERT(date, purchase_date) >= ? AND CONVERT(date, purchase_date) <= ?

            UNION ALL

            -- Payments are credits
            SELECT CONVERT(date, payment_date), 'Pay_' + CAST(id AS NVARCHAR(20)),
                   'Payment', 0, amount
            FROM supplier_payment WHERE supplier_id = ?
              AND CONVERT(date, payment_date) >= ? AND CONVERT(date, payment_date) <= ?
        ) t ORDER BY tx_date, ref,
          CASE tx_type WHEN 'Purchase' THEN 1 WHEN 'Cash' THEN 2 WHEN 'Return' THEN 3 WHEN 'Payment' THEN 4 END
    """, (supplier_id, fd, td, supplier_id, fd, td, supplier_id, fd, td, supplier_id, fd, td))

    if not txns and abs(opening) < 0.001:
        ui.notify(f'No transactions found for {supplier_name}', color='warning')
        return

    title = f'Statement of Account — {supplier_name}'
    elements = _hdr(title, fd, td)
    hdr = ['Date', 'Reference', 'Type', 'Debit', 'Credit', 'Balance']
    data = [hdr]
    ts_obj = _ts()

    running = opening
    data.append([fd, '', 'Opening Balance', '', '', f'${running:.2f}'])

    for r in txns:
        d = float(r[3] or 0)
        c = float(r[4] or 0)
        running = running + d - c
        idx = len(data)
        data.append([
            str(r[0] or ''), str(r[1] or ''), str(r[2] or ''),
            f'${d:.2f}' if d > 0 else '',
            f'${c:.2f}' if c > 0 else '',
            f'${running:.2f}'
        ])
        if running > 0:
            ts_obj.add('TEXTCOLOR', (5, idx), (5, idx), colors.red)

    data.append(['', '', 'CLOSING BALANCE', '', '', f'${running:.2f}'])
    _totrow(ts_obj, len(data) - 1)

    ps = landscape(A4)
    avail = ps[0] - 30 * mm
    cw = [avail * w for w in [.14, .18, .12, .16, .16, .16]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements, landscape_mode=True), f'Statement_{supplier_name}')


# ── SUPPLIER REGISTRY ─────────────────────────────────────────────────────────

REPORTS = {
    'sup_tx':      ('Supplier Transactions',       report_supplier_transactions),
    'sup_stmt':    ('Statement of Account',        report_supplier_statement),
    'sup_returns': ('Purchases & Returns',         report_supplier_purchases_returns),
    'sup_balance': ('Global Supplier Balance',     report_global_supplier_balance),
}

DESCRIPTIONS = {
    'sup_tx':      'All purchase invoices per supplier with HT, VAT, TTC, method and status.',
    'sup_stmt':    'Running debit/credit balance per supplier over the selected period.',
    'sup_returns': 'Total purchases vs. total returns per supplier, showing net purchases.',
    'sup_balance': 'All active suppliers with their current account balance and pending invoice total.',
}


def open_print_special_dialog(supplier_id=None, supplier_name=None):
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'sup_tx', 'from_date': first_of_month, 'to_date': today,
             'supplier_id': supplier_id, 'supplier_name': supplier_name}
    btns = {};  refs = {}
    per_supplier_key = None

    if supplier_id:
        per_supplier_key = f'single_stmt_{supplier_id}'

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(168,85,247,0.25);border:1px solid rgba(168,85,247,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs:
            if key == per_supplier_key:
                refs['n'].text = f'Statement of Account — {supplier_name}'
            else:
                refs['n'].text = REPORTS[key][0]
        if 'd' in refs:
            if key == per_supplier_key:
                refs['d'].text = f'All transactions for {supplier_name}: purchases, returns, and payments with running balance.'
            else:
                refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#130d1f; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('business', size='1.5rem').classes('text-purple-400')
                    ui.label('Supplier Report Center').classes(
                        'text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:250px; min-width:250px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-purple-400 uppercase tracking-widest mb-2')
                    if per_supplier_key:
                        b = ui.button(f'Statement — {supplier_name}',
                                      on_click=lambda: select(per_supplier_key))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(168,85,247,0.25);border:1px solid rgba(168,85,247,0.5);'
                                      ' text-align:left; justify-content:flex-start;')
                        btns[per_supplier_key] = b
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left;'
                                      ' justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    default_title = f'Statement of Account — {supplier_name}' if per_supplier_key else REPORTS['sup_tx'][0]
                    refs['n'] = ui.label(default_title)\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
                            ui.input(value=first_of_month).props('type=date outlined dense dark color=purple stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
                            ui.input(value=today).props('type=date outlined dense dark color=purple stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'to_date': e.value}))

                        def _run():
                            k, f, t = state['report_key'], state['from_date'], state['to_date']
                            if not f or not t: ui.notify('Select dates.', color='warning'); return
                            if f > t: ui.notify('From before To.', color='negative'); return
                            try:
                                if per_supplier_key and k == per_supplier_key:
                                    report_single_supplier_statement(f, t, state['supplier_id'], state['supplier_name'])
                                else:
                                    REPORTS[k][1](f, t)
                            except Exception as ex:
                                ui.notify(f'Error: {ex}', color='negative')
                                import traceback; traceback.print_exc()

                        ui.button('View Report', icon='visibility', on_click=_run)\
                          .props('unelevated color=purple')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
                        default_desc = (f'All transactions for {supplier_name}: purchases, returns, and payments with running balance.'
                                        if per_supplier_key else DESCRIPTIONS.get('sup_tx', ''))
                        refs['d'] = ui.label(default_desc)\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')

        if per_supplier_key:
            select(per_supplier_key)
        else:
            select('sup_tx')
    dlg.open()
