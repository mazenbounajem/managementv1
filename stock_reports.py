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

    # Helper JS snippets
    # 1) Print via opening in new tab (more reliable than iframe printing)
    js_open_print = f"window.open('{data_url}', '_blank');"

    with ui.dialog() as d:
        with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
            with ui.row().classes('w-full justify-between items-center p-3'
                                  ' bg-gray-900 border-b border-white/10'):
                ui.label(title).classes('text-white font-bold text-lg')

                with ui.row().classes('items-center gap-3'):
                    ui.button('Open for Print', on_click=lambda: ui.run_javascript(js_open_print))\
                        .classes('bg-sky-600 text-white px-4 py-1 rounded text-sm')
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



def report_adjustment_cost_price(fd, td):
    sql = '''
        SELECT so.operation_date, so.reference_number, soi.product_name,
               ISNULL(p.cost_price, 0), ISNULL(p.price_ttc, ISNULL(p.price, 0)),
               CAST(soi.previous_quantity AS float),
               CAST(soi.adjusted_quantity AS float),
               CAST(soi.previous_quantity + soi.adjusted_quantity AS float)
        FROM stock_operation_items soi
        LEFT JOIN products p ON p.id = soi.product_id
        JOIN stock_operations so ON so.id = soi.operation_id
        WHERE CONVERT(date, so.operation_date) >= ?
          AND CONVERT(date, so.operation_date) <= ?
        ORDER BY so.operation_date DESC, soi.id ASC
    '''
    rows = _q(sql, (fd, td))
    if not rows:
        ui.notify('No adjustment history found for selected dates.', color='warning')
        return

    elements = []
    elements.extend(_hdr('Adjustment History (Cost, Price, Qty)', fd, td))

    hdr = ['Date', 'Ref', 'Product', 'Cost', 'Price', 'Qty Before', 'Qty Change', 'Qty After']
    data = [hdr]
    
    for r in rows:
        data.append([
            str(r[0])[:19], str(r[1] or ''), str(r[2] or ''),
            _fmt_num(r[3]), _fmt_num(r[4]),
            _fmt_qty(r[5]), _fmt_qty(r[6]), _fmt_qty(r[7])
        ])
        
    ts_obj = _ts()
    avail = landscape(A4)[0] - 30*mm
    cw = [avail*0.14, avail*0.12, avail*0.24, avail*0.10, avail*0.10, avail*0.10, avail*0.10, avail*0.10]
    
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    
    _show(_build(elements, landscape_mode=True), 'Adjustment History (Cost/Price)')

def report_ops_with_items_grouped_b64(fd, td):
    return report_ops_with_items_grouped(fd, td)

def report_ops_with_items_grouped(fd, td):
    """From-date to-date: show all operations with their items, grouped by reference_number."""
    ops_sql = """
        SELECT so.id, so.operation_date, u.username, so.operation_type, so.reference_number
        FROM stock_operations so
        JOIN users u ON u.id = so.user_id
        WHERE CONVERT(date, so.operation_date) >= ?
          AND CONVERT(date, so.operation_date) <= ?
        ORDER BY so.reference_number, so.operation_date, so.id
    """
    ops = _q(ops_sql, (fd, td))
    if not ops:
        ui.notify('No operations found for selected period.', color='warning')
        return

    op_ids = [r[0] for r in ops]
    placeholders = ','.join(['?'] * len(op_ids))
    items_sql = f"""
        SELECT soi.operation_id,
               soi.product_name,
               soi.barcode,
               CAST(soi.adjusted_quantity AS float) AS adjusted_quantity,
               ISNULL(p.cost_price,0) AS cost_price
        FROM stock_operation_items soi
        LEFT JOIN products p ON p.id = soi.product_id
        WHERE soi.operation_id IN ({placeholders})
        ORDER BY soi.operation_id
    """
    items_rows = []
    connection.contogetrows(items_sql, items_rows, op_ids)

    items_by_op = {}
    for ir in items_rows:
        opid = int(ir[0])
        items_by_op.setdefault(opid, []).append(ir[1:])

    elements = _hdr('Operations + Items by Reference', fd, td)
    hdr = ['Reference', 'Op Date', 'Type', 'Product', 'Barcode', 'Qty', 'Unit Cost', 'Cost Total']

    table_data = [hdr]
    grand_total = 0.0

    ref_groups = {}
    for (op_id, op_dt, username, op_type, refno) in ops:
        ref_key = str(refno or 'N/A')
        ref_groups.setdefault(ref_key, []).append((op_id, op_dt, username, op_type, refno))

    styles = _ts()

    for ref_key, ref_ops in ref_groups.items():
        ref_subtotal = 0.0
        table_data.append([ref_key, '', '', '----', '', '', '', ''])
        for (op_id, op_dt, username, op_type, refno) in ref_ops:
            op_items = items_by_op.get(int(op_id), [])
            if not op_items:
                # keep operation visible even if no items (requested: "with items", but this avoids missing ops)
                table_data.append([ref_key, str(op_dt)[:19], op_type, '(No items)', '', '0', _fmt_num(0), _fmt_num(0)])
                continue

            for (prod_name, barcode, adj_qty, cost_price) in op_items:
                qty = float(adj_qty or 0)
                cp = float(cost_price or 0)
                ct = qty * cp
                ref_subtotal += ct
                grand_total += ct
                table_data.append([
                    ref_key,
                    str(op_dt)[:19],
                    str(op_type or ''),
                    str(prod_name or ''),
                    str(barcode or ''),
                    _fmt_qty(qty),
                    _fmt_num(cp),
                    _fmt_num(ct),
                ])

        table_data.append([ref_key, '', '', 'SUBTOTAL', '', '', '', _fmt_num(ref_subtotal)])

    avail = A4[0] - 30*mm
    cw = [avail*0.16, avail*0.16, avail*0.12, avail*0.20, avail*0.12, avail*0.08, avail*0.10, avail*0.14]
    t = Table(table_data, colWidths=cw, repeatRows=1)
    t.setStyle(styles)
    elements.append(t)

    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph(f"Summation (all operations in period): <b>{_fmt_num(grand_total)}</b>", getSampleStyleSheet()['Normal']))
    _show(_build(elements, landscape_mode=False), 'Operations with Items (Grouped)')

REPORTS = {
    'ops_log':    ('Operations Log',            report_operations_log),
    'adj_hist':   ('Adjustment History',        report_adjustment_history),
    'movement':   ('Stock Movement Summary',    report_stock_movement_summary),
    'snapshot':   ('Current Stock Snapshot',   report_stock_snapshot),
    'ops_items': ('Operations + Items (By Reference)', report_ops_with_items_grouped),
}

DESCRIPTIONS = {
    'ops_log':   'All stock operations (any type) logged in the selected period with user and reference.',
    'adj_hist':  'Only manual adjustments, damage, stock count, and return operations with quantity changes.',
    'movement':  'Combined sales (negative) and purchase (positive) movements per product per day.',
    'snapshot':  'Current stock level for all active products with cost valuation. Red = LOW stock.',
}


def _fmt_num(x):
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return "0.00"


def _fmt_qty(x):
    try:
        f = float(x)
        # if integer-like, show no decimals
        if abs(f - int(f)) < 1e-9:
            return str(int(f))
        return f"{f:.3f}".rstrip('0').rstrip('.')
    except Exception:
        return "0"

def _fetch_cost_price(pid):
    # best effort: avoid failing report if cost_price is NULL
    rows = []
    connection.contogetrows("SELECT ISNULL(cost_price,0) FROM products WHERE id = ?", rows, [pid])
    return float(rows[0][0]) if rows else 0.0

def _build_table(elements, title, headers, rows, col_widths, landscape_mode=False, style_fn=None):
    elements.append(Paragraph(title, getSampleStyleSheet()['Heading2']))
    t = Table([headers] + rows, colWidths=col_widths, repeatRows=1)
    if style_fn:
        t.setStyle(style_fn())
    elements.append(t)
    if landscape_mode:
        # landscape is handled at the doc build level in _build; ignore here
        pass

def _ops_current_and_grouped_pdf(current_items, from_date, to_date):
    """Return base64 PDF for 2 reports shown in one PDF:
    1) Current operation (draft/current_items)
    2) All operations grouped by reference in [from_date,to_date] with totals.
    """
    elements = []
    elements.extend(_hdr('Stock Operations - Current & Grouped', from_date, to_date))

    # ---------- Report 1: current operation (items passed in) ----------
    elements.append(Paragraph("Report 1: Current Operation (Draft / Current Items)", getSampleStyleSheet()['Heading2']))

    # Header table columns
    hdr1 = ['Product', 'Barcode', 'Qty', 'Unit Cost', 'Cost Total']
    data1 = []
    grand_cost_1 = 0.0

    for it in (current_items or []):
        pid = it.get('product_id')
        cost_price = _fetch_cost_price(pid) if pid is not None else 0.0
        qty = float(it.get('quantity') or 0)
        cost_total = qty * cost_price
        grand_cost_1 += cost_total
        data1.append([
            str(it.get('product_name') or ''),
            str(it.get('barcode') or ''),
            _fmt_qty(qty),
            _fmt_num(cost_price),
            _fmt_num(cost_total)
        ])

    ts1 = TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#1a3a50')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f6ff')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#aaccdd')),
        ('FONTSIZE',       (0, 1), (-1, -1), 7.5),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 3),
        ('TOPPADDING',     (0, 0), (-1, -1), 3),
    ])
    t1 = Table(data1 and [hdr1] + data1 or [hdr1, ['','','','','']], colWidths=[
        A4[0]-30*mm * 0.35, A4[0]-30*mm * 0.20, A4[0]-30*mm * 0.10, A4[0]-30*mm * 0.15, A4[0]-30*mm * 0.20
    ], repeatRows=1)
    t1.setStyle(ts1)
    elements.append(Spacer(1, 4*mm))
    elements.append(t1)

    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph(f"Draft cost summation: <b>{_fmt_num(grand_cost_1)}</b>", getSampleStyleSheet()['Normal']))

    # ---------- Report 2: grouped operations by reference ----------
    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph("Report 2: All Operations (Grouped by Reference)", getSampleStyleSheet()['Heading2']))

    # Fetch ops in date range, grouped by reference_number; then items
    # NOTE: We include operation header rows and their item rows.
    ops_sql = """
        SELECT so.id, so.operation_date, u.username, so.operation_type, so.reference_number
        FROM stock_operations so
        JOIN users u ON u.id = so.user_id
        WHERE CONVERT(date, so.operation_date) >= ?
          AND CONVERT(date, so.operation_date) <= ?
        ORDER BY so.reference_number, so.operation_date, so.id
    """
    ops = _q(ops_sql, (from_date, to_date))
    if not ops:
        elements.append(Paragraph("No operations found in selected period.", getSampleStyleSheet()['Normal']))
        return _build(elements, landscape_mode=False)

    # Fetch all items for these ops (guard empty IN)
    op_ids = [r[0] for r in ops]
    if not op_ids:
        elements.append(Paragraph("No items found for operations in selected period.", getSampleStyleSheet()['Normal']))
        return _build(elements, landscape_mode=False)

    placeholders = ','.join(['?'] * len(op_ids))
    items_sql = f"""
        SELECT soi.operation_id,
               soi.product_name,
               soi.barcode,
               CAST(soi.adjusted_quantity AS float) AS adjusted_quantity,
               ISNULL(p.cost_price,0) AS cost_price
        FROM stock_operation_items soi
        LEFT JOIN products p ON p.id = soi.product_id
        WHERE soi.operation_id IN ({placeholders})
        ORDER BY soi.operation_id
    """
    items_rows = []
    connection.contogetrows(items_sql, items_rows, op_ids)

    # index items by operation_id
    items_by_op = {}
    for ir in items_rows:
        opid = int(ir[0])
        items_by_op.setdefault(opid, []).append(ir[1:])

    # Build per-reference report
    # Table layout: each operation header row plus item rows (simple approach).
    elements.append(Spacer(1, 2*mm))

    # reference groups
    ref_groups = {}
    for r in ops:
        op_id, op_dt, username, op_type, refno = r
        ref_key = str(refno or 'N/A')
        ref_groups.setdefault(ref_key, []).append(r)

    group_grand_total = 0.0
    styles = _ts()
    hdr = ['Ref', 'Op Date', 'Type', 'Item', 'Barcode', 'Qty', 'Unit Cost', 'Cost Total']
    elements.append(Spacer(1, 1*mm))

    table_data = [hdr]
    row_index = 1

    for ref_key, ref_ops in ref_groups.items():
        ref_subtotal = 0.0
        # Add a reference header row
        table_data.append([ref_key, '', '', '----', '', '', '', ''])
        row_index += 1

        for op in ref_ops:
            op_id, op_dt, username, op_type, refno = op
            op_date_str = str(op_dt)[:19]
            op_items = items_by_op.get(int(op_id), [])

            # (2) Operation header line before its items
            table_data.append([
                ref_key,
                op_date_str,
                str(op_type or ''),
                'OPERATION',
                f"ref:{str(refno or 'N/A')}",
                '',
                '',
                ''
            ])
            row_index += 1

            if not op_items:
                table_data.append([ref_key, '', '', '(no items)', '', '0', _fmt_num(0), _fmt_num(0)])
                row_index += 1
                continue

            for (prod_name, barcode, adj_qty, cost_price) in op_items:
                qty = float(adj_qty or 0)
                cp = float(cost_price or 0)
                ct = qty * cp
                ref_subtotal += ct
                group_grand_total += ct
                table_data.append([
                    ref_key,
                    '',
                    '',
                    str(prod_name or ''),
                    str(barcode or ''),
                    _fmt_qty(qty),
                    _fmt_num(cp),
                    _fmt_num(ct)
                ])
                row_index += 1

        table_data.append([ref_key, '', '', 'SUBTOTAL', '', '', '', _fmt_num(ref_subtotal)])
        row_index += 1

    # approximate column widths
    avail = A4[0] - 30*mm
    cw = [avail*0.14, avail*0.14, avail*0.12, avail*0.22, avail*0.12, avail*0.08, avail*0.10, avail*0.12]
    t2 = Table(table_data, colWidths=cw, repeatRows=1)
    t2.setStyle(styles)
    elements.append(t2)

    # grand total row
    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph(f"Grand cost summation (all grouped operations): <b>{_fmt_num(group_grand_total)}</b>", getSampleStyleSheet()['Normal']))

    return _build(elements, landscape_mode=False)

def open_print_current_and_grouped_dialog(current_items, operation_date, reference_number, from_date, to_date):
    # Keep existing defaults (operation_date -> single day, otherwise today)
    from_date_final = None
    to_date_final = None
    if from_date and to_date:
        from_date_final, to_date_final = from_date, to_date
    else:
        today = date.today().strftime('%Y-%m-%d')
        if operation_date:
            opd = str(operation_date).split(' ')[0].split('T')[0]
            from_date_final = opd
            to_date_final = opd
        else:
            from_date_final = today
            to_date_final = today

    state = {'from_date': from_date_final, 'to_date': to_date_final, 'report_type': 1}

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#0d1520; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style('background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('print', size='1.5rem').classes('text-sky-400')
                    ui.label('Stock Print Special').classes('text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes('bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                
                # Left panel: buttons
                with ui.column().classes('h-full p-6 gap-6 overflow-y-auto').style('width:360px; min-width:360px; background:rgba(255,255,255,0.03); border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes('text-[10px] font-black text-sky-400 uppercase tracking-widest mb-2')
                    
                    rep1_btn = ui.button('1) Adjustment (Cost, Price, Qty)', on_click=lambda: select_report(1)).props('unelevated').classes('w-full py-4 font-bold rounded-xl text-sm shadow-md transition-all').style('justify-content:flex-start;')
                    rep2_btn = ui.button('2) Cost Summation (By Ref & Date)', on_click=lambda: select_report(2)).props('unelevated').classes('w-full py-4 font-bold rounded-xl text-sm shadow-md transition-all mt-2').style('justify-content:flex-start;')

                    def select_report(num):
                        state['report_type'] = num
                        if num == 1:
                            rep1_btn.props('color=primary')
                            rep2_btn.props('color=grey-8')
                        else:
                            rep1_btn.props('color=grey-8')
                            rep2_btn.props('color=secondary')
                        
                    # initialize
                    select_report(1)

                    ui.separator().classes('bg-white/10 mt-4')
                    ui.label('Configure the dates on the right, then click View Report.').classes('text-gray-300 text-xs mt-2')

                # Right panel: from-to + view report button
                with ui.column().classes('flex-1 h-full p-6 gap-6 overflow-auto'):
                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                            ui.input(value=state['from_date']).props('type=date outlined dense dark color=cyan stack-label').classes('text-white font-bold w-48').on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                            ui.input(value=state['to_date']).props('type=date outlined dense dark color=cyan stack-label').classes('text-white font-bold w-48').on_value_change(lambda e: state.update({'to_date': e.value}))
                        
                        def cmd_view_report():
                            f, t = state['from_date'], state['to_date']
                            if not f or not t:
                                return ui.notify('Select dates', color='warning')
                            if f > t:
                                return ui.notify('From before To', color='warning')

                            if state['report_type'] == 1:
                                report_adjustment_cost_price(f, t)
                            else:
                                b64 = report_ops_with_items_grouped_b64(f, t)
                                if b64:
                                    _show(b64, 'Cost Summation Grouped')
                            # Keep the report-center dialog open (matches the Expenses/Category behavior).

                        ui.button('VIEW REPORT', icon='visibility', on_click=cmd_view_report).props('unelevated color=purple').classes('px-10 py-3 rounded-xl font-black text-sm uppercase tracking-widest self-end mb-1 shadow-lg')
    dlg.open()
