"""
purchase_return_reports.py
==========================
Print Special report suite for the Purchase Returns module.

Reports:
  1. Global Purchase Returns  – daily / monthly totals
  2. Purchase Returns by Item – detailed item list per return
  3. Returns by Supplier      – grouped by supplier with totals
  4. Individual Receipts      – compact format for all returns in period
"""

from nicegui import ui
from datetime import date, datetime
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
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#4e2d1a')), # Brownish-red for purchase returns
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f4f0')]),
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
            with ui.row().classes('w-full justify-between items-center p-3 bg-gray-900 border-b border-white/10'):
                ui.label(title).classes('text-white font-bold text-lg')
                ui.button('X Close', on_click=d.close).classes('bg-red-600 text-white px-4 py-1 rounded text-sm')
            ui.html(f'<iframe src="{data_url}" width="100%" height="100%" style="border:none; min-height:calc(100vh - 56px);"></iframe>').classes('w-full flex-1')
    d.open()


def _hdr(name, fd, td):
    s = getSampleStyleSheet()
    ts = ParagraphStyle('t', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    ss = ParagraphStyle('s', parent=s['Normal'],   fontSize=9,
                        textColor=colors.grey, spaceAfter=8)
    return [Paragraph(f"{_company()} — {name}", ts),
            Paragraph(f"Period: {fd}  to  {td}", ss),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#4e2d1a')),
            Spacer(1, 6*mm)]


def _totrow(ts_obj, idx):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#331a0d'))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


# ── Report 1: Global Purchase Returns ────────────────────────────────────────

def report_global_purchase_return_summary(fd, td):
    sql = """
        SELECT CONVERT(varchar(10), pr.purchase_date, 23) AS dt,
               COUNT(DISTINCT pr.id)                       AS ret_count,
               SUM(ISNULL(pr.subtotal, 0))                 AS total_ht,
               SUM(ISNULL(pr.total_vat, 0))                AS total_vat,
               SUM(ISNULL(pr.total_amount, 0))             AS total_ttc
        FROM purchase_returns pr
        WHERE CONVERT(date, pr.purchase_date) >= ?
          AND CONVERT(date, pr.purchase_date) <= ?
        GROUP BY CONVERT(varchar(10), pr.purchase_date, 23)
        ORDER BY dt
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No return data.', color='warning'); return
    elements = _hdr('Global Purchase Returns Summary', fd, td)
    hdr = ['Date', '# Returns', 'Total HT', 'Total VAT', 'Total TTC']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), f"${float(r[2] or 0):.2f}",
                     f"${float(r[3] or 0):.2f}", f"${float(r[4] or 0):.2f}"])
    data.append(['TOTAL', str(sum(int(r[1]) for r in rows)),
                 f"${sum(float(r[2] or 0) for r in rows):.2f}",
                 f"${sum(float(r[3] or 0) for r in rows):.2f}",
                 f"${sum(float(r[4] or 0) for r in rows):.2f}"])
    ts_obj = _ts(); _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.20, .15, .22, .22, .22]]
    t = Table(data, colWidths=cw, repeatRows=1); t.setStyle(ts_obj)
    elements.append(t); _show(_build(elements), 'Global Purchase Returns')


# ── Report 2: Purchase Return by Items Daily ───────────────────────────────

def report_purchase_return_by_items_daily(fd, td):
    sql = """
        SELECT CONVERT(varchar(10), pr.purchase_date, 23) AS dt,
               pr.invoice_number,
               s.name AS supplier,
               p.product_name,
               pri.quantity,
               pri.unit_cost,
               pri.total_cost AS subtotal
        FROM purchase_return_items pri
        INNER JOIN purchase_returns pr ON pr.id = pri.purchase_return_id
        INNER JOIN products p ON p.id = pri.product_id
        INNER JOIN suppliers s ON s.id = pr.supplier_id
        WHERE CONVERT(date, pr.purchase_date) >= ?
          AND CONVERT(date, pr.purchase_date) <= ?
        ORDER BY dt, pr.invoice_number
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No detail data.', color='warning'); return
    elements = _hdr('Purchase Returns by Items (Daily)', fd, td)
    hdr = ['Date', 'Invoice', 'Supplier', 'Product', 'Qty', 'Unit Cost', 'Subtotal']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]),
                     str(r[4]), f"${float(r[5] or 0):.2f}", f"${float(r[6] or 0):.2f}"])
    data.append(['TOTAL', '', '', '', str(sum(int(r[4]) for r in rows)), '',
                 f"${sum(float(r[6] or 0) for r in rows):.2f}"])
    ts_obj = _ts(); _totrow(ts_obj, len(data)-1)
    ps = landscape(A4); avail = ps[0] - 30*mm
    cw = [avail*w for w in [.10, .12, .18, .25, .07, .13, .15]]
    t = Table(data, colWidths=cw, repeatRows=1); t.setStyle(ts_obj)
    elements.append(t); _show(_build(elements, landscape_mode=True), 'Returns by Items')


# ── Report 3: Individual Receipts ────────────────────────────────────────────

def report_individual_purchase_returns(fd, td):
    sql = """
        SELECT pr.invoice_number,
               CONVERT(varchar(10), pr.purchase_date, 23) AS dt,
               s.name AS supplier,
               pr.subtotal, pr.total_vat, pr.total_amount
        FROM purchase_returns pr
        INNER JOIN suppliers s ON s.id = pr.supplier_id
        WHERE CONVERT(date, pr.purchase_date) >= ?
          AND CONVERT(date, pr.purchase_date) <= ?
        ORDER BY dt, pr.invoice_number
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No returns in this period.', color='warning'); return
    
    company = _company()
    s = getSampleStyleSheet()
    rt = ParagraphStyle('rt', fontName='Helvetica-Bold', fontSize=10, alignment=1)
    rs = ParagraphStyle('rs', fontSize=8, leading=10)
    
    elements = []
    for r in rows:
        inv, dt_, sup, ht, vat, ttc = r[0], r[1], r[2], float(r[3]), float(r[4]), float(r[5])
        elements.append(Paragraph(f"<b>{company} - DEBIT NOTE</b>", rt))
        elements.append(Paragraph(f"Return #: {inv} | Date: {dt_}", rs))
        elements.append(Paragraph(f"Supplier: {sup}", rs))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Paragraph(f"Base HT: ${ht:.2f}", rs))
        elements.append(Paragraph(f"VAT Amt: ${vat:.2f}", rs))
        elements.append(Paragraph(f"<b>TOTAL TTC: ${ttc:.2f}</b>", rs))
        elements.append(HRFlowable(width="100%", thickness=1.0, color=colors.black))
        elements.append(Spacer(1, 10*mm))

    _show(_build(elements), 'Individual Purchase Returns')


# ── REGISTRY ─────────────────────────────────────────────────────────────────

REPORTS = {
    'global_summary': ('Global Purchase Return',   report_global_purchase_return_summary),
    'by_items':       ('Returns by Items Daily',  report_purchase_return_by_items_daily),
    'individual':     ('Individual Returns',      report_individual_purchase_returns),
}

DESCRIPTIONS = {
    'global_summary': 'Daily totals for purchase returns: count, base HT, VAT, and total TTC.',
    'by_items':       'Detailed list of returned products including supplier names and individual costs.',
    'individual':     'Step-by-step listing of each return (Debit Note) issued in the selected period.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'global_summary', 'from_date': first_of_month, 'to_date': today}
    btns = {}; refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(239,68,68,0.25);border:1px solid rgba(239,68,68,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#1a100d; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style('background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('assignment_return', size='1.5rem').classes('text-red-400')
                    ui.label('Purchase Returns Report Center').classes('text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes('bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style('width:250px; min-width:250px; background:rgba(255,255,255,0.03); border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes('text-[10px] font-black text-red-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k)).classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white').style('background:rgba(255,255,255,0.04); text-align:left; justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['global_summary'][0]).classes('text-white font-black text-2xl').style('font-family:"Outfit",sans-serif;')
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
                        refs['d'] = ui.label(DESCRIPTIONS.get('global_summary', '')).classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('global_summary')
    dlg.open()
