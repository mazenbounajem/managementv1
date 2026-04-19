"""
reports_framework.py
Shared utility for building the standard "Print Special" full-screen
report-selector dialog used across all modules (Sales, Purchase, Product,
Customer, Supplier, Stock, Expenses, Accounting).

Usage:
    from reports_framework import open_report_dialog
    open_report_dialog(REPORTS, DESCRIPTIONS, title='Customer Reports')

REPORTS  = dict[key -> (label, fn(from_date, to_date))]
DESCRIPTIONS = dict[key -> description_string]
"""

from nicegui import ui
from datetime import date as _date
from io import BytesIO
import base64

# ── ReportLab ───────────────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

from connection import connection


# ── DB helper ───────────────────────────────────────────────────────────────

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


# ── PDF helpers ──────────────────────────────────────────────────────────────

def base_doc(buf, landscape_mode=False):
    ps = landscape(A4) if landscape_mode else A4
    return SimpleDocTemplate(buf, pagesize=ps,
                             leftMargin=15*mm, rightMargin=15*mm,
                             topMargin=15*mm, bottomMargin=15*mm)


def report_styles():
    s = getSampleStyleSheet()
    title = ParagraphStyle('RTitle', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    sub   = ParagraphStyle('RSub',   parent=s['Normal'],   fontSize=9,
                           textColor=colors.grey, spaceAfter=8)
    return s, title, sub


def table_style():
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#2d2d6b')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  8),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1),
         [colors.white, colors.HexColor('#f0f0f8')]),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('FONTSIZE',      (0, 1), (-1, -1), 7.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
    ])


def add_total_row_style(ts, row_idx):
    ts.add('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#1a1a4e'))
    ts.add('TEXTCOLOR',  (0, row_idx), (-1, row_idx), colors.yellow)
    ts.add('FONTNAME',   (0, row_idx), (-1, row_idx), 'Helvetica-Bold')


def build_pdf(elements, landscape_mode=False):
    buf = BytesIO()
    doc = base_doc(buf, landscape_mode)
    doc.build(elements)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def show_pdf(b64: str, title='Report'):
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


def pdf_header(company, report_name, from_date, to_date):
    """Standard PDF header elements."""
    _, title_s, sub_s = report_styles()
    elements = [
        Paragraph(f"{company} — {report_name}", title_s),
        Paragraph(f"Period: {from_date}  to  {to_date}", sub_s),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2d2d6b')),
        Spacer(1, 6*mm),
    ]
    return elements


# ── Shared dialog builder ────────────────────────────────────────────────────

def open_report_dialog(reports: dict, descriptions: dict,
                       title: str = 'Report Center',
                       icon: str = 'print',
                       accent_color: str = 'purple'):
    """
    Open a full-screen, dark-themed Print Special dialog.

    Parameters
    ----------
    reports      : dict[key -> (label, fn)]
                   fn signature: fn(from_date: str, to_date: str) -> None
    descriptions : dict[key -> str]
    title        : dialog title bar text
    icon         : material icon name
    accent_color : tailwind color token used for highlights
    """
    today =          _date.today().strftime('%Y-%m-%d')
    first_of_month = _date.today().replace(day=1).strftime('%Y-%m-%d')

    state = {
        'report_key': next(iter(reports)),
        'from_date':  first_of_month,
        'to_date':    today,
    }

    report_buttons = {}
    ui_refs = {}

    def select_report(key):
        state['report_key'] = key
        ac = f'rgba(139,92,246,0.25)' if accent_color == 'purple' else 'rgba(59,130,246,0.25)'
        ab = f'rgba(139,92,246,0.5)'  if accent_color == 'purple' else 'rgba(59,130,246,0.5)'
        for k, b in report_buttons.items():
            if k == key:
                b.style(f'background:{ac}; border:1px solid {ab};')
            else:
                b.style('background:rgba(255,255,255,0.04); border:none;')
        if 'name_label' in ui_refs:
            ui_refs['name_label'].text = reports[key][0]
        if 'desc_label' in ui_refs:
            ui_refs['desc_label'].text = descriptions.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')

        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style(
                'background:#0f0f19; border-radius:0;'):

            # Title bar
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);'
                    'border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon(icon, size='1.5rem').classes(f'text-{accent_color}-400')
                    ui.label(title).classes('text-white font-black text-xl').style(
                        'font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes(
                    'bg-red-600/80 hover:bg-red-600 text-white'
                    ' px-4 py-1 rounded-lg text-sm font-bold')

            # Body
            with ui.row().classes('w-full gap-0 overflow-hidden').style(
                    'height:calc(100vh - 56px);'):

                # LEFT sidebar
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:280px; min-width:280px;'
                        'background:rgba(255,255,255,0.03);'
                        'border-right:1px solid rgba(255,255,255,0.08);'):

                    ui.label('SELECT REPORT').classes(
                        f'text-[10px] font-black text-{accent_color}-400'
                        ' uppercase tracking-widest mb-2')

                    for k, (lbl, _fn) in reports.items():
                        btn = ui.button(lbl, on_click=lambda k=k: select_report(k))\
                                 .classes('w-full px-4 py-3 rounded-xl text-sm font-bold'
                                          ' text-white transition-all')\
                                 .style('background:rgba(255,255,255,0.04);'
                                        'text-align:left; justify-content:flex-start;')
                        report_buttons[k] = btn

                # RIGHT panel
                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):

                    name_label = ui.label(reports[state['report_key']][0])\
                        .classes('text-white font-black text-2xl')\
                        .style('font-family:"Outfit",sans-serif;')
                    ui_refs['name_label'] = name_label

                    # Date + View row
                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl'
                                         ' border border-white/10 w-full flex-wrap'):

                        with ui.column().classes('gap-1'):
                            ui.label('FROM DATE').classes(
                                f'text-[9px] font-black text-{accent_color}-400'
                                ' uppercase tracking-widest')
                            ui.input(value=first_of_month)\
                               .props('type=date outlined dense dark'
                                      f' color={accent_color} stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'from_date': e.value}))

                        with ui.column().classes('gap-1'):
                            ui.label('TO DATE').classes(
                                f'text-[9px] font-black text-{accent_color}-400'
                                ' uppercase tracking-widest')
                            ui.input(value=today)\
                               .props('type=date outlined dense dark'
                                      f' color={accent_color} stack-label')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'to_date': e.value}))

                        def _run_report():
                            key = state['report_key']
                            f   = state['from_date']
                            t   = state['to_date']
                            if not f or not t:
                                ui.notify('Select both dates.', color='warning')
                                return
                            if f > t:
                                ui.notify('"From" must be before "To".', color='negative')
                                return
                            _, fn = reports[key]
                            try:
                                fn(f, t)
                            except Exception as ex:
                                ui.notify(f'Report error: {ex}', color='negative')
                                import traceback; traceback.print_exc()

                        ui.button('View Report', icon='visibility', on_click=_run_report)\
                          .props(f'unelevated color={accent_color}')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase'
                                   ' tracking-widest shadow-xl')

                    # Description
                    with ui.column().classes('w-full glass p-5 rounded-2xl'
                                            ' border border-white/10 gap-2'):
                        ui.label('REPORT DESCRIPTION').classes(
                            f'text-[9px] font-black text-{accent_color}-400'
                            ' uppercase tracking-widest')
                        desc_label = ui.label(
                            descriptions.get(state['report_key'], '')
                        ).classes('text-sm text-gray-300 font-medium leading-relaxed')
                        ui_refs['desc_label'] = desc_label

        select_report(state['report_key'])

    dlg.open()
