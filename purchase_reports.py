"""
purchase_reports.py
===================
Print Special report suite for the Purchase module.

Reports:
  1. Purchase by Supplier    – grouped by supplier with totals
  2. VAT by Supplier         – input VAT breakdown per supplier
  3. Total Purchase Summary  – daily / monthly totals
  4. Profit on Purchase      – purchase cost vs. potential retail
  5. Aging Invoices          – unpaid invoices grouped by age bucket
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
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#2d1a4e')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f0f8')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#bbbbbb')),
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


def _hdr(name, fd, td):
    s = getSampleStyleSheet()
    ts = ParagraphStyle('t', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    ss = ParagraphStyle('s', parent=s['Normal'],   fontSize=9,
                        textColor=colors.grey, spaceAfter=8)
    return [Paragraph(f"{_company()} — {name}", ts),
            Paragraph(f"Period: {fd}  to  {td}", ss),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2d1a4e')),
            Spacer(1, 6*mm)]


def _totrow(ts_obj, idx):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#1a0d33'))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


# ── Report 1: Purchase by Supplier ───────────────────────────────────────────

def report_purchase_by_supplier(fd, td):
    sql = """
        SELECT s.name, p.invoice_number,
               CONVERT(varchar(10), p.purchase_date, 23),
               p.subtotal, ISNULL(p.total_vat,0), p.final_total,
               p.payment_status
        FROM purchases p
        INNER JOIN suppliers s ON s.id = p.supplier_id
        WHERE CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        ORDER BY s.name, p.purchase_date
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No purchase data.', color='warning'); return
    elements = _hdr('Purchase by Supplier', fd, td)
    hdr = ['Supplier', 'Invoice', 'Date', 'Base HT', 'VAT', 'Total TTC', 'Status']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        st = str(r[6] or '');
        data.append([str(r[0]), str(r[1]), str(r[2]),
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}",
                     f"${float(r[5] or 0):.2f}", st])
        if st.lower() == 'pending':
            ts_obj.add('TEXTCOLOR', (6, i), (6, i), colors.red)
    data.append(['GRAND TOTAL', '', '',
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}",
                 f"${sum(float(r[5] or 0) for r in rows):.2f}", ''])
    _totrow(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.18, .14, .10, .13, .10, .13, .10]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Purchase by Supplier')


# ── Report 2: VAT by Supplier ─────────────────────────────────────────────────

def report_vat_by_supplier(fd, td):
    sql = """
        SELECT s.name,
               SUM(pi.quantity * pi.unit_cost) AS base_ht,
               SUM(ISNULL(pi.vat_amount, 0))   AS total_vat,
               COUNT(DISTINCT p.id)             AS invoice_count
        FROM purchase_items pi
        INNER JOIN purchases p ON p.id   = pi.purchase_id
        INNER JOIN suppliers s ON s.id   = p.supplier_id
        WHERE CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        GROUP BY s.name
        ORDER BY total_vat DESC
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No VAT data.', color='warning'); return
    elements = _hdr('Purchase VAT by Supplier', fd, td)
    hdr = ['Supplier', 'Base HT', 'Total VAT', '# Invoices']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), f"${float(r[1] or 0):.2f}",
                     f"${float(r[2] or 0):.2f}", str(r[3])])
    data.append(['TOTAL', f"${sum(float(r[1] or 0) for r in rows):.2f}",
                 f"${sum(float(r[2] or 0) for r in rows):.2f}",
                 str(sum(int(r[3]) for r in rows))])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.40, .20, .20, .20]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'VAT by Supplier')


# ── Report 3: Total Purchase Summary ─────────────────────────────────────────

def report_total_purchase_summary(fd, td):
    sql = """
        SELECT CONVERT(varchar(10), p.purchase_date, 23) AS dt,
               COUNT(DISTINCT p.id)                       AS inv_count,
               SUM(p.subtotal)                            AS total_ht,
               SUM(ISNULL(p.total_vat, 0))                AS total_vat,
               SUM(p.final_total)                         AS total_ttc
        FROM purchases p
        WHERE CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        GROUP BY CONVERT(varchar(10), p.purchase_date, 23)
        ORDER BY dt
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No purchase data.', color='warning'); return
    elements = _hdr('Total Purchase Summary', fd, td)
    hdr = ['Date', '# Invoices', 'Total HT', 'Total VAT', 'Total TTC']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), f"${float(r[2] or 0):.2f}",
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}"])
    data.append(['TOTAL', str(sum(int(r[1]) for r in rows)),
                 f"${sum(float(r[2] or 0) for r in rows):.2f}",
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}"])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.20, .15, .22, .22, .22]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Total Purchase Summary')


# ── Report 4: Profit on Purchase ─────────────────────────────────────────────

def report_profit_on_purchase(fd, td):
    sql = """
        SELECT p.product_name, s.name AS supplier,
               SUM(pi.quantity) AS total_qty,
               SUM(pi.quantity * pi.unit_cost) AS total_cost,
               SUM(pi.quantity * pr.price)     AS potential_retail,
               SUM(pi.quantity * (pr.price - pi.unit_cost)) AS potential_profit,
               CASE WHEN SUM(pi.quantity * pr.price) > 0
                    THEN SUM(pi.quantity * (pr.price - pi.unit_cost))
                         / SUM(pi.quantity * pr.price) * 100
                    ELSE 0 END AS margin_pct
        FROM purchase_items pi
        INNER JOIN purchases pu ON pu.id   = pi.purchase_id
        INNER JOIN products  p  ON p.id    = pi.product_id
        LEFT  JOIN suppliers s  ON s.id    = pu.supplier_id
        LEFT  JOIN products  pr ON pr.id   = pi.product_id
        WHERE CONVERT(date, pu.purchase_date) >= ?
          AND CONVERT(date, pu.purchase_date) <= ?
        GROUP BY p.product_name, s.name
        ORDER BY potential_profit DESC
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No data.', color='warning'); return
    elements = _hdr('Profit on Purchase', fd, td)
    hdr = ['Product', 'Supplier', 'Qty', 'Total Cost', 'Retail Value', 'Profit', 'Margin %']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        pct = float(r[6] or 0)
        data.append([str(r[0]), str(r[1] or ''), str(r[2]),
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}",
                     f"${float(r[5] or 0):.2f}", f"{pct:.1f}%"])
        if pct < 0: ts_obj.add('TEXTCOLOR', (5, i), (6, i), colors.red)
    data.append(['TOTAL', '', str(sum(int(r[2] or 0) for r in rows)),
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}",
                 f"${sum(float(r[5] or 0) for r in rows):.2f}", ''])
    _totrow(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.24, .15, .07, .13, .13, .13, .10]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Profit on Purchase')


# ── Report 5: Aging Invoices ─────────────────────────────────────────────────

def report_aging_invoices(fd, td):
    sql = """
        SELECT s.name, p.invoice_number,
               CONVERT(varchar(10), p.purchase_date, 23),
               p.final_total, p.payment_status,
               DATEDIFF(day, p.purchase_date, GETDATE()) AS age_days
        FROM purchases p
        INNER JOIN suppliers s ON s.id = p.supplier_id
        WHERE p.payment_status IN ('pending', 'Pending')
        ORDER BY age_days DESC
    """
    rows = _q(sql)
    if not rows: ui.notify('No pending invoices!', color='positive'); return
    elements = _hdr('Aging Invoices (Unpaid)', fd, td)
    hdr = ['Supplier', 'Invoice', 'Date', 'Amount', 'Status', 'Age (days)', 'Bracket']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        age = int(r[5] or 0)
        bracket = ('Current' if age <= 30 else
                   '31-60d'  if age <= 60 else
                   '61-90d'  if age <= 90 else '>90d')
        data.append([str(r[0]), str(r[1]), str(r[2]),
                     f"${float(r[3] or 0):.2f}", str(r[4]), str(age), bracket])
        col = (colors.HexColor('#ff6600') if age > 90 else
               colors.HexColor('#cc0000') if age > 60 else
               colors.HexColor('#ffaa00') if age > 30 else colors.black)
        ts_obj.add('TEXTCOLOR', (5, i), (6, i), col)
        if age > 60: ts_obj.add('FONTNAME', (5, i), (6, i), 'Helvetica-Bold')

    data.append(['TOTAL OVERDUE', '',  '',
                 f"${sum(float(r[3] or 0) for r in rows):.2f}", '', '', ''])
    _totrow(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.20, .14, .12, .12, .10, .10, .10]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Aging Invoices')


# ── REGISTRY ─────────────────────────────────────────────────────────────────

REPORTS = {
    'by_supplier':  ('Purchase by Supplier',     report_purchase_by_supplier),
    'vat_supplier': ('VAT by Supplier',           report_vat_by_supplier),
    'summary':      ('Total Purchase Summary',    report_total_purchase_summary),
    'profit':       ('Profit on Purchase',        report_profit_on_purchase),
    'aging':        ('Aging Invoices',            report_aging_invoices),
}

DESCRIPTIONS = {
    'by_supplier':  'All purchases listed per supplier with base, VAT, and TTC amounts + payment status.',
    'vat_supplier': 'Input VAT grouped by supplier — useful for VAT declarations.',
    'summary':      'Daily aggregate: # invoices, total HT, total VAT, total TTC.',
    'profit':       'Potential retail profit on purchased stock (cost vs. current retail price).',
    'aging':        'All PENDING (unpaid) invoices grouped by age bracket: Current / 31-60 / 61-90 / >90 days.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'by_supplier', 'from_date': first_of_month, 'to_date': today}
    btns = {};  refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(168,85,247,0.25);border:1px solid rgba(168,85,247,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#100d19; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('shopping_cart', size='1.5rem').classes('text-purple-400')
                    ui.label('Purchase Report Center').classes(
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
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left;'
                                      ' justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['by_supplier'][0])\
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
                            try: REPORTS[k][1](f, t)
                            except Exception as ex:
                                ui.notify(f'Error: {ex}', color='negative')
                                import traceback; traceback.print_exc()

                        ui.button('View Report', icon='visibility', on_click=_run)\
                          .props('unelevated color=purple')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('by_supplier', ''))\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('by_supplier')
    dlg.open()
