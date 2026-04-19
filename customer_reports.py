"""
customer_reports.py  /  supplier_reports.py  (combined template)
================================================================
Customer reports:
  1. Customer Transactions    – ledger entries per customer
  2. Statement of Account     – running balance per date range
  3. Sales & Returned Products – sales vs. returns per customer
  4. Global Customer Balance  – all customers outstanding balance

Used by:
  customerui.py  → open_print_special_dialog()  (accent = blue)

supplier_reports.py mirrors this for suppliers.
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


def _ts(header_color='#1a3a6e'):
    return TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor(header_color)),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#aaaacc')),
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
    data_url = f"data:application/pdf;base64,{b64}"
    with ui.dialog() as d:
        with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
            with ui.row().classes('w-full justify-between items-center p-3'
                                  ' bg-gray-900 border-b border-white/10'):
                ui.label(title).classes('text-white font-bold text-lg')
                ui.button('X Close', on_click=d.close).classes(
                    'bg-red-600 text-white px-4 py-1 rounded text-sm')
            ui.html(f'<iframe src="{data_url}" width="100%" height="100%"'
                    ' style="border:none; min-height:calc(100vh - 56px);"></iframe>'
                    ).classes('w-full flex-1')
    d.open()


def _hdr(name, fd, td, accent='#1a3a6e'):
    s = getSampleStyleSheet()
    ts = ParagraphStyle('t', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    ss = ParagraphStyle('s', parent=s['Normal'],   fontSize=9,
                        textColor=colors.grey, spaceAfter=8)
    return [Paragraph(f"{_company()} — {name}", ts),
            Paragraph(f"Period: {fd}  to  {td}", ss),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor(accent)),
            Spacer(1, 6*mm)]


def _totrow(ts_obj, idx, bg='#0d1f4e'):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor(bg))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOMER REPORTS
# ─────────────────────────────────────────────────────────────────────────────

def report_customer_transactions(fd, td):
    sql = """
        SELECT c.customer_name, s.invoice_number,
               CONVERT(varchar(10), s.sale_date, 23),
               s.subtotal, ISNULL(s.total_vat,0), s.total_amount,
               s.payment_method, s.payment_status
        FROM sales s
        INNER JOIN customers c ON c.id = s.customer_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        ORDER BY c.customer_name, s.sale_date
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No transactions found.', color='warning'); return
    elements = _hdr('Customer Transactions', fd, td)
    hdr = ['Customer', 'Invoice', 'Date', 'HT', 'VAT', 'TTC', 'Method', 'Status']
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
    cw = [avail*w for w in [.18, .12, .10, .10, .08, .10, .10, .09]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Customer Transactions')


def report_customer_statement(fd, td):
    """Running balance statement per customer."""
    sql = """
        SELECT c.customer_name,
               CONVERT(varchar(10), s.sale_date, 23),
               s.invoice_number,
               s.total_amount AS debit,
               ISNULL(
                   (SELECT SUM(cr.amount)
                    FROM customer_receipts cr
                    WHERE cr.customer_id = c.id
                      AND CONVERT(date, cr.receipt_date) = CONVERT(date, s.sale_date)
                      AND CONVERT(date, cr.receipt_date) >= ?
                      AND CONVERT(date, cr.receipt_date) <= ?), 0) AS credit
        FROM sales s
        INNER JOIN customers c ON c.id = s.customer_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        ORDER BY c.customer_name, s.sale_date
    """
    rows = _q(sql, (fd, td, fd, td))
    if not rows: ui.notify('No statement data.', color='warning'); return
    elements = _hdr('Statement of Account — Customers', fd, td)
    hdr = ['Customer', 'Date', 'Invoice', 'Debit', 'Credit', 'Balance']
    data = [hdr];  ts_obj = _ts()
    running = {}
    for i, r in enumerate(rows, 1):
        cust = str(r[0])
        deb  = float(r[3] or 0);  cred = float(r[4] or 0)
        running[cust] = running.get(cust, 0) + deb - cred
        bal = running[cust]
        data.append([cust, str(r[2] or ''), str(r[2] or ''),
                     f"${deb:.2f}", f"${cred:.2f}", f"${bal:.2f}"])
        if bal > 0: ts_obj.add('TEXTCOLOR', (5, i), (5, i), colors.red)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.22, .12, .14, .14, .14, .14]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Statement of Account')


def report_customer_sales_returns(fd, td):
    sql = """
        SELECT c.customer_name,
               SUM(s.total_amount) AS total_sales,
               ISNULL(
                   (SELECT SUM(sr.total_amount)
                    FROM sales_returns sr
                    WHERE sr.customer_id = c.id
                      AND CONVERT(date, sr.return_date) >= ?
                      AND CONVERT(date, sr.return_date) <= ?), 0) AS total_returns,
               SUM(s.total_amount) -
               ISNULL(
                   (SELECT SUM(sr.total_amount)
                    FROM sales_returns sr
                    WHERE sr.customer_id = c.id
                      AND CONVERT(date, sr.return_date) >= ?
                      AND CONVERT(date, sr.return_date) <= ?), 0) AS net_sales
        FROM sales s
        INNER JOIN customers c ON c.id = s.customer_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY c.customer_name
        ORDER BY net_sales DESC
    """
    rows = _q(sql, (fd, td, fd, td, fd, td))
    if not rows: ui.notify('No data.', color='warning'); return
    elements = _hdr('Sales & Returns per Customer', fd, td)
    hdr = ['Customer', 'Total Sales', 'Total Returns', 'Net Sales']
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
    elements.append(t);  _show(_build(elements), 'Sales & Returns')


def report_global_customer_balance(fd, td):
    sql = """
        SELECT c.customer_name, c.phone,
               ISNULL(c.balance, 0) AS balance,
               ISNULL(
                   (SELECT SUM(s.total_amount)
                    FROM sales s
                    WHERE s.customer_id = c.id AND s.payment_status = 'pending'), 0) AS pending
        FROM customers c
        WHERE c.is_active = 1
        ORDER BY pending DESC, c.customer_name
    """
    rows = _q(sql)
    if not rows: ui.notify('No customers.', color='warning'); return
    elements = _hdr('Global Customer Balance', fd, td)
    hdr = ['Customer', 'Phone', 'Account Balance', 'Pending Invoices']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1] or ''),
                     f"${float(r[2] or 0):.2f}", f"${float(r[3] or 0):.2f}"])
    data.append(['TOTAL', '',
                 f"${sum(float(r[2] or 0) for r in rows):.2f}",
                 f"${sum(float(r[3] or 0) for r in rows):.2f}"])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.40, .20, .20, .20]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Global Customer Balance')


# ── CUSTOMER REGISTRY ─────────────────────────────────────────────────────────

REPORTS = {
    'cust_tx':       ('Customer Transactions',      report_customer_transactions),
    'cust_stmt':     ('Statement of Account',       report_customer_statement),
    'cust_returns':  ('Sales & Returns',            report_customer_sales_returns),
    'cust_balance':  ('Global Customer Balance',    report_global_customer_balance),
}

DESCRIPTIONS = {
    'cust_tx':      'All sales invoices per customer with HT, VAT, TTC, method and status.',
    'cust_stmt':    'Running debit/credit balance per customer over the selected period.',
    'cust_returns': 'Total sales vs. total returns per customer, showing net sales.',
    'cust_balance': 'All active customers with their current account balance and pending invoice total.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'cust_tx', 'from_date': first_of_month, 'to_date': today}
    btns = {};  refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(59,130,246,0.25);border:1px solid rgba(59,130,246,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#0d1525; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('people', size='1.5rem').classes('text-blue-400')
                    ui.label('Customer Report Center').classes(
                        'text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:250px; min-width:250px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-blue-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left;'
                                      ' justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['cust_tx'][0])\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-blue-400 uppercase tracking-widest')
                            ui.input(value=first_of_month).props('type=date outlined dense dark color=blue stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-blue-400 uppercase tracking-widest')
                            ui.input(value=today).props('type=date outlined dense dark color=blue stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'to_date': e.value}))

                        def _run():
                            k, f, t = state['report_key'], state['from_date'], state['to_date']
                            if not f or not t: ui.notify('Select dates.', color='warning'); return
                            if f > t: ui.notify('From before To.', color='negative'); return
                            try: REPORTS[k][1](f, t)
                            except Exception as ex:
                                ui.notify(f'Error: {ex}', color='negative')
                                import traceback; traceback.print_exc()

                        ui.button('View Report', icon='visibility', on_click=_run)\
                          .props('unelevated color=blue')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-blue-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('cust_tx', ''))\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('cust_tx')
    dlg.open()
