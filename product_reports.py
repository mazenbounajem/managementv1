"""
product_reports.py
==================
Print Special report suite for the Products module.

Reports:
  1. Product List         – all products with cost, price, stock, supplier
  2. Stock Transactions   – movement log (sales + purchases) for all or one product
  3. Low Stock Alert      – items at or below reorder point
  4. Price History        – purchase price evolution per product
  5. Profitability        – margin analysis across all active products
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
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#1a4e2d')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f8f2')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#aaaaaa')),
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
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a4e2d')),
            Spacer(1, 6*mm)]


def _total(ts_obj, idx):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#0d3320'))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


# ── Report 1: Product List ───────────────────────────────────────────────────

def report_product_list(fd, td):
    sql = """
        SELECT p.product_name, c.category_name, s.name,
               p.cost_price, p.price, p.price_ttc,
               p.stock_quantity, p.min_stock_level,
               CASE WHEN p.is_active = 1 THEN 'Yes' ELSE 'No' END
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        ORDER BY p.product_name
    """
    rows = _q(sql)
    if not rows:
        ui.notify('No products found.', color='warning'); return
    elements = _hdr('Complete Product List', fd, td)
    hdr = ['Product', 'Category', 'Supplier', 'Cost', 'Price HT', 'Price TTC',
           'Stock', 'Min Level', 'Active']
    data = [hdr]
    ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        stk = int(r[6] or 0);  mnl = int(r[7] or 0)
        data.append([str(r[0]), str(r[1] or ''), str(r[2] or ''),
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}",
                     f"${float(r[5] or 0):.2f}", str(stk), str(mnl), str(r[8])])
        if stk <= mnl:
            ts_obj.add('TEXTCOLOR', (6, i), (6, i), colors.red)
            ts_obj.add('FONTNAME',  (6, i), (6, i), 'Helvetica-Bold')
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.22, .11, .13, .08, .09, .09, .07, .07, .06]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements, landscape_mode=True), 'Product List')


# ── Report 2: Stock Transactions ─────────────────────────────────────────────

def report_stock_transactions(fd, td):
    sql = """
        SELECT p.product_name,
               'Sale' AS tx_type,
               CONVERT(varchar(10), s.sale_date, 23),
               s.invoice_number,
               -si.quantity,
               si.unit_price, si.total_price
        FROM sale_items si
        INNER JOIN sales    s ON s.id   = si.sales_id
        INNER JOIN products p ON p.id   = si.product_id
        WHERE CONVERT(date, s.sale_date) >= ? AND CONVERT(date, s.sale_date) <= ?
        UNION ALL
        SELECT p.product_name,
               'Purchase',
               CONVERT(varchar(10), pu.purchase_date, 23),
               pu.invoice_number,
               pi.quantity,
               pi.unit_cost, pi.total_cost
        FROM purchase_items pi
        INNER JOIN purchases pu ON pu.id   = pi.purchase_id
        INNER JOIN products  p  ON p.id    = pi.product_id
        WHERE CONVERT(date, pu.purchase_date) >= ? AND CONVERT(date, pu.purchase_date) <= ?
        ORDER BY 3, 1
    """
    rows = _q(sql, (fd, td, fd, td))
    if not rows:
        ui.notify('No transactions found.', color='warning'); return
    elements = _hdr('Stock Transactions Log', fd, td)
    hdr = ['Product', 'Type', 'Date', 'Reference', 'Qty', 'Unit Cost/Price', 'Total']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        qty = int(r[4] or 0)
        data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]),
                     str(qty), f"${float(r[5] or 0):.2f}", f"${float(r[6] or 0):.2f}"])
        col = colors.red if qty < 0 else colors.HexColor('#006600')
        ts_obj.add('TEXTCOLOR', (4, i), (4, i), col)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.25, .08, .10, .14, .07, .14, .12]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements, landscape_mode=True), 'Stock Transactions')


# ── Report 3: Low Stock Alert ─────────────────────────────────────────────────

def report_low_stock(fd, td):
    sql = """
        SELECT p.product_name, s.name, p.stock_quantity,
               p.min_stock_level,
               (ISNULL(p.min_stock_level,0) - p.stock_quantity) AS shortage,
               p.cost_price, p.price
        FROM products p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE p.stock_quantity <= ISNULL(p.min_stock_level, 0)
          AND p.is_active = 1
        ORDER BY shortage DESC
    """
    rows = _q(sql)
    if not rows:
        ui.notify('All products above reorder level!', color='positive'); return
    elements = _hdr('Low Stock Alert', fd, td)
    hdr = ['Product', 'Supplier', 'Avail Stock', 'Min Level', 'Shortage', 'Cost', 'Retail']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        data.append([str(r[0]), str(r[1] or 'N/A'), str(r[2]), str(r[3]),
                     str(r[4] or 0), f"${float(r[5] or 0):.2f}", f"${float(r[6] or 0):.2f}"])
        ts_obj.add('TEXTCOLOR', (4, i), (4, i), colors.red)
        ts_obj.add('FONTNAME',  (4, i), (4, i), 'Helvetica-Bold')
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.28, .16, .10, .10, .10, .12, .12]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements, landscape_mode=True), 'Low Stock Alert')


# ── Report 4: Price History ───────────────────────────────────────────────────

def report_price_history(fd, td):
    sql = """
        SELECT p.product_name, s.name,
               CONVERT(varchar(10), pu.purchase_date, 23),
               pu.invoice_number,
               pi.quantity, pi.unit_cost
        FROM purchase_items pi
        INNER JOIN purchases pu ON pu.id   = pi.purchase_id
        INNER JOIN products  p  ON p.id    = pi.product_id
        LEFT  JOIN suppliers s  ON s.id    = pu.supplier_id
        WHERE CONVERT(date, pu.purchase_date) >= ?
          AND CONVERT(date, pu.purchase_date) <= ?
        ORDER BY p.product_name, pu.purchase_date DESC
    """
    rows = _q(sql, (fd, td))
    if not rows:
        ui.notify('No purchase history found.', color='warning'); return
    elements = _hdr('Product Price History', fd, td)
    hdr = ['Product', 'Supplier', 'Date', 'Invoice', 'Qty', 'Unit Cost']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1] or ''), str(r[2]), str(r[3]),
                     str(r[4]), f"${float(r[5] or 0):.2f}"])
    avail = landscape(A4)[0] - 30*mm
    cw = [avail*w for w in [.30, .18, .12, .15, .08, .13]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(_ts())
    elements.append(t)
    _show(_build(elements, landscape_mode=True), 'Price History')


# ── Report 5: Profitability ───────────────────────────────────────────────────

def report_profitability(fd, td):
    sql = """
        SELECT p.product_name, s.name,
               p.cost_price, p.price,
               (p.price - p.cost_price) AS margin_abs,
               CASE WHEN p.price > 0
                    THEN (p.price - p.cost_price) / p.price * 100
                    ELSE 0 END AS margin_pct,
               p.stock_quantity,
               p.stock_quantity * p.cost_price AS stock_value
        FROM products p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE p.is_active = 1
        ORDER BY margin_pct DESC
    """
    rows = _q(sql)
    if not rows:
        ui.notify('No products.', color='warning'); return
    elements = _hdr('Product Profitability', fd, td)
    hdr = ['Product', 'Supplier', 'Cost', 'Price HT', 'Margin $', 'Margin %',
           'Stock Qty', 'Stock Value']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        pct = float(r[5] or 0)
        data.append([str(r[0]), str(r[1] or ''),
                     f"${float(r[2] or 0):.2f}", f"${float(r[3] or 0):.2f}",
                     f"${float(r[4] or 0):.2f}", f"{pct:.1f}%",
                     str(r[6]), f"${float(r[7] or 0):.2f}"])
        if pct < 0:
            ts_obj.add('TEXTCOLOR', (4, i), (5, i), colors.red)
    t_stk = sum(float(r[7] or 0) for r in rows)
    data.append(['TOTAL', '', '', '', '', '', str(sum(int(r[6] or 0) for r in rows)),
                 f"${t_stk:.2f}"])
    _total(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.24, .15, .09, .09, .09, .09, .09, .12]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements, landscape_mode=True), 'Product Profitability')


# ── REPORTS REGISTRY ─────────────────────────────────────────────────────────

REPORTS = {
    'product_list':    ('Product List',           report_product_list),
    'stock_tx':        ('Stock Transactions',     report_stock_transactions),
    'low_stock':       ('Low Stock Alert',        report_low_stock),
    'price_history':   ('Price History',          report_price_history),
    'profitability':   ('Profitability Report',   report_profitability),
}

DESCRIPTIONS = {
    'product_list':  'All products with category, supplier, cost, price, stock level. Red = below reorder.',
    'stock_tx':      'All sales (negative) and purchases (positive) movements for selected date range.',
    'low_stock':     'Items whose available stock is at or below their minimum reorder level.',
    'price_history': 'Historical purchase cost per product — useful to track price evolution.',
    'profitability': 'Current cost vs. retail price margin and stock valuation for active products.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'product_list', 'from_date': first_of_month, 'to_date': today}
    btns = {};  refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(34,197,94,0.25);border:1px solid rgba(34,197,94,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#0f190f; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);'
                    'border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('inventory_2', size='1.5rem').classes('text-green-400')
                    ui.label('Product Report Center').classes(
                        'text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:250px; min-width:250px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-green-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left;'
                                      ' justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['product_list'][0])\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-green-400 uppercase tracking-widest')
                            ui.input(value=first_of_month).props('type=date outlined dense dark color=green stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-green-400 uppercase tracking-widest')
                            ui.input(value=today).props('type=date outlined dense dark color=green stack-label')\
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
                          .props('unelevated color=green')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-green-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('product_list', ''))\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('product_list')
    dlg.open()
