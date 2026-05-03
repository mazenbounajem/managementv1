"""
auxiliary_reports.py
====================
Auxiliary reports:
  1. Auxiliary Ledger Transactions - Details of JV transactions
  2. Statement of Account          - Running debit/credit balance
  3. Trial Balance                 - Overview of selected auxiliary balance
  4. Global Auxiliary Balance      - All auxiliaries basic reporting

Used by:
  auxiliaryui.py -> open_print_special_dialog() (accent = purple)
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

def _ts(header_color='#8a2be2'):
    return TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor(header_color)),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  8),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5edff')]),
        ('GRID',           (0, 0), (-1, -1), 0.4, colors.HexColor('#ccc0dd')),
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

def _hdr(name, fd, td, accent='#8a2be2'):
    s = getSampleStyleSheet()
    ts = ParagraphStyle('t', parent=s['Heading1'], fontSize=16, spaceAfter=4)
    ss = ParagraphStyle('s', parent=s['Normal'],   fontSize=9,
                        textColor=colors.grey, spaceAfter=8)
    return [Paragraph(f"{_company()} — {name}", ts),
            Paragraph(f"Period: {fd}  to  {td}", ss),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor(accent)),
            Spacer(1, 6*mm)]

def _totrow(ts_obj, idx, bg='#4b0082'):
    ts_obj.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor(bg))
    ts_obj.add('TEXTCOLOR',  (0, idx), (-1, idx), colors.yellow)
    ts_obj.add('FONTNAME',   (0, idx), (-1, idx), 'Helvetica-Bold')

# ─────────────────────────────────────────────────────────────────────────────
#  REPORTS
# ─────────────────────────────────────────────────────────────────────────────

def _get_selected_aux():
    from nicegui import app
    try:
        from auxiliaryui import AuxiliaryUI
        for instance in AuxiliaryUI.instances:
            if hasattr(instance, 'get_selected_aux_number'):
                aux = instance.get_selected_aux_number()
                if aux: return aux
    except Exception:
        pass
    
    # Try the new approach or fallback if no static tracking
    return None

def report_auxiliary_statement(fd, td):
    aux_num = _get_selected_aux()
    if not aux_num:
        ui.notify('Please select an auxiliary from the table first.', color='warning')
        return

    sql = """
        SELECT CONVERT(varchar(10), ht.transaction_date, 23),
               ht.type, ht.jv_id, l.debit, l.credit, ht.description
        FROM accounting_transactions ht
        JOIN accounting_transaction_lines l ON ht.jv_id = l.jv_id
        WHERE l.auxiliary_id = ?
          AND CONVERT(date, ht.transaction_date) >= ?
          AND CONVERT(date, ht.transaction_date) <= ?
        ORDER BY ht.transaction_date ASC, ht.jv_id ASC
    """
    rows = _q(sql, (aux_num, fd, td))
    if not rows: ui.notify('No transactions found for this account.', color='warning'); return
    
    # Needs account name for header
    name_row = _q("SELECT account_name FROM auxiliary WHERE number=?", (aux_num,))
    acc_name = str(name_row[0][0]) if name_row else aux_num

    elements = _hdr(f'Statement of Account — {acc_name} ({aux_num})', fd, td)
    hdr = ['Date', 'Type', 'JV ID', 'Description', 'Debit', 'Credit', 'Balance']
    data = [hdr];  ts_obj = _ts()
    running = 0.0
    
    # Getting opening balance before from_date
    open_sql = """
        SELECT SUM(ISNULL(l.debit,0)) - SUM(ISNULL(l.credit,0))
        FROM accounting_transactions ht
        JOIN accounting_transaction_lines l ON ht.jv_id = l.jv_id
        WHERE l.auxiliary_id = ? AND CONVERT(date, ht.transaction_date) < ?
    """
    open_res = _q(open_sql, (aux_num, fd))
    if open_res and open_res[0][0]:
        running = float(open_res[0][0])
        data.append(['', 'OPENING', '', 'Opening Balance', '', '', f"${running:.2f}"])

    tot_deb, tot_cred = 0.0, 0.0
    for i, r in enumerate(rows, len(data)):
        deb  = float(r[3] or 0);  cred = float(r[4] or 0)
        tot_deb += deb; tot_cred += cred
        running += deb - cred
        
        data.append([str(r[0] or ''), str(r[1] or ''), str(r[2] or ''),
                     str(r[5] or ''), f"${deb:.2f}", f"${cred:.2f}", f"${running:.2f}"])
        if running < 0:
            ts_obj.add('TEXTCOLOR', (6, i), (6, i), colors.red)

    data.append(['TOTAL', '', '', '', f"${tot_deb:.2f}", f"${tot_cred:.2f}", f"${running:.2f}"])
    _totrow(ts_obj, len(data)-1)
    
    ps = A4; avail = ps[0] - 30*mm
    cw = [avail*w for w in [.12, .13, .08, .31, .12, .12, .12]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Statement of Account')

def report_auxiliary_trial_balance(fd, td):
    aux_num = _get_selected_aux()
    if not aux_num:
         prefix = '%' # All
    else:
         prefix = aux_num.split('.')[0] + '.%'

    sql = """
        SELECT a.number, a.account_name,
               ISNULL(SUM(l.debit), 0) AS d, ISNULL(SUM(l.credit), 0) AS c
        FROM auxiliary a
        JOIN accounting_transaction_lines l ON a.number = l.auxiliary_id
        JOIN accounting_transactions t ON l.jv_id = t.jv_id
        WHERE a.number LIKE ?
          AND CONVERT(date, t.transaction_date) >= ?
          AND CONVERT(date, t.transaction_date) <= ?
        GROUP BY a.number, a.account_name
        ORDER BY a.number
    """
    rows = _q(sql, (prefix, fd, td))
    if not rows: ui.notify('No trial balance data.', color='warning'); return
    
    elements = _hdr('Trial Balance', fd, td)
    hdr = ['Aux Number', 'Account Name', 'Total Debit', 'Total Credit', 'Net Balance']
    data = [hdr];  ts_obj = _ts()
    
    tot_d, tot_c = 0.0, 0.0
    for r in rows:
        d = float(r[2]); c = float(r[3])
        tot_d += d; tot_c += c
        bal = d - c
        data.append([str(r[0]), str(r[1]), f"${d:.2f}", f"${c:.2f}", f"${bal:.2f}"])
        
    data.append(['TOTAL', '', f"${tot_d:.2f}", f"${tot_c:.2f}", f"${(tot_d - tot_c):.2f}"])
    _totrow(ts_obj, len(data)-1)
    
    ps = A4; avail = ps[0] - 30*mm
    cw = [avail*w for w in [.20, .35, .15, .15, .15]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Trial Balance')

def report_auxiliary_transactions(fd, td):
    # Full detailed JV listing for auxiliaries
    sql = """
        SELECT CONVERT(varchar(10), t.transaction_date, 23),
               t.jv_id, a.number, a.account_name, l.debit, l.credit, l.description
        FROM accounting_transactions t
        JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        JOIN auxiliary a ON l.auxiliary_id = a.number
        WHERE CONVERT(date, t.transaction_date) >= ?
          AND CONVERT(date, t.transaction_date) <= ?
        ORDER BY t.transaction_date DESC, t.jv_id DESC
    """
    rows = _q(sql, (fd, td))
    if not rows: ui.notify('No transactions for this period.', color='warning'); return
    
    elements = _hdr('Auxiliary Ledger Transactions', fd, td)
    hdr = ['Date', 'JV', 'Aux Number', 'Account Name', 'Debit', 'Credit', 'Description']
    data = [hdr];  ts_obj = _ts()
    
    td_deb = 0.0; td_cred = 0.0
    for r in rows:
        d = float(r[4] or 0); c = float(r[5] or 0)
        td_deb += d; td_cred += c
        data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]), f"${d:.2f}", f"${c:.2f}", str(r[6] or '')])

    data.append(['TOTAL', '', '', '', f"${td_deb:.2f}", f"${td_cred:.2f}", ''])
    _totrow(ts_obj, len(data)-1)
    
    ps = landscape(A4); avail = ps[0] - 30*mm
    cw = [avail*w for w in [.10, .06, .12, .22, .10, .10, .30]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements, landscape_mode=True), 'Ledger Transactions')

def report_global_auxiliary_balance(fd, td):
    sql = """
        SELECT a.number, a.account_name, l.Name_en,
               (ISNULL((SELECT SUM(al.debit - al.credit) FROM accounting_transaction_lines al JOIN accounting_transactions at ON al.jv_id = at.jv_id WHERE al.auxiliary_id = a.number AND CONVERT(date, at.transaction_date) <= ?), 0)) as balance
        FROM auxiliary a
        LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
        WHERE a.status = 1
        ORDER BY balance DESC, a.number
    """
    rows = _q(sql, (td,))
    if not rows: ui.notify('No active auxiliaries found.', color='warning'); return
    
    elements = _hdr('Global Auxiliary Balance', fd, td)
    hdr = ['Aux Number', 'Account Name', 'Ledger', 'Net Balance']
    data = [hdr]; ts_obj = _ts()
    
    tot = 0.0
    for r in rows:
        bal = float(r[3] or 0)
        tot += bal
        data.append([str(r[0]), str(r[1] or ''), str(r[2] or ''), f"${bal:.2f}"])
        
    data.append(['TOTAL', '', '', f"${tot:.2f}"])
    _totrow(ts_obj, len(data)-1)
    
    ps = A4; avail = ps[0] - 30*mm
    cw = [avail*w for w in [.20, .35, .25, .20]]
    t = Table(data, colWidths=cw, repeatRows=1);  t.setStyle(ts_obj)
    elements.append(t);  _show(_build(elements), 'Global Balance')


REPORTS = {
    'aux_tb':        ('Trial Balance',              report_auxiliary_trial_balance),
    'aux_tx':        ('Ledger Transactions',        report_auxiliary_transactions),
    'aux_global':    ('Global Auxiliary Balance',   report_global_auxiliary_balance),
}

DESCRIPTIONS = {
    'aux_tb':       'Overview of debit/credit totals and balance. If an auxiliary is selected, it shows only that auxiliary tree.',
    'aux_tx':       'Detailed JV line items for all auxiliary accounts.',
    'aux_global':   'List of all active auxiliaries with their ledger name and total net balance.',
}


def open_print_special_dialog():
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {'report_key': 'aux_tb', 'from_date': first_of_month, 'to_date': today}
    btns = {};  refs = {}

    def select(key):
        state['report_key'] = key
        for k, b in btns.items():
            sty = ('background:rgba(138,43,226,0.25);border:1px solid rgba(138,43,226,0.5);'
                   if k == key else 'background:rgba(255,255,255,0.04);border:none;')
            b.style(sty)
        if 'n' in refs: refs['n'].text = REPORTS[key][0]
        if 'd' in refs: refs['d'].text = DESCRIPTIONS.get(key, '')

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#0d1525; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style('background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('account_tree', size='1.5rem').classes('text-purple-400')
                    ui.label('Auxiliary Report Center').classes('text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes('bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style('width:250px; min-width:250px;background:rgba(255,255,255,0.03);border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes('text-[10px] font-black text-purple-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left; justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['aux_tb'][0]).classes('text-white font-black text-2xl').style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl border border-white/10 w-full flex-wrap'):
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
                        refs['d'] = ui.label(DESCRIPTIONS.get('aux_tb', '')).classes('text-sm text-gray-300 font-medium leading-relaxed')

        select('aux_tb')
    dlg.open()
