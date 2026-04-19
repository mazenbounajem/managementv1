"""
stock_reports.py
================
Print Special reports for Stock Operations module.

Reports:
  1. Operations Log           – all operations in date range
  2. Adjustment History       – manual adjustments, damage, stock count
  3. Stock Movement Summary   – net movement per product per day
  4. Current Stock Snapshot   – full product list with current stock
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
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#1a3a50')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f6ff')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#aaccdd')),
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
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a3a50')),
            Spacer(1, 6*mm)]


def _totrow(ts_obj, idx):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#0d2030'))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


def report_operations_log(fd, td):
    sql = """
        SELECT so.operation_date, u.username, so.operation_type,
               so.total_items, so.reference_number
        FROM stock_operations so
        JOIN users u ON u.id = so.user_id
        WHERE CONVERT(date, so.operation_date) >= ?
          AND CONVERT(date, so.operation_date) <= ?
        ORDER BY so.operation_date DESC
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No operations found.', color='warning'); return
    elements = _hdr('Stock Operations Log', fd, td)
    hdr = ['Date', 'User', 'Type', 'Items', 'Reference']
    data = [hdr]
    for r in rows:
        data.append([str(r[0])[:19], str(r[1]), str(r[2]), str(r[3] or 0), str(r[4] or '')])
    ts_obj = _ts()
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.25, .20, .20, .10, .25]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Operations Log')


def report_adjustment_history(fd, td):
    sql = """
        SELECT so.operation_date, u.username, so.operation_type,
               so.reference_number,
               COALESCE(p.product_name, soi.product_name, 'N/A') AS product,
               ISNULL(soi.adjusted_quantity, 0) AS qty_change,
               ISNULL(soi.reason, '') AS reason
        FROM stock_operations so
        JOIN users u ON u.id = so.user_id
        LEFT JOIN stock_operation_items soi ON soi.operation_id = so.id
        LEFT JOIN products p ON p.id = soi.product_id
        WHERE so.operation_type IN ('manual_adjustment','damage','stock_count','return')
          AND CONVERT(date, so.operation_date) >= ?
          AND CONVERT(date, so.operation_date) <= ?
        ORDER BY so.operation_date DESC
    """
    rows = _q(sql, (fd, td))
    if not rows:
        # Try without join if stock_operation_items doesn't exist
        sql2 = """
            SELECT operation_date, user_id, operation_type,
                   reference_number, 'N/A', 0, ''
            FROM stock_operations
            WHERE operation_type IN ('manual_adjustment','damage','stock_count','return')
              AND CONVERT(date, operation_date) >= ?
              AND CONVERT(date, operation_date) <= ?
            ORDER BY operation_date DESC
        """
        rows = _q(sql2, (fd, td))
    if not rows: ui.notify('No adjustments found.', color='warning'); return
    elements = _hdr('Stock Adjustment History', fd, td)
    hdr = ['Date', 'User', 'Type', 'Reference', 'Product', 'Qty Change', 'Reason']
    data = [hdr]
    ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        qty = int(r[5] or 0)
        data.append([str(r[0])[:19], str(r[1]), str(r[2]), str(r[3] or ''),
                     str(r[4] or ''), str(qty), str(r[6] or '')])
        col = colors.red if qty < 0 else colors.HexColor('#006600')
        ts_obj.add('TEXTCOLOR', (5, i), (5, i), col)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.16, .10, .12, .14, .16, .10, .20]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Adjustment History')


def report_stock_movement_summary(fd, td):
    """Combined sales out + purchases in, grouped by product + day."""
    sql = """
        SELECT CONVERT(varchar(10), s.sale_date, 23) AS dt,
               p.product_name,
               -SUM(si.quantity) AS movement,
               'Sale' AS tx_type
        FROM sale_items si
        INNER JOIN sales s ON s.id = si.sales_id
        INNER JOIN products p ON p.id = si.product_id
        WHERE CONVERT(date, s.sale_date) >= ? AND CONVERT(date, s.sale_date) <= ?
        GROUP BY CONVERT(varchar(10), s.sale_date, 23), p.product_name
        UNION ALL
        SELECT CONVERT(varchar(10), pu.purchase_date, 23),
               p.product_name,
               SUM(pi.quantity),
               'Purchase'
        FROM purchase_items pi
        INNER JOIN purchases pu ON pu.id = pi.purchase_id
        INNER JOIN products p ON p.id = pi.product_id
        WHERE CONVERT(date, pu.purchase_date) >= ? AND CONVERT(date, pu.purchase_date) <= ?
        GROUP BY CONVERT(varchar(10), pu.purchase_date, 23), p.product_name
        ORDER BY 1, 2
    """
    rows = _q(sql, (fd, td, fd, td))
    if not rows: ui.notify('No stock movements.', color='warning'); return
    elements = _hdr('Stock Movement Summary', fd, td)
    hdr = ['Date', 'Product', 'Movement', 'Type']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        qty = int(r[2] or 0)
        data.append([str(r[0]), str(r[1]), str(qty), str(r[3])])
        col = colors.red if qty < 0 else colors.HexColor('#006600')
        ts_obj.add('TEXTCOLOR', (2, i), (2, i), col)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.15, .50, .15, .15]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Stock Movement Summary')


def report_stock_snapshot(fd, td):
    sql = """
        SELECT p.product_name, c.category_name, s.name,
               p.stock_quantity, p.min_stock_level,
               CASE WHEN p.stock_quantity <= ISNULL(p.min_stock_level,0) THEN 'LOW' ELSE 'OK' END,
               p.cost_price,
               p.stock_quantity * p.cost_price AS stock_value
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        WHERE p.is_active = 1
        ORDER BY p.product_name
    """
    rows = _q(sql)
    if not rows: ui.notify('No products.', color='warning'); return
    elements = _hdr('Current Stock Snapshot', fd, td)
    hdr = ['Product', 'Category', 'Supplier', 'Stock', 'Min Level', 'Status', 'Cost', 'Value']
    data = [hdr];  ts_obj = _ts()
    for i, r in enumerate(rows, 1):
        status = str(r[5])
        data.append([str(r[0]), str(r[1] or ''), str(r[2] or ''),
                     str(r[3] or 0), str(r[4] or 0), status,
                     f"${float(r[6] or 0):.2f}", f"${float(r[7] or 0):.2f}"])
        if status == 'LOW':
            ts_obj.add('TEXTCOLOR', (5, i), (5, i), colors.red)
            ts_obj.add('FONTNAME',  (5, i), (5, i), 'Helvetica-Bold')
    data.append(['TOTAL', '', '', str(sum(int(r[3] or 0) for r in rows)), '', '', '',
                 f"${sum(float(r[7] or 0) for r in rows):.2f}"])
    _totrow(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.24, .11, .13, .08, .08, .08, .10, .12]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Stock Snapshot')


REPORTS = {
    'ops_log':    ('Operations Log',            report_operations_log),
    'adj_hist':   ('Adjustment History',        report_adjustment_history),
    'movement':   ('Stock Movement Summary',    report_stock_movement_summary),
    'snapshot':   ('Current Stock Snapshot',   report_stock_snapshot),
}

DESCRIPTIONS = {
    'ops_log':   'All stock operations (any type) logged in the selected period with user and reference.',
    'adj_hist':  'Only manual adjustments, damage, stock count, and return operations with quantity changes.',
    'movement':  'Combined sales (negative) and purchase (positive) movements per product per day.',
    'snapshot':  'Current stock level for all active products with cost valuation. Red = LOW stock.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'ops_log', 'from_date': first_of_month, 'to_date': today}
    btns = {};  refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(14,165,233,0.25);border:1px solid rgba(14,165,233,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#0d1520; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('warehouse', size='1.5rem').classes('text-sky-400')
                    ui.label('Stock Operations Report Center').classes(
                        'text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:250px; min-width:250px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-sky-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left;'
                                      ' justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['ops_log'][0])\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                            ui.input(value=first_of_month).props('type=date outlined dense dark color=cyan stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                            ui.input(value=today).props('type=date outlined dense dark color=cyan stack-label')\
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
                          .props('unelevated color=cyan')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('ops_log', ''))\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('ops_log')
    dlg.open()
