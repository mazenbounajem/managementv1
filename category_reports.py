from nicegui import ui
from datetime import date
from connection import connection

import base64
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def _q(sql, params=None):
    rows = []
    if params is not None:
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


def fetch_products_by_category(category_id: int):
    """
    Returns: barcode, product_name, stock_quantity, cost_price
    """
    sql = """
        SELECT
            ISNULL(p.barcode, '')               AS barcode,
            p.product_name                      AS product_name,
            ISNULL(p.stock_quantity, 0)       AS stock_quantity,
            ISNULL(p.cost_price, 0)           AS cost_price
        FROM products p
        WHERE p.category_id = ?
        ORDER BY p.product_name
    """
    return _q(sql, (category_id,))


def _base_doc(buffer, landscape_mode=False):
    ps = landscape(A4) if landscape_mode else A4
    return SimpleDocTemplate(
        buffer,
        pagesize=ps,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )


def _styles():
    s = getSampleStyleSheet()
    title = ParagraphStyle('RT', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    sub = ParagraphStyle('RS', parent=s['Normal'], fontSize=9, textColor=colors.grey, spaceAfter=8)
    return s, title, sub


def _header_ts():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d2d6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f8')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ])


def _total_row_style(ts, idx):
    ts.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#1a1a4e'))
    ts.add('TEXTCOLOR', (0, idx), (-1, idx), colors.yellow)
    ts.add('FONTNAME', (0, idx), (-1, idx), 'Helvetica-Bold')


def _build_pdf(elements, landscape_mode=False):
    buf = BytesIO()
    doc = _base_doc(buf, landscape_mode=landscape_mode)
    doc.build(elements)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def _show_pdf(b64: str, title='Report'):
    data_url = f"data:application/pdf;base64,{b64}"
    js_open_print = f"window.open('{data_url}', '_blank');"
    with ui.dialog() as d:
        with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
            with ui.row().classes('w-full justify-between items-center p-3 bg-gray-900 border-b border-white/10'):
                ui.label(title).classes('text-white font-bold text-lg')
                with ui.row().classes('items-center gap-3'):
                    ui.button('Open for Print', on_click=lambda: ui.run_javascript(js_open_print)) \
                        .classes('bg-sky-600 text-white px-4 py-1 rounded text-sm')
                    ui.button('X Close', on_click=d.close).classes('bg-red-600 hover:bg-red-700 text-white px-4 py-1 rounded text-sm')
            ui.html(
                f'<iframe src="{data_url}" width="100%" height="100%" style="border:none; min-height:calc(100vh - 56px);"></iframe>'
            ).classes('w-full flex-1')
    d.open()


def generate_category_cost_pdf(category_id: int):
    # Fetch category name for title
    cat_rows = _q("SELECT category_name FROM categories WHERE id = ?", (category_id,))
    category_name = cat_rows[0][0] if cat_rows else f"Category #{category_id}"

    rows = fetch_products_by_category(category_id)
    if not rows:
        ui.notify('No products in selected category.', color='warning')
        return

    _, title_s, sub_s = _styles()
    elements = []
    elements.append(Paragraph(f"{_company()} — Category Cost Report", title_s))
    elements.append(Paragraph(f"Category: {category_name}", sub_s))
    elements.append(Paragraph(f"Generated: {date.today().isoformat()}", sub_s))
    elements.append(Spacer(1, 4 * mm))

    hdr = ['Barcode', 'Product', 'Stock Qty', 'Cost Price', 'Total Cost (Cost×Qty)']
    data = [hdr]

    total_cost_sum = 0.0
    for barcode, product_name, stock_qty, cost_price in rows:
        stock_qty_f = float(stock_qty or 0)
        cost_price_f = float(cost_price or 0)
        line_cost = stock_qty_f * cost_price_f
        total_cost_sum += line_cost
        data.append([
            str(barcode or ''),
            str(product_name or ''),
            str(int(stock_qty_f)),
            f"${cost_price_f:.2f}",
            f"${line_cost:.2f}",
        ])

    data.append(['', 'TOTAL', '', '', f"${total_cost_sum:.2f}"])

    avail = landscape(A4)[0] - 30 * mm
    cw = [avail * 0.13, avail * 0.35, avail * 0.12, avail * 0.14, avail * 0.26]

    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts()
    _total_row_style(ts, len(data) - 1)
    t.setStyle(ts)

    elements.append(t)
    _show_pdf(_build_pdf(elements, landscape_mode=True), 'Category Cost Report')


def generate_sales_by_category_pdf(from_date: str, to_date: str):
    """
    Sales by category for the selected period.
    Shows: category, qty sold, invoice count, total revenue.
    """
    rows = _q(
        """
        SELECT
            ISNULL(c.category_name, 'Uncategorised') AS category_name,
            SUM(si.quantity)                            AS qty_sold,
            COUNT(DISTINCT s.id)                        AS invoice_count,
            SUM(ISNULL(si.total_price, 0))            AS total_revenue
        FROM sale_items si
        INNER JOIN sales s   ON s.id = si.sales_id
        INNER JOIN products p ON p.id = si.product_id
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE s.status = 'Sale'
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        GROUP BY c.category_name
        ORDER BY total_revenue DESC, category_name
        """,
        (from_date, to_date),
    )

    if not rows:
        ui.notify('No sales found for the selected period.', color='warning')
        return

    _, title_s, sub_s = _styles()
    elements = []
    elements.append(Paragraph(f"{_company()} — Sales by Category", title_s))
    elements.append(Paragraph(f"Period: {from_date} to {to_date}", sub_s))
    elements.append(Spacer(1, 4 * mm))

    hdr = ['Category', 'Qty Sold', 'Invoices', 'Total Revenue']
    data = [hdr]

    total_invoices = 0
    total_rev = 0.0

    for cat_name, qty_sold, invoice_count, total_revenue in rows:
        q = float(qty_sold or 0)
        inv_cnt = int(invoice_count or 0)
        rev = float(total_revenue or 0)

        total_invoices += inv_cnt
        total_rev += rev

        data.append([
            str(cat_name or 'Uncategorised'),
            str(int(q)) if abs(q - int(q)) < 1e-9 else f"{q:.3f}".rstrip('0').rstrip('.'),
            str(inv_cnt),
            f"${rev:.2f}",
        ])

    data.append(['', 'TOTAL', str(total_invoices), f"${total_rev:.2f}"])

    avail = landscape(A4)[0] - 30 * mm
    cw = [avail * 0.45, avail * 0.16, avail * 0.16, avail * 0.23]

    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts()
    _total_row_style(ts, len(data) - 1)
    t.setStyle(ts)

    elements.append(t)
    _show_pdf(_build_pdf(elements, landscape_mode=True), 'Sales by Category')


def open_print_special_dialog(category_id=None):
    """
    Category page "Special Print" entry point.
    Supports:
      - Cost report for selected category
      - Sales-by-category for any date range (ignores category_id)
    """
    today = date.today().strftime('%Y-%m-%d')

    state = {
        'report_key': 'cost',
        'from_date': today,
        'to_date': today,
    }

    REPORTS = {
        'cost': (
            'Category Cost (Cost×Stock)',
            'Prints per-product cost×stock valuation for the selected category.'
        ),
        'sales_by_category': (
            'Sales by Category',
            'Shows each category and its sales totals (qty sold, invoice count, total revenue) for the selected period.'
        ),
    }

    btns = {}
    refs = {}

    def select(key: str):
        state['report_key'] = key
        for k, b in btns.items():
            sty = (
                'background:rgba(168,85,247,0.25);border:1px solid rgba(168,85,247,0.55);'
                if k == key else 'background:rgba(255,255,255,0.04);border:none;'
            )
            b.style(sty)

        if 'n' in refs:
            refs['n'].text = REPORTS[key][0]
        if 'd' in refs:
            refs['d'].text = REPORTS[key][1]

        # Toggle input visibility based on report
        if 'category_inputs' in refs:
            refs['category_inputs'].set_visibility(key == 'cost')
        if 'date_inputs' in refs:
            refs['date_inputs'].set_visibility(key == 'sales_by_category')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')

        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#120818; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'
            ):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('receipt_long', size='1.5rem').classes('text-purple-400')
                    ui.label('Category Report Center').classes('text-white font-black text-xl').style(
                        'font-family:"Outfit",sans-serif;'
                    )
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold'
                )

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                # Left panel
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                    'width:360px; min-width:360px; background:rgba(255,255,255,0.03);'
                    'border-right:1px solid rgba(255,255,255,0.08);'
                ):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-purple-400 uppercase tracking-widest mb-2'
                    )

                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k)) \
                            .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white') \
                            .style('background:rgba(255,255,255,0.04); text-align:left; justify-content:flex-start;')
                        btns[k] = b

                    ui.separator().classes('bg-white/10 mt-4')

                # Right panel
                with ui.column().classes('flex-1 p-6 gap-4 overflow-y-auto').style(
                    'background:#120818;'
                ):
                    ui.label('REPORT DETAILS').classes(
                        'text-[10px] font-black text-purple-400 uppercase tracking-widest'
                    )

                    refs['n'] = ui.label(REPORTS[state['report_key']][0]).classes('text-white text-2xl font-black')
                    refs['d'] = ui.label(REPORTS[state['report_key']][1]).classes('text-gray-400 text-sm')

                    # Report-specific inputs
                    with ui.card().classes('w-full p-4').style('background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);'):
                        # Category inputs (we just display selected id/name and validate)
                        refs['category_inputs'] = ui.column().classes('gap-3')
                        refs['date_inputs'] = ui.column().classes('gap-3')

                        # category input (no .add(); create directly inside the column context)
                        with refs['category_inputs']:
                            ui.label('Selected Category').classes('text-gray-300 text-sm font-bold')
                            refs['category_id_label'] = ui.label(
                                f'{category_id}' if category_id is not None else '(none selected)'
                            ).classes('text-white text-lg font-black')

                        # date inputs (for sales_by_category)
                        with refs['date_inputs']:
                            ui.label('From Date').classes('text-gray-300 text-sm font-bold')
                            refs['from_date'] = ui.input(value=state['from_date']).props('outlined dense').classes('w-full')
                            ui.label('To Date').classes('text-gray-300 text-sm font-bold mt-2')
                            refs['to_date'] = ui.input(value=state['to_date']).props('outlined dense').classes('w-full')

                    # Action buttons
                    with ui.row().classes('w-full justify-between items-center gap-4 mt-2'):
                        ui.button(
                            'Close',
                            on_click=dlg.close
                        ).classes('bg-white/10 text-white px-4 py-2 rounded-lg')

                        def _run_report():
                            key = state['report_key']
                            try:
                                if key == 'cost':
                                    if category_id is None:
                                        ui.notify('Select a category first.', color='negative')
                                        return
                                    generate_category_cost_pdf(int(category_id))
                                elif key == 'sales_by_category':
                                    from_d = refs['from_date'].value
                                    to_d = refs['to_date'].value
                                    if not from_d or not to_d:
                                        ui.notify('From/To date required.', color='negative')
                                        return
                                    generate_sales_by_category_pdf(from_d, to_d)
                                else:
                                    ui.notify('Unknown report type.', color='negative')
                            except Exception as e:
                                ui.notify(f'Error generating report: {e}', color='negative')
                            finally:
                                # keep dialog open so user can switch report type
                                pass

                        ui.button(
                            'Generate / Open PDF',
                            on_click=_run_report
                        ).classes('bg-sky-600 text-white px-6 py-3 rounded-xl font-bold')

        # initial selection visuals + open
        select(state['report_key'])
        dlg.open()
