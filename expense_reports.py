"""
expense_reports.py
==================
Print Special reports for Expenses module.

Reports:
  1. Expenses by Type        – grouped by expense category
  2. Expenses by Date Range  – all expenses in period
  3. Monthly Summary         – per-month aggregate
  4. Expense Trend           – month-over-month comparison
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
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#5e2d1a')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f0')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#ddbbaa')),
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
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#5e2d1a')),
            Spacer(1, 6*mm)]


def _totrow(ts_obj, idx):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#3a1000'))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')


def report_expenses_by_type(fd, td):
    sql = """
        SELECT e.expense_type,
               COUNT(e.id)        AS count,
               SUM(e.amount)      AS total,
               AVG(e.amount)      AS avg_amount
        FROM expenses e
        WHERE CONVERT(date, e.expense_date) >= ?
          AND CONVERT(date, e.expense_date) <= ?
        GROUP BY e.expense_type
        ORDER BY total DESC
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No expenses found.', color='warning'); return
    elements = _hdr('Expenses by Type', fd, td)
    hdr = ['Type', 'Count', 'Total Amount', 'Avg Amount']
    data = [hdr]
    for r in rows:
        data.append([str(r[0] or 'Uncategorised'), str(r[1]),
                     f"${float(r[2] or 0):.2f}", f"${float(r[3] or 0):.2f}"])
    data.append(['TOTAL', str(sum(int(r[1]) for r in rows)),
                 f"${sum(float(r[2] or 0) for r in rows):.2f}", ''])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.45, .15, .20, .20]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Expenses by Type')


def report_expenses_detail(fd, td):
    sql = """
        SELECT CONVERT(varchar(10), e.expense_date, 23),
               e.expense_type,
               e.description,
               e.amount,
               e.payment_method,
               e.invoice_number
        FROM expenses e
        WHERE CONVERT(date, e.expense_date) >= ?
          AND CONVERT(date, e.expense_date) <= ?
        ORDER BY e.expense_date
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No expenses found.', color='warning'); return
    elements = _hdr('Expenses Detail', fd, td)
    hdr = ['Date', 'Type', 'Description', 'Amount', 'Method', 'Reference']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1] or ''), str(r[2] or ''),
                     f"${float(r[3] or 0):.2f}", str(r[4] or ''), str(r[5] or '')])
    data.append(['TOTAL', '', '', f"${sum(float(r[3] or 0) for r in rows):.2f}", '', ''])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    ps = landscape(A4);  avail = ps[0] - 30*mm
    cw = [avail*w for w in [.12, .15, .28, .14, .13, .14]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Expenses Detail')


def report_monthly_summary(fd, td):
    sql = """
        SELECT FORMAT(e.expense_date, 'yyyy-MM') AS month_str,
               COUNT(e.id)   AS count,
               SUM(e.amount) AS total
        FROM expenses e
        WHERE CONVERT(date, e.expense_date) >= ?
          AND CONVERT(date, e.expense_date) <= ?
        GROUP BY FORMAT(e.expense_date, 'yyyy-MM')
        ORDER BY month_str
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No data.', color='warning'); return
    elements = _hdr('Monthly Expense Summary', fd, td)
    hdr = ['Month', '# Expenses', 'Total']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[1]), f"${float(r[2] or 0):.2f}"])
    data.append(['TOTAL', str(sum(int(r[1]) for r in rows)),
                 f"${sum(float(r[2] or 0) for r in rows):.2f}"])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.35, .30, .35]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Monthly Expense Summary')


def report_expense_trend(fd, td):
    """Year-over-year comparison if data spans multiple years."""
    sql = """
        SELECT FORMAT(e.expense_date, 'yyyy') AS yr,
               FORMAT(e.expense_date, 'MM')   AS mo,
               FORMAT(e.expense_date, 'MMM')  AS mono_name,
               SUM(e.amount)                  AS total
        FROM expenses e
        WHERE CONVERT(date, e.expense_date) >= ?
          AND CONVERT(date, e.expense_date) <= ?
        GROUP BY FORMAT(e.expense_date, 'yyyy'), FORMAT(e.expense_date, 'MM'),
                 FORMAT(e.expense_date, 'MMM')
        ORDER BY yr, mo
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No data.', color='warning'); return
    elements = _hdr('Expense Trend by Year / Month', fd, td)
    hdr = ['Year', 'Month', 'Total Amount']
    data = [hdr]
    for r in rows:
        data.append([str(r[0]), str(r[2]), f"${float(r[3] or 0):.2f}"])
    data.append(['GRAND TOTAL', '', f"${sum(float(r[3] or 0) for r in rows):.2f}"])
    ts_obj = _ts();  _totrow(ts_obj, len(data)-1)
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [.25, .40, .35]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Expense Trend')


REPORTS = {
    'by_type':   ('Expenses by Type',        report_expenses_by_type),
    'detail':    ('Expense Detail',          report_expenses_detail),
    'monthly':   ('Monthly Summary',         report_monthly_summary),
    'trend':     ('Expense Trend',           report_expense_trend),
}

DESCRIPTIONS = {
    'by_type':  'Total expenses grouped by type/category with count and average in selected period.',
    'detail':   'Line-by-line expense list: date, type, description, amount, method, reference.',
    'monthly':  'Monthly aggregate: count and total per month in the selected date range.',
    'trend':    'Year-by-year, month-by-month comparison to identify spending trends.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'by_type', 'from_date': first_of_month, 'to_date': today}
    btns = {};  refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(249,115,22,0.25);border:1px solid rgba(249,115,22,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#180d05; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('receipt_long', size='1.5rem').classes('text-orange-400')
                    ui.label('Expenses Report Center').classes(
                        'text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:250px; min-width:250px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes(
                        'text-[10px] font-black text-orange-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left;'
                                      ' justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['by_type'][0])\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest')
                            ui.input(value=first_of_month).props('type=date outlined dense dark color=orange stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest')
                            ui.input(value=today).props('type=date outlined dense dark color=orange stack-label')\
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
                          .props('unelevated color=orange')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('by_type', ''))\
                            .classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('by_type')
    dlg.open()
