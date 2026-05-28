"""
accounting_reports.py
=====================
Print Special reports for Accounting/Finance module.
"""

from nicegui import ui
from datetime import date
from connection import connection
import accounting_helpers
from trial_balance_generator import TrialBalanceReportGenerator

def report_trial_balance_flat(fd, td, a=None):
    accounting_helpers.print_trial_balance(from_date=fd, to_date=td)

def report_trial_balance_hierarchical(fd, td, a=None):
    accounting_helpers.print_hierarchical_trial_balance_pdf('', from_date=fd, to_date=td)

def report_trial_balance_expert(fd, td, a=None):
    """Integrates the Expert 10-column Report into the UI."""
    try:
        try:
            info = connection.get_company_info()
            c_name = info.get('company_name', 'ManagementOS') if info else 'ManagementOS'
        except:
            c_name = 'ManagementOS'

        gen = TrialBalanceReportGenerator(from_date=fd, to_date=td, company_name=c_name, account_filter=a)
        rows = gen.fetch_raw_data()
        
        if not rows:
            ui.notify(f'No accounting data found for period {fd} to {td}', color='warning', icon='warning')
            return

        report_data = gen.process_hierarchy(rows)
        
        if not report_data:
            ui.notify('No hierarchical data could be computed.', color='warning')
            return

        with ui.dialog().props('maximized persistent') as dlg:
            with ui.card().classes('w-full h-full p-0 gap-0 bg-[#0f1712] rounded-none'):
                # Header
                with ui.row().classes('w-full items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('analytics', color='green-400', size='2rem')
                        with ui.column().classes('gap-0'):
                            ui.label(f'TRIAL BALANCE EXPERT VIEW').classes('text-white font-black text-xl tracking-tighter')
                            ui.label(f'{fd} to {td}').classes('text-green-400 text-[10px] uppercase font-bold tracking-widest')
                    
                    with ui.row().classes('gap-3'):
                        def export_excel():
                            ui.run_javascript(f'''
                                const rows = {report_data};
                                if (!rows || rows.length === 0) return;
                                const csvHeaders = "Description,Cy,Debit True,Credit True,Bal D True,Bal C True,Debit 3,Credit 3,Bal D 3,Bal C 3";
                                const csvRows = rows.map(r => [
                                    r.Description, r.Cy, r['Debit true'], r['Credit true'], 
                                    r['Balance Debit true'], r['Balance Credit true'], 
                                    r['Debit 3'], r['Credit 3 ref'], r['Balance Debit 3'], r['Balance Credit 3']
                                ].join(","));
                                const csvContent = "data:text/csv;charset=utf-8," + csvHeaders + "\\n" + csvRows.join("\\n");
                                const encodedUri = encodeURI(csvContent);
                                const link = document.createElement("a");
                                link.setAttribute("href", encodedUri);
                                link.setAttribute("download", "Expert_Trial_Balance.csv");
                                document.body.appendChild(link);
                                link.click();
                            ''')
                            ui.notify('Exporting to CSV...', color='positive')

                        ui.button('EXCEL', icon='download', on_click=export_excel).props('flat color=green-400').classes('font-black')
                        ui.button('PRINT', icon='print', on_click=lambda: ui.run_javascript('window.print()')).props('flat color=blue-400').classes('font-black')
                        ui.button('CLOSE', icon='close', on_click=dlg.close).props('flat color=red').classes('font-black')

                # Grid Container
                with ui.column().classes('w-full flex-1 overflow-auto p-4'):
                    columns = [
                        {'name': 'Description',         'label': 'DESCRIPTION',      'field': 'Description',         'align': 'left',   'sortable': True},
                        {'name': 'Cy',                  'label': 'CY',               'field': 'Cy',                  'align': 'center', 'style': 'font-weight:900; color:#4ade80;'},
                        {'name': 'Debit true',          'label': 'DEBIT TRUE',       'field': 'Debit true',          'align': 'right'},
                        {'name': 'Credit true',         'label': 'CREDIT TRUE',      'field': 'Credit true',         'align': 'right'},
                        {'name': 'Balance Debit true',  'label': 'BAL D TRUE',       'field': 'Balance Debit true',  'align': 'right'},
                        {'name': 'Balance Credit true', 'label': 'BAL C TRUE',       'field': 'Balance Credit true', 'align': 'right'},
                        {'name': 'Debit 3',             'label': 'DEBIT 3',          'field': 'Debit 3',             'align': 'right',  'style': 'color:#facc15;'},
                        {'name': 'Credit 3',            'label': 'CREDIT 3',         'field': 'Credit 3 ref',        'align': 'right',  'style': 'color:#facc15;'},
                        {'name': 'Balance Debit 3',     'label': 'BAL D 3',          'field': 'Balance Debit 3',     'align': 'right',  'style': 'color:#fb923c;'},
                        {'name': 'Balance Credit 3',    'label': 'BAL C 3',          'field': 'Balance Credit 3',    'align': 'right',  'style': 'color:#fb923c;'},
                    ]

                    # Show all rows without pagination
                    table = ui.table(columns=columns, rows=report_data, row_key='Description', pagination={'rowsPerPage': 0})\
                        .classes('w-full bg-transparent text-white border-none')\
                        .props('dark flat dense binary-state-sort hide-pagination')
                    
                    table.add_slot('body-cell-Description', '''
                        <q-td :props="props">
                            <div :style="props.row.is_summary ? 'font-weight:900; color:#4ade80; text-transform:uppercase; font-size:11px;' : 'font-weight:400; font-size:10px; color:#9ca3af; padding-left:10px;'">
                                {{ props.value }}
                            </div>
                        </q-td>
                    ''')
                    table.style('font-family: "Outfit", sans-serif;')
        
            ui.add_head_html('<style> @media print { .q-dialog__inner > div { max-width: none !important; width: 100% !important; background: white !important; color: black !important; } .q-table__container { background: white !important; color: black !important; } .hide-on-print { display: none !important; } } </style>')
        dlg.open()
    except Exception as e:
        ui.notify(f'Expert Report Error: {e}', color='negative')
        import traceback; traceback.print_exc()

REPORTS = {
    'tb_expert': ('Trial Balance (Expert View)', report_trial_balance_expert),
    'tb_flat': ('Trial Balance (Flat)', report_trial_balance_flat),
    'tb_hier': ('Trial Balance (Hierarchical)', report_trial_balance_hierarchical),
    'tb_ui': ('Trial Hierarchy (Detailed UI)', lambda f, t, a: ui.navigate.to(f'/trial-hierarchy?from_date={f}&to_date={t}')),
    'view_tx': ('View Transactions', lambda f, t, a: accounting_helpers.show_transactions_dialog(account_number=a)),
    'stmt': ('Statement of Account', lambda f, t, a: accounting_helpers.print_account_statement(a, from_date=f, to_date=t)),
}

DESCRIPTIONS = {
    'tb_expert': 'Professional 10-column hierarchical trial balance with currency dimensions and scaled valuations.',
    'tb_flat': 'Standard flat trial balance showing all accounts with debit, credit, and balance.',
    'tb_hier': 'Hierarchical trial balance grouped by ledger root accounts (1 to 7).',
    'tb_ui': 'Interactive tree-based trial balance showing Ledger and Auxiliary levels with live balances.',
    'view_tx': 'View all accounting transactions linked to the selected account within the period.',
    'stmt': 'Generate a formal Statement of Account PDF for the selected ledger account.',
}

def open_print_special_dialog(initial_account=None):
    today          = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    state = {
        'report_key': 'tb_expert',
        'from_date': first_of_month,
        'to_date': today,
        'account': initial_account or ''
    }
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
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#0f1712; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style(
                    'background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('account_balance', size='1.5rem').classes('text-green-400')
                    ui.label('Accounting Report Center').classes('text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes('bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                with ui.column().classes('h-full p-4 gap-2 overflow-y-auto').style(
                        'width:250px; min-width:250px; background:rgba(255,255,255,0.03); border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes('text-[10px] font-black text-green-400 uppercase tracking-widest mb-2')
                    for k, (lbl, _) in REPORTS.items():
                        b = ui.button(lbl, on_click=lambda k=k: select(k))\
                               .classes('w-full px-4 py-3 rounded-xl text-sm font-bold text-white')\
                               .style('background:rgba(255,255,255,0.04); text-align:left; justify-content:flex-start;')
                        btns[k] = b

                with ui.column().classes('flex-1 h-full p-6 gap-5 overflow-auto'):
                    refs['n'] = ui.label(REPORTS['tb_expert'][0]).classes('text-white font-black text-2xl').style('font-family:"Outfit",sans-serif;')

                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl border border-white/10 w-full flex-wrap'):
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
                        with ui.column().classes('gap-1'):
                            ui.label('ACCOUNT #').classes('text-[9px] font-black text-green-400 uppercase tracking-widest')
                            ui.input(value=state['account']).props('outlined dense dark color=green')\
                               .classes('text-white font-bold w-44')\
                               .on_value_change(lambda e: state.update({'account': e.value}))

                        def _run():
                            k, f, t, a = state['report_key'], state['from_date'], state['to_date'], state['account']
                            if not f or not t: ui.notify('Select dates.', color='warning'); return
                            if f > t: ui.notify('From before To.', color='negative'); return
                            if k == 'stmt' and not a: ui.notify('Please enter an account number.', color='warning'); return
                            try: REPORTS[k][1](f, t, a)
                            except Exception as ex: ui.notify(f'Error: {ex}', color='negative')

                        ui.button('View Report', icon='visibility', on_click=_run)\
                          .props('unelevated color=green')\
                          .classes('px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest')

                    with ui.column().classes('w-full glass p-5 rounded-2xl border border-white/10 gap-2'):
                        ui.label('DESCRIPTION').classes('text-[9px] font-black text-green-400 uppercase tracking-widest')
                        refs['d'] = ui.label(DESCRIPTIONS.get('tb_expert', '')).classes('text-sm text-gray-300 font-medium leading-relaxed')

    select('tb_expert')
    dlg.open()
