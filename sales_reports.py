"""
sales_reports.py
================
Complete Sales Report Suite  (Print Special dialog + PDF generation).

Reports available:
  1. Daily Sales Detail       – per-day invoice lines, qty, price, VAT
  2. Global Daily Sales       – per-day aggregate HT / VAT / TTC
  3. Daily Product Sales      – product + supplier + reorder + avg monthly suggestion
  4. Average Monthly Sales    – per-item avg qty & revenue per month
  5. Sales by Supplier        – revenue grouped by supplier
  6. Profit Analysis          – invoice-level profit & margin
  7. Invoice Receipt          – compact thermal-style receipt (single invoice)
"""

from nicegui import ui
from datetime import datetime, date
from connection import connection
import base64
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


# ==============================================================================
#  DB helpers
# ==============================================================================

def _q(sql, params=None):
    rows = []
    if params:
        connection.contogetrows(sql, rows, params)
    else:
        connection.contogetrows(sql, rows)
    return rows


def _company():
    try:
        info = connection.get_company_info()
        return info.get('company_name', 'Company') if info else 'Company'
    except Exception:
        return 'Company'


# ==============================================================================
#  DATA FETCHERS
# ==============================================================================

def fetch_daily_sales_detail(from_date, to_date):
    sql = """
        SELECT
            CONVERT(varchar(10), s.sale_date, 23) AS sale_date,
            s.invoice_number,
            c.customer_name,
            p.product_name,
            si.quantity,
            si.unit_price,
            ISNULL(si.vat_percentage, 0) AS vat_pct,
            ISNULL(si.vat_amount,     0) AS vat_amt,
            si.total_price
        FROM sale_items si
        INNER JOIN sales     s   ON s.id  = si.sales_id
        INNER JOIN customers c   ON c.id  = s.customer_id
        INNER JOIN products  p   ON p.id  = si.product_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        ORDER BY s.sale_date, s.invoice_number, p.product_name
    """
    return _q(sql, (from_date, to_date))


def fetch_global_daily_sales(from_date, to_date):
    sql = """
        SELECT
            CONVERT(varchar(10), s.sale_date, 23) AS sale_date,
            COUNT(DISTINCT s.id)              AS invoice_count,
            SUM(ISNULL(s.subtotal, 0))        AS total_ht,
            SUM(ISNULL(s.total_vat, 0))       AS total_vat,
            SUM(ISNULL(s.total_amount, 0))    AS total_ttc
        FROM sales s
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY CONVERT(varchar(10), s.sale_date, 23)
        ORDER BY sale_date
    """
    return _q(sql, (from_date, to_date))


def fetch_daily_product_sales(from_date, to_date):
    """
    Fixed: removed si.unit_price from GROUP BY (causes non-determinism);
    uses AVG(si.unit_price) instead and adds avg_monthly_order suggestion.
    """
    sql = """
        WITH sale_months AS (
            SELECT
                si.product_id,
                COUNT(DISTINCT YEAR(s.sale_date)*100 + MONTH(s.sale_date)) AS months_active,
                SUM(si.quantity) AS total_qty_period
            FROM sale_items si
            INNER JOIN sales s ON s.id = si.sales_id
            WHERE s.status = 'Sale'
              AND CONVERT(date, s.sale_date) >= ?
              AND CONVERT(date, s.sale_date) <= ?
            GROUP BY si.product_id
        )
        SELECT
            CONVERT(varchar(10), s.sale_date, 23)  AS sale_date,
            p.product_name,
            ISNULL(sup.name, 'N/A')                AS supplier,
            SUM(si.quantity)                       AS qty_sold,
            AVG(si.unit_price)                     AS avg_unit_price,
            SUM(si.total_price)                    AS subtotal,
            p.stock_quantity                       AS stock_avail,
            ISNULL(p.min_stock_level, 0)           AS reorder_point,
            CASE WHEN p.stock_quantity <= ISNULL(p.min_stock_level, 0)
                 THEN 'YES' ELSE 'no' END          AS to_order,
            CASE WHEN sm.months_active > 0
                 THEN CEILING(CAST(sm.total_qty_period AS float)
                              / sm.months_active * 1.2)
                 ELSE 0 END                        AS suggested_order_qty
        FROM sale_items si
        INNER JOIN sales    s   ON s.id   = si.sales_id
        INNER JOIN products p   ON p.id   = si.product_id
        LEFT  JOIN suppliers sup ON sup.id = p.supplier_id
        LEFT  JOIN sale_months sm ON sm.product_id = p.id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY
            CONVERT(varchar(10), s.sale_date, 23),
            p.product_name, sup.name,
            p.stock_quantity, p.min_stock_level,
            sm.months_active, sm.total_qty_period
        ORDER BY sale_date, p.product_name
    """
    return _q(sql, (from_date, to_date, from_date, to_date))


def fetch_avg_monthly_sales(from_date, to_date):
    sql = """
        SELECT
            p.product_name,
            ISNULL(sup.name, 'N/A') AS supplier,
            COUNT(DISTINCT YEAR(s.sale_date)*100 + MONTH(s.sale_date)) AS months_active,
            SUM(si.quantity)        AS total_qty,
            CAST(SUM(si.quantity) AS float)
              / NULLIF(COUNT(DISTINCT YEAR(s.sale_date)*100 + MONTH(s.sale_date)),0)
                                    AS avg_qty_month,
            SUM(si.total_price)     AS total_revenue,
            SUM(si.total_price)
              / NULLIF(COUNT(DISTINCT YEAR(s.sale_date)*100 + MONTH(s.sale_date)),0)
                                    AS avg_rev_month
        FROM sale_items si
        INNER JOIN sales    s   ON s.id   = si.sales_id
        INNER JOIN products p   ON p.id   = si.product_id
        LEFT  JOIN suppliers sup ON sup.id = p.supplier_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY p.product_name, sup.name
        ORDER BY total_revenue DESC
    """
    return _q(sql, (from_date, to_date))


def fetch_sales_by_supplier(from_date, to_date):
    sql = """
        SELECT
            ISNULL(sup.name, 'No Supplier') AS supplier,
            p.product_name,
            SUM(si.quantity)                AS total_qty,
            SUM(si.total_price)             AS total_revenue
        FROM sale_items si
        INNER JOIN sales    s   ON s.id   = si.sales_id
        INNER JOIN products p   ON p.id   = si.product_id
        LEFT  JOIN suppliers sup ON sup.id = p.supplier_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY sup.name, p.product_name
        ORDER BY supplier, total_revenue DESC
    """
    return _q(sql, (from_date, to_date))


def fetch_profit_report(from_date, to_date):
    sql = """
        SELECT
            s.invoice_number,
            CONVERT(varchar(10), s.sale_date, 23) AS sale_date,
            c.customer_name,
            s.total_amount                         AS total_ttc,
            SUM(si.quantity * ISNULL(p.cost_price, 0)) AS total_cost,
            s.total_amount
              - SUM(si.quantity * ISNULL(p.cost_price, 0)) AS profit,
            CASE WHEN s.total_amount > 0
                 THEN (s.total_amount
                       - SUM(si.quantity * ISNULL(p.cost_price, 0)))
                      / s.total_amount * 100
                 ELSE 0 END AS profit_pct
        FROM sales s
        INNER JOIN customers  c  ON c.id       = s.customer_id
        INNER JOIN sale_items si ON si.sales_id = s.id
        INNER JOIN products   p  ON p.id        = si.product_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY s.invoice_number, s.sale_date, c.customer_name, s.total_amount
        ORDER BY s.sale_date, s.invoice_number
    """
    return _q(sql, (from_date, to_date))


# ==============================================================================
#  PDF HELPERS
# ==============================================================================

def _base_doc(buffer, landscape_mode=False):
    ps = landscape(A4) if landscape_mode else A4
    return SimpleDocTemplate(buffer, pagesize=ps,
                             leftMargin=15*mm, rightMargin=15*mm,
                             topMargin=15*mm, bottomMargin=15*mm)


def _styles():
    s = getSampleStyleSheet()
    title = ParagraphStyle('RT', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    sub   = ParagraphStyle('RS', parent=s['Normal'],   fontSize=9,
                           textColor=colors.grey, spaceAfter=8)
    return s, title, sub


def _header_ts():
    return TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#2d2d6b')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f8')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('FONTSIZE',       (0, 1), (-1, -1), 7.5),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',     (0, 0), (-1, -1), 4),
    ])


def _build_pdf(elements, landscape_mode=False):
    buf = BytesIO()
    doc = _base_doc(buf, landscape_mode)
    doc.build(elements)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def _show_pdf(b64: str, title='Report'):
    data_url = f"data:application/pdf;base64,{b64}"
    with ui.dialog() as d:
        with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
            with ui.row().classes('w-full justify-between items-center p-3'
                                  ' bg-gray-900 border-b border-white/10'):
                ui.label(title).classes('text-white font-bold text-lg')
                ui.button('X Close', on_click=d.close).classes(
                    'bg-red-600 hover:bg-red-700 text-white px-4 py-1 rounded text-sm')
            ui.html(
                f'<iframe src="{data_url}" width="100%" height="100%"'
                ' style="border:none; min-height:calc(100vh - 56px);"></iframe>'
            ).classes('w-full flex-1')
    d.open()


def _total_row_style(ts, idx):
    ts.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#1a1a4e'))
    ts.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


def _std_header(report_name, from_date, to_date):
    _, title_s, sub_s = _styles()
    return [
        Paragraph(f"{_company()} — {report_name}", title_s),
        Paragraph(f"Period: {from_date}  to  {to_date}", sub_s),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2d2d6b')),
        Spacer(1, 6*mm),
    ]


# ==============================================================================
#  INDIVIDUAL PDF BUILDERS
# ==============================================================================

def generate_daily_detail_pdf(from_date, to_date):
    rows = fetch_daily_sales_detail(from_date, to_date)
    if not rows:
        ui.notify('No data for selected period.', color='warning'); return
    elements = _std_header('Daily Sales Detail', from_date, to_date)
    hdr = ['Date', 'Invoice', 'Customer', 'Product', 'Qty',
           'Unit Price', 'VAT %', 'VAT Amt', 'Subtotal']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]),
                     str(r[4]), f"${float(r[5] or 0):.2f}",
                     f"{float(r[6] or 0):.1f}%",
                     f"${float(r[7] or 0):.2f}",
                     f"${float(r[8] or 0):.2f}"])
    t_sub = sum(float(r[8] or 0) for r in rows)
    t_vat = sum(float(r[7] or 0) for r in rows)
    data.append(['', '', '', 'TOTAL', '', '', '', f"${t_vat:.2f}", f"${t_sub:.2f}"])
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.08, .10, .13, .17, .05, .09, .07, .09, .10]]
    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts();  _total_row_style(ts, len(data)-1);  t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements, landscape_mode=True), 'Daily Sales Detail')


def generate_global_daily_pdf(from_date, to_date):
    rows = fetch_global_daily_sales(from_date, to_date)
    if not rows:
        ui.notify('No data for selected period.', color='warning'); return
    elements = _std_header('Global Daily Sales Summary', from_date, to_date)
    hdr = ['Date', '# Invoices', 'Total HT', 'Total VAT', 'Total TTC']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), f"${float(r[2] or 0):.2f}",
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}"])
    data.append(['TOTAL',
                 str(sum(int(r[1]) for r in rows)),
                 f"${sum(float(r[2] or 0) for r in rows):.2f}",
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}"])
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.20, .15, .22, .22, .22]]
    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts();  _total_row_style(ts, len(data)-1);  t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements), 'Global Daily Sales')


def generate_daily_product_pdf(from_date, to_date):
    """Fixed: no unit_price in GROUP BY; includes avg monthly suggestion."""
    rows = fetch_daily_product_sales(from_date, to_date)
    if not rows:
        ui.notify('No data for selected period.', color='warning'); return
    elements = _std_header('Daily Product Sales', from_date, to_date)
    hdr = ['Date', 'Product', 'Supplier', 'Qty Sold', 'Avg Price',
           'Subtotal', 'Avail Stock', 'Reorder Pt', 'To Order?', 'Sug. Order Qty']
    data = [hdr]
    ts = _header_ts()
    for i, r in enumerate(rows, 1):
        to_order = str(r[8])
        row = [str(r[0]), str(r[1]), str(r[2]),
               str(r[3]), f"${float(r[4] or 0):.2f}",
               f"${float(r[5] or 0):.2f}",
               str(r[6]), str(r[7]), to_order, str(r[9])]
        data.append(row)
        if to_order == 'YES':
            ts.add('TEXTCOLOR', (8, i), (8, i), colors.red)
            ts.add('FONTNAME',  (8, i), (8, i), 'Helvetica-Bold')
    data.append(['', 'TOTAL', '', str(sum(int(r[3]) for r in rows)),
                 '', f"${sum(float(r[5] or 0) for r in rows):.2f}",
                 '', '', '', ''])
    _total_row_style(ts, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.08, .14, .11, .06, .07, .08, .07, .07, .07, .08]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements, landscape_mode=True), 'Daily Product Sales')


def generate_avg_monthly_pdf(from_date, to_date):
    rows = fetch_avg_monthly_sales(from_date, to_date)
    if not rows:
        ui.notify('No data for selected period.', color='warning'); return
    elements = _std_header('Average Monthly Sales per Item', from_date, to_date)
    hdr = ['Product', 'Supplier', 'Months', 'Total Qty',
           'Avg Qty/Month', 'Total Revenue', 'Avg Rev/Month']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]),
                     f"{float(r[4] or 0):.1f}",
                     f"${float(r[5] or 0):.2f}",
                     f"${float(r[6] or 0):.2f}"])
    data.append(['TOTAL', '', '', str(sum(int(r[3]) for r in rows)), '',
                 f"${sum(float(r[5] or 0) for r in rows):.2f}", ''])
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.25, .15, .08, .09, .13, .15, .15]]
    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts();  _total_row_style(ts, len(data)-1);  t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements), 'Average Monthly Sales')


def generate_sales_by_supplier_pdf(from_date, to_date):
    rows = fetch_sales_by_supplier(from_date, to_date)
    if not rows:
        ui.notify('No data for selected period.', color='warning'); return
    elements = _std_header('Sales by Supplier', from_date, to_date)
    hdr = ['Supplier', 'Product', 'Total Qty', 'Total Revenue']
    data = [hdr];   ts = _header_ts()
    current_sup = None;   sup_start = 1
    for i, r in enumerate(rows, 1):
        if r[0] != current_sup:
            if current_sup is not None:
                ts.add('BACKGROUND', (0, i-1), (-1, i-1), colors.HexColor('#dde8ff'))
            current_sup = r[0]
        data.append([str(r[0]), str(r[1]), str(r[2]), f"${float(r[3] or 0):.2f}"])
    data.append(['GRAND TOTAL', '', str(sum(int(r[2]) for r in rows)),
                 f"${sum(float(r[3] or 0) for r in rows):.2f}"])
    _total_row_style(ts, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.30, .40, .15, .15]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements), 'Sales by Supplier')


def generate_profit_pdf(from_date, to_date):
    rows = fetch_profit_report(from_date, to_date)
    if not rows:
        ui.notify('No data for selected period.', color='warning'); return
    elements = _std_header('Profit Analysis', from_date, to_date)
    hdr = ['Invoice', 'Date', 'Customer', 'TTC', 'Cost', 'Profit', 'Margin %']
    data = [hdr];  ts = _header_ts()
    for i, r in enumerate(rows, 1):
        pct = float(r[6] or 0)
        data.append([str(r[0]), str(r[1]), str(r[2]),
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}",
                     f"${float(r[5] or 0):.2f}", f"{pct:.1f}%"])
        if pct < 0:
            ts.add('TEXTCOLOR', (5, i), (6, i), colors.red)
    t_rev  = sum(float(r[3] or 0) for r in rows)
    t_cost = sum(float(r[4] or 0) for r in rows)
    t_prof = sum(float(r[5] or 0) for r in rows)
    t_marg = (t_prof / t_rev * 100) if t_rev else 0
    data.append(['TOTAL', '', '', f"${t_rev:.2f}", f"${t_cost:.2f}",
                 f"${t_prof:.2f}", f"{t_marg:.1f}%"])
    _total_row_style(ts, len(data)-1)
    avail = landscape(A4)[0] - 30*mm
    cw = [avail*w for w in [.12, .09, .18, .12, .12, .12, .11]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements, landscape_mode=True), 'Profit Analysis')


def generate_invoice_receipt_pdf(from_date, to_date):
    """
    Compact receipt-style report listing all invoices in period,
    intended to be printed on an 80mm receipt printer.
    """
    sql = """
        SELECT s.invoice_number,
               CONVERT(varchar(10), s.sale_date, 23),
               c.customer_name,
               s.subtotal, s.total_vat, s.total_amount
        FROM sales s
        INNER JOIN customers c ON c.id = s.customer_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        ORDER BY s.sale_date, s.invoice_number
    """
    rows = _q(sql, (from_date, to_date))
    if not rows:
        ui.notify('No invoices in selected period.', color='warning'); return

    company = _company()
    _, title_s, sub_s = _styles()
    receipt_style = ParagraphStyle('rec', fontSize=7, leading=9)
    receipt_title = ParagraphStyle('recT', fontSize=9, fontName='Helvetica-Bold',
                                   alignment=1, spaceAfter=2)
    elements = []
    for r in rows:
        inv, dt_, cust, ht, vat, ttc = (str(r[0]), str(r[1]), str(r[2]),
                                          float(r[3] or 0), float(r[4] or 0),
                                          float(r[5] or 0))
        elements.append(Paragraph(company, receipt_title))
        elements.append(Paragraph(f"Invoice: {inv}  |  {dt_}", receipt_style))
        elements.append(Paragraph(f"Client: {cust}", receipt_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Paragraph(f"Base (HT): ${ht:.2f}", receipt_style))
        elements.append(Paragraph(f"VAT:       ${vat:.2f}", receipt_style))
        elements.append(Paragraph(f"TOTAL TTC: ${ttc:.2f}", receipt_style))
        elements.append(HRFlowable(width="100%", thickness=1.0, color=colors.black))
        elements.append(Spacer(1, 4*mm))

    _show_pdf(_build_pdf(elements), 'Invoice Receipts')


# ==============================================================================
#  PRINT SPECIAL DIALOG  (the main entry point called from salesui)
# ==============================================================================

REPORTS = {
    'daily_detail':    ('Daily Sales Detail',       generate_daily_detail_pdf),
    'global_daily':    ('Global Daily Sales',       generate_global_daily_pdf),
    'product_sales':   ('Daily Product Sales',      generate_daily_product_pdf),
    'avg_monthly':     ('Average Monthly Sales',    generate_avg_monthly_pdf),
    'by_supplier':     ('Sales by Supplier',        generate_sales_by_supplier_pdf),
    'profit':          ('Profit Analysis',          generate_profit_pdf),
    'receipt':         ('Invoice Receipts',         generate_invoice_receipt_pdf),
}

DESCRIPTIONS = {
    'daily_detail':  'All invoice lines per day: product, qty, unit price, VAT%, VAT amount, subtotal.',
    'global_daily':  'One row per day: invoice count, total HT, total VAT, total TTC.',
    'product_sales': ('Per-day product breakdown with supplier, available stock, reorder point, '
                      '"To Order?" flag, and suggested order qty based on 1.2× average monthly sales.'),
    'avg_monthly':   'Per-item average quantity and revenue per active month in the selected period.',
    'by_supplier':   'Revenue and quantity grouped by the supplier that manufactures/imports each product.',
    'profit':        'Per-invoice: TTC, estimated cost, profit $, and margin %. Grand total row at bottom.',
    'receipt':       'Compact receipt-format listing all invoices in the period — suitable for receipt printer.',
}


def open_print_special_dialog():
    """Open the full-screen Print Special report center."""
    today           = date.today().strftime('%Y-%m-%d')
    first_of_month  = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {
        'report_key': 'daily_detail',
        'from_date':  first_of_month,
        'to_date':    today,
    }
    report_buttons = {}
    ui_refs        = {}

    def select_report(key):
        state['report_key'] = key
        for k, b in report_buttons.items():
            if k == key:
                b.style('background:rgba(139,92,246,0.25); border:1px solid rgba(139,92,246,0.5);')
            else:
                b.style('background:rgba(255,255,255,0.04); border:none;')
        if 'name_label' in ui_refs:
            ui_refs['name_label'].text = REPORTS[key][0]
        if 'desc_label' in ui_refs:
            ui_refs['desc_label'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#0f0f19; border-radius:0;'):

            # Title bar
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);'
                    'border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('print', size='1.5rem').classes('text-purple-400')
                    ui.label('Sales Report Center').classes(
                        'text-white font-black text-xl').style(
                        'font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 hover:bg-red-600 text-white px-4 py-1 rounded-lg text-sm font-bold')

            # Body
            with ui.row().classes('w-full gap-0 overflow-hidden').style(
                    'height:calc(100vh - 56px);'):

                # LEFT sidebar
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:260px; min-width:260px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-purple-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _fn) in REPORTS.items():
                        btn = ui.button(lbl, on_click=lambda k=k: select_report(k))\
                                 .classes('w-full px-4 py-3 rounded-xl text-sm font-bold'
                                          ' text-white transition-all')\
                                 .style('background:rgba(255,255,255,0.04);'
                                        'text-align:left; justify-content:flex-start;')
                        report_buttons[k] = btn

                # RIGHT content
                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    name_label = ui.label(REPORTS['daily_detail'][0])\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')
                    ui_refs['name_label'] = name_label

                    # Date + view row
                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM DATE').classes(
                                'text-[9px] font-black text-purple-400 uppercase tracking-widest')
                            ui.input(value=first_of_month)\
                               .props('type=date outlined dense dark color=purple stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))

                        with ui.column().classes('gap-1'):
                            ui.label('TO DATE').classes(
                                'text-[9px] font-black text-purple-400 uppercase tracking-widest')
                            ui.input(value=today)\
                               .props('type=date outlined dense dark color=purple stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'to_date': e.value}))

                        def _run():
                            key = state['report_key']
                            f, t = state['from_date'], state['to_date']
                            if not f or not t:
                                ui.notify('Select dates.', color='warning'); return
                            if f > t:
                                ui.notify('From must be before To.', color='negative'); return
                            _, fn = REPORTS[key]
                            try:
                                fn(f, t)
                            except Exception as ex:
                                ui.notify(f'Error: {ex}', color='negative')
                                import traceback; traceback.print_exc()

                        ui.button('View Report', icon='visibility', on_click=_run)\
                          .props('unelevated color=purple')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm'
                                   ' uppercase tracking-widest shadow-xl')

                    with ui.column().classes('w-full glass p-5 rounded-2xl'
                                            ' border border-white/10 gap-2'):
                        ui.label('REPORT DESCRIPTION').classes(
                            'text-[9px] font-black text-purple-400 uppercase tracking-widest')
                        desc_label = ui.label(DESCRIPTIONS.get('daily_detail', ''))\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')
                        ui_refs['desc_label'] = desc_label

        select_report('daily_detail')

    dlg.open()
