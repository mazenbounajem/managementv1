"""
sales_return_reports.py
=======================
Complete Sales Returns Report Suite.

Reports available:
  1. Daily Returns Detail    – per-day return lines, cost, qty, price, customer
  2. Global Returns Summary  – per-day aggregate HT / VAT / TTC
  3. Returns by Customer     – aggregate returns per customer
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

def fetch_daily_returns_detail(from_date, to_date):
    sql = """
        SELECT
            CONVERT(varchar(10), sr.sale_date, 23) AS return_date,
            sr.invoice_number,
            c.customer_name,
            p.product_name,
            sri.quantity,
            sri.unit_price,
            ISNULL(p.cost_price, 0) AS cost_price,
            ISNULL(sri.vat_amount, 0) AS vat_amt,
            sri.total_price AS subtotal
        FROM sales_return_items sri
        INNER JOIN sales_returns sr ON sr.id = sri.sales_return_id
        INNER JOIN customers c     ON c.id = sr.customer_id
        INNER JOIN products p      ON p.id = sri.product_id
        WHERE CONVERT(date, sr.sale_date) >= ?
          AND CONVERT(date, sr.sale_date) <= ?
        ORDER BY sr.sale_date, sr.invoice_number, p.product_name
    """
    return _q(sql, (from_date, to_date))


def fetch_global_returns_summary(from_date, to_date):
    sql = """
        SELECT
            CONVERT(varchar(10), sr.sale_date, 23) AS return_date,
            COUNT(DISTINCT sr.id)              AS return_count,
            SUM(ISNULL(sr.subtotal, 0))        AS total_ht,
            SUM(ISNULL(sr.total_vat, 0))       AS total_vat,
            SUM(ISNULL(sr.total_amount, 0))    AS total_ttc
        FROM sales_returns sr
        WHERE CONVERT(date, sr.sale_date) >= ?
          AND CONVERT(date, sr.sale_date) <= ?
        GROUP BY CONVERT(varchar(10), sr.sale_date, 23)
        ORDER BY return_date
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
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#6b2d2d')), # Dark red for returns
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f0f0')]),
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
            with ui.row().classes('w-full justify-between items-center p-3 bg-gray-900 border-b border-white/10'):
                ui.label(title).classes('text-white font-bold text-lg')
                ui.button('X Close', on_click=d.close).classes('bg-red-600 hover:bg-red-700 text-white px-4 py-1 rounded text-sm')
            ui.html(f'<iframe src="{data_url}" width="100%" height="100%" style="border:none; min-height:calc(100vh - 56px);"></iframe>').classes('w-full flex-1')
    d.open()


def _total_row_style(ts, idx):
    ts.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#4e1a1a'))
    ts.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


def _std_header(report_name, from_date, to_date):
    _, title_s, sub_s = _styles()
    return [
        Paragraph(f"{_company()} — {report_name}", title_s),
        Paragraph(f"Period: {from_date}  to  {to_date}", sub_s),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#6b2d2d')),
        Spacer(1, 6*mm),
    ]


# ==============================================================================
#  INDIVIDUAL PDF BUILDERS
# ==============================================================================

def generate_daily_returns_pdf(from_date, to_date):
    rows = fetch_daily_returns_detail(from_date, to_date)
    if not rows:
        ui.notify('No returns data for selected period.', color='warning'); return
    elements = _std_header('Daily Returns Detail', from_date, to_date)
    hdr = ['Date', 'Invoice', 'Customer', 'Product', 'Qty', 'Unit Price', 'Cost', 'VAT Amt', 'Subtotal']
    data = [hdr]
    for r in rows:
        data.append([
            str(r[0]), str(r[1]), str(r[2]), str(r[3]),
            str(r[4]), f"${float(r[5] or 0):.2f}", f"${float(r[6] or 0):.2f}",
            f"${float(r[7] or 0):.2f}", f"${float(r[8] or 0):.2f}"
        ])
    t_sub = sum(float(r[8] or 0) for r in rows)
    t_vat = sum(float(r[7] or 0) for r in rows)
    t_cost = sum(float(r[4] or 0) * float(r[6] or 0) for r in rows)
    data.append(['', '', '', 'TOTAL', '', '', f"${t_cost:.2f}", f"${t_vat:.2f}", f"${t_sub:.2f}"])
    ps = landscape(A4); avail = ps[0] - 30*mm
    cw = [avail*w for w in [.08, .10, .12, .18, .05, .09, .09, .09, .10]]
    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts(); _total_row_style(ts, len(data)-1); t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements, landscape_mode=True), 'Daily Returns Detail')


def generate_global_returns_pdf(from_date, to_date):
    rows = fetch_global_returns_summary(from_date, to_date)
    if not rows:
        ui.notify('No returns data for selected period.', color='warning'); return
    elements = _std_header('Global Returns Summary', from_date, to_date)
    hdr = ['Date', '# Returns', 'Total HT', 'Total VAT', 'Total TTC']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), f"${float(r[2] or 0):.2f}", f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}"])
    data.append(['TOTAL', str(sum(int(r[1]) for r in rows)), f"${sum(float(r[2] or 0) for r in rows):.2f}", f"${sum(float(r[3] or 0) for r in rows):.2f}", f"${sum(float(r[4] or 0) for r in rows):.2f}"])
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.20, .15, .22, .22, .22]]
    t = Table(data, colWidths=cw, repeatRows=1)
    ts = _header_ts(); _total_row_style(ts, len(data)-1); t.setStyle(ts)
    elements.append(t)
    _show_pdf(_build_pdf(elements), 'Global Returns Summary')


# ==============================================================================
#  PRINT SPECIAL DIALOG
# ==============================================================================

REPORTS = {
    'daily_detail':    ('Daily Returns Detail',    generate_daily_returns_pdf),
    'global_summary':   ('Global Returns Summary',  generate_global_returns_pdf),
}

DESCRIPTIONS = {
    'daily_detail':  'Return lines: date, invoice, customer, product, quantity, price, unit cost, VAT, and subtotal.',
    'global_summary': 'Daily return totals: count, total HT (Base), total VAT, and total TTC.',
}


def open_print_special_dialog():
    today = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'daily_detail', 'from_date': first_of_month, 'to_date': today}
    btns = {}; refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = 'background:rgba(239,68,68,0.25);border:1px solid rgba(239,68,68,0.5);' if k == key else 'background:rgba(255,255,255,0.04);border:none;'
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#1a0f0f; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style('background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('assignment_return', size='1.5rem').classes('text-red-400')
                    ui.label('Sales Returns Report Center').classes('text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes('bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style('width:260px;min-width:260px;background:rgba(255,255,255,0.03);border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes('text-[10px] font-black text-red-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k)).classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white transition-all').style('background:rgba(255,255,255,0.04);text-align:left;justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['daily_detail'][0]).classes('text-white font-black text-2xl').style('font-family:"Outfit",sans-serif;')
                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-red-400 uppercase tracking-widest')
                            ui.input(value=first_of_month).props('type=date outlined dense dark color=red stack-label').classes('text-white font-bold w-44').on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-red-400 uppercase tracking-widest')
                            ui.input(value=today).props('type=date outlined dense dark color=red stack-label').classes('text-white font-bold w-44').on_value_change(lambda e: state.update({'to_date': e.value}))
                        
                        def _run():
                            k, f, t = state['report_key'], state['from_date'], state['to_date']
                            if not f or not t: ui.notify('Select dates.', color='warning'); return
                            if f > t: ui.notify('From before To.', color='negative'); return
                            try: REPORTS[k][1](f, t)
                            except Exception as ex: ui.notify(f'Error: {ex}', color='negative')

                        ui.button('View Report', icon='visibility', on_click=_run).props('unelevated color=red').classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest shadow-xl shadow-red-500/20')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-red-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('daily_detail', '')).classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('daily_detail')
    dlg.open()
