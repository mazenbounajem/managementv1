from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable, ModernActionBar
from session_storage import session_storage
from datetime import datetime
import datetime as dt

def supplier_payment_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    state = {
        'selected_supplier': None,
        'unpaid_invoices': [],
        'selected_invoices': [],
        'payment_data': [],
        'new_mode': False,
        'draft_payment_id': None,
        'draft_amount': 0.0,
        'draft_method': 'Cash',
    }
    input_refs = {}

    def to_float(value):
        try:
            return round(float(value or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    def calculate_supplier_pending(supplier_id):
        """Calculate total pending amount from unpaid purchase invoices"""
        result = []
        sql = """
            SELECT SUM(ISNULL(total_amount, 0)) 
            FROM purchases p 
            INNER JOIN suppliers s ON s.id = p.supplier_id 
            WHERE s.id = ? AND p.payment_status = 'pending' AND ISNULL(p.total_amount, 0) > 0
        """
        connection.contogetrows(sql, result, (supplier_id,))
        return to_float(result[0][0]) if result and result[0][0] is not None else 0.0

    def refresh_history():
        data = []
        sql = """SELECT sp.id, sp.payment_date, s.name, sp.amount, sp.payment_method, s.id as supplier_id \n                 FROM supplier_payment sp\n                 JOIN suppliers s ON sp.supplier_id = s.id\n                 ORDER BY sp.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        for r in data:
            rows.append({
                'id': r[0],
                'date': r[1],
                'supplier': r[2],
                'amount': to_float(r[3]),
                'method': r[4],              'supplier_id': r[5],           })
        history_table.options['rowData'] = rows
        history_table.update()

    def fetch_supplier_balance(supplier_id):
        """Get accurate pending balance from unpaid invoices"""
        return calculate_supplier_pending(supplier_id)

    def clear_draft_state(reset_supplier=True):
        state['selected_invoices'] = []
        state['draft_payment_id'] = None
        state['draft_amount'] = 0.0
        state['draft_method'] = input_refs['method'].value if 'method' in input_refs else 'Cash'
        if reset_supplier:
            state['selected_supplier'] = None

    def clear_form(reset_supplier=True):
        if 'supplier' in input_refs:
            input_refs['supplier'].set_value('')
        if 'balance' in input_refs:
            input_refs['balance'].set_value(0)
        if 'amount' in input_refs:
            input_refs['amount'].set_value(0)
        if 'method' in input_refs:
            input_refs['method'].set_value('Cash')
        clear_draft_state(reset_supplier=reset_supplier)

    def set_new_mode(enabled):
        state['new_mode'] = enabled
        if 'history_overlay' in input_refs:
            input_refs['history_overlay'].set_visibility(enabled)

    def exit_new_mode():
        set_new_mode(False)

    def load_supplier_draft_balance():
        supplier = state.get('selected_supplier')
        if supplier:
            current_balance = fetch_supplier_balance(supplier['id'])
            supplier['balance'] = current_balance
            if 'balance' in input_refs:
                input_refs['balance'].set_value(current_balance)

    def update_draft_amount_from_selected_invoices():
        total = sum(to_float(item.get('settlement_amount')) for item in state['selected_invoices'])
        total = round(total, 2)
        state['draft_amount'] = total
        if 'amount' in input_refs:
            input_refs['amount'].set_value(total)

    def allocate_payment_to_invoices(selected_rows, pay_amount):
        allocations = []
        remaining = round(pay_amount, 2)

        ordered_rows = sorted(
            selected_rows,
            key=lambda row: (str(row.get('date') or ''), row.get('id') or 0)
        )

        for row in ordered_rows:
            invoice_due = to_float(row.get('amount'))
            if invoice_due <= 0:
                continue
            settlement_amount = min(invoice_due, remaining)
            if settlement_amount > 0:
                allocations.append({
                    'id': row['id'],
                    'invoice_number': row['invoice_number'],
                    'date': row['date'],
                    'amount': invoice_due,
                    'status': row['status'],
                    'settlement_amount': round(settlement_amount, 2),
                    'remaining_after_settlement': round(invoice_due - settlement_amount, 2),
                })
                remaining = round(remaining - settlement_amount, 2)
            if remaining <= 0:
                break

        return allocations

    def select_supplier():
        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select Supplier').classes('text-xl font-bold mb-4')

            s_data = []
            connection.contogetrows(
"SELECT id, name, balance, balance_usd FROM suppliers ORDER BY name",
                s_data,
            )
            s_rows = [           {'id': r[0], 'name': r[1], 'balance_ll': to_float(r[2]), 'balance_usd': to_float(r[3] or 0)}               for r in s_data           ]

            grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Name', 'field': 'name', 'flex': 1},
                {'headerName': 'Balance LL', 'field': 'balance_ll', 'width': 100, 'valueFormatter': '"L.L. " + Number(params.value || 0).toLocaleString()'},
                {'headerName': 'Balance USD', 'field': 'balance_usd', 'width': 110, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                ],
                'rowData': s_rows,
                'rowSelection': 'single'
            }).classes('w-full h-80 ag-theme-quartz-dark')

            async def confirm():
                row = await grid.get_selected_row()
                if row:
                    state['selected_supplier'] = {
                        'id': row['id'],
                        'name': row['name'],
                        'balance_ll': row['balance_ll'],
                        'balance_usd': row['balance_usd'],
                        'balance': row['balance_ll'] + row['balance_usd']
                    }
                    input_refs['supplier'].set_value(row['name'])
                    if 'balance' in input_refs:
                        input_refs['balance'].set_value(row['balance_usd'] or 0)
                    input_refs['amount'].set_value('0.00')
                    state['selected_invoices'] = []
                    state['draft_amount'] = 0.0
                    if 'total' in input_refs:
                        input_refs['total'].set_value('0.00')
                    d.close()
                    ui.notify('Supplier selected. Click Amount to open pending purchase invoices.', color='positive')
                else:
                    ui.notify('Select supplier with balance > 0', color='warning')

            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ModernButton('Cancel', on_click=d.close, variant='secondary')
                ModernButton('Select', on_click=confirm)

        d.open()

    def open_settlement_dialog(supplier):
        state['unpaid_invoices'] = []
        load_supplier_draft_balance()

        invoices_data = []
        sql = """
            SELECT p.id, p.invoice_number, p.total_amount, p.purchase_date, p.payment_status, s.name
            FROM purchases p
            INNER JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.payment_status = 'pending'
              AND s.name = ?
              AND ISNULL(p.total_amount, 0) > 0
            ORDER BY p.purchase_date ASC, p.id ASC
        """
        connection.contogetrows(sql, invoices_data, (supplier['name'],))

        rows = []
        total_due = 0.0
        for r in invoices_data:
            amount = to_float(r[2])
            row = {
                'id': r[0],
                'invoice_number': r[1],
                'amount': amount,
                'date': str(r[3]),
                'status': r[4] or 'pending',
                'supplier_name': r[5] or supplier['name'],
            }
            rows.append(row)
            total_due += amount

        total_due = round(total_due, 2)
        state['unpaid_invoices'] = rows

        if not rows:
            ui.notify('No pending purchase invoices for this supplier', color='info')
            return

        with ui.dialog() as settlement_dialog, ModernCard().classes('w-full max-w-5xl p-8'):
            ui.label(f'Pending Purchase Invoices: {supplier["name"]}').classes('text-2xl font-bold mb-2 text-white')
            ui.label(f'Supplier Balance: ${to_float(supplier["balance"]):.2f}').classes('text-lg mb-1 text-green-400 font-bold')
            ui.label('Tick the checkbox rows you want to pay. Only pending purchase invoices for the selected supplier are shown here.').classes('text-sm mb-4 text-yellow-300')

            ui.label('📋 Invoice Selection Table - Check invoices to pay').classes('text-base font-bold mb-2 text-blue-300')

            invoice_grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Select', 'checkboxSelection': True, 'headerCheckboxSelection': True, 'width': 80},
                    {'headerName': 'Invoice #', 'field': 'invoice_number', 'flex': 1},
                    {'headerName': 'Supplier', 'field': 'supplier_name', 'width': 180},
                    {'headerName': 'Date', 'field': 'date', 'width': 130},
                    {'headerName': 'Amount', 'field': 'amount', 'width': 130, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                    {'headerName': 'Status', 'field': 'status', 'width': 120},
                ],
                'rowData': rows,
                'rowSelection': 'multiple',
                'suppressRowClickSelection': True,
            }).classes('w-full h-96 ag-theme-quartz-dark mb-6')

            with ui.row().classes('items-center gap-4 mb-2'):
                ui.label('Payment Amount:').classes('font-bold')
                max_allowed = min(to_float(supplier['balance']), total_due)
                default_amount = to_float(input_refs['amount'].value or 0)
                if default_amount <= 0:
                    default_amount = max_allowed

                payment_amount_ref = ui.number(
                    value=default_amount,
                    min=0,
                    max=max_allowed,
                    step=0.01,
                ).classes('w-40')
                ui.label('Method:').classes('font-bold ml-4')
                payment_method_ref = ui.select(
                    ['Cash', 'Card', 'Visa', 'OMT'],
                    value=input_refs['method'].value or 'Cash',
                ).classes('w-40')

            selected_total_label = ui.label('Total Selected: $0.00').classes('text-md mb-4 text-blue-300 font-bold')

            ui.label('🔍 Payment Allocation Preview Table - Shows how payment distributes').classes('text-base font-bold mb-2 text-green-300')

            preview_label = ui.label('Choose invoices, adjust payment amount if needed, then click OK.').classes('text-sm text-gray-300 mb-2')
            preview_grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Invoice #', 'field': 'invoice_number', 'flex': 1},
                    {'headerName': 'Invoice Total', 'field': 'amount', 'width': 140, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                    {'headerName': 'Settlement', 'field': 'settlement_amount', 'width': 140, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                    {'headerName': 'Remaining', 'field': 'remaining_after_settlement', 'width': 140, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                ],
                'rowData': [],
                'defaultColDef': MDS.get_ag_grid_default_def(),
            }).classes('w-full h-48 ag-theme-quartz-dark mb-4')

            async def recalculate_preview():
                selected_rows = await invoice_grid.get_selected_rows()
                pay_amount = to_float(payment_amount_ref.value)
                selected_total = round(sum(to_float(row.get('amount')) for row in selected_rows), 2)

                if pay_amount > max_allowed:
                    payment_amount_ref.set_value(max_allowed)
                    pay_amount = max_allowed

                if pay_amount > selected_total and selected_total > 0:
                    payment_amount_ref.set_value(selected_total)
                    pay_amount = selected_total

                allocations = allocate_payment_to_invoices(selected_rows, pay_amount) if selected_rows and pay_amount > 0 else []

                preview_grid.options['rowData'] = allocations
                preview_grid.update()

                selected_total_label.text = f'Total Selected: ${selected_total:.2f}'
                if selected_rows:
                    preview_label.text = f'Selected invoices total: ${selected_total:.2f} | Planned payment: ${pay_amount:.2f}'
                else:
                    preview_label.text = 'Select one or more pending purchase invoices.'

            invoice_grid.on('selectionChanged', lambda e: recalculate_preview())
            payment_amount_ref.on('update:model-value', lambda e: recalculate_preview())

            async def confirm_settlement():
                selected_rows = await invoice_grid.get_selected_rows()
                if not selected_rows:
                    ui.notify('Select at least one invoice', color='warning')
                    return

                pay_amount = to_float(payment_amount_ref.value)
                if pay_amount <= 0:
                    ui.notify('Payment amount must be greater than 0', color='warning')
                    return

                selected_total = round(sum(to_float(row.get('amount')) for row in selected_rows), 2)
                if pay_amount > selected_total:
                    ui.notify('Payment amount cannot exceed selected invoices total', color='warning')
                    return

                if pay_amount > to_float(supplier['balance']):
                    ui.notify('Payment amount cannot exceed supplier balance', color='warning')
                    return

                allocations = allocate_payment_to_invoices(selected_rows, pay_amount)
                if not allocations:
                    ui.notify('Nothing to pay for the selected invoices', color='warning')
                    return

                state['selected_invoices'] = allocations
                state['draft_amount'] = pay_amount
                state['draft_method'] = payment_method_ref.value or 'Cash'

                input_refs['amount'].set_value(f'{pay_amount:.2f}')
                if 'total' in input_refs:
                    input_refs['total'].set_value(f'{selected_total:.2f}')
                input_refs['method'].set_value(state['draft_method'])

                ui.notify(f'Payment prepared for {len(allocations)} invoice(s). Click Save to finalize.', color='positive')
                settlement_dialog.close()

            with ui.row().classes('w-full justify-end gap-4'):
                ModernButton('Cancel', on_click=settlement_dialog.close, variant='secondary')
                ModernButton('OK', on_click=confirm_settlement, variant='primary')

        settlement_dialog.open()

    def open_invoices_if_supplier_selected():
        if not state.get('new_mode'):
            ui.notify('Click New first', color='warning')
            return
        if state.get('selected_supplier'):
            open_settlement_dialog(state['selected_supplier'])
        else:
            ui.notify('Select supplier first, then click Balance or Amount to see pending invoices', color='warning')

    def process_payment():
        if not state['selected_supplier']:
            ui.notify('Select supplier first', color='negative')
            return

        # Refresh balance before payment check
        load_supplier_draft_balance()

        if not state.get('new_mode'):
            ui.notify('Click New before saving a new payment', color='warning')
            return

        try:
            supplier = state['selected_supplier']
            supplier_id = supplier['id']
            load_supplier_draft_balance()

            pay_amount = to_float(input_refs['amount'].value)
            payment_method = input_refs['method'].value or state.get('draft_method') or 'Cash'
            selected_invoices = state.get('selected_invoices', [])

            if pay_amount <= 0:
                ui.notify('Amount must be greater than 0', color='warning')
                return

            if pay_amount > to_float(supplier['balance']):
                ui.notify('Amount exceeds supplier balance', color='warning')
                return

            if not selected_invoices:
                ui.notify('Click Amount and choose pending purchase invoices before saving', color='warning')
                return

            allocated_total = round(sum(to_float(item.get('settlement_amount')) for item in selected_invoices), 2)
            if round(pay_amount, 2) != allocated_total:
                update_draft_amount_from_selected_invoices()
                ui.notify('Payment amount was adjusted to match invoice allocation. Click Save again.', color='warning')
                return

            sql = """
                INSERT INTO supplier_payment (supplier_id, amount, payment_date, payment_method, created_at, status)
                VALUES (?, ?, GETDATE(), ?, GETDATE(), 'completed')
            """
            connection.insertingtodatabase(sql, (supplier_id, pay_amount, payment_method))
            payment_id = connection.getid("SELECT MAX(id) FROM supplier_payment", [])
            state['draft_payment_id'] = payment_id

            for allocation in selected_invoices:
                invoice_id = allocation['id']
                invoice_total = to_float(allocation['amount'])
                settled_amount = to_float(allocation['settlement_amount'])
                remaining_amount = round(invoice_total - settled_amount, 2)
                new_status = 'completed' if remaining_amount <= 0 else 'pending'

                connection.insertingtodatabase(
                    "UPDATE purchases SET total_amount = ?, payment_status = ? WHERE id = ?",
                    (remaining_amount, new_status, invoice_id),
                )

            # Balance now dynamic from pending invoices, no manual update needed

            ui.notify(f'Payment saved: ${pay_amount:.2f}', color='positive')
            refresh_history()
            load_supplier_draft_balance()  # Refresh balance display
            clear_form(reset_supplier=False)  # Keep supplier selected
            exit_new_mode()

        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
    if standalone:
        layout_container = ModernPageLayout("Payable Management", standalone=standalone)
        layout_container.__enter__()
    
    try:
        with ui.row().classes('w-full gap-6 items-start animate-fade-in p-4'):
            # Left Column: Process Form
            with ui.column().classes('w-[360px] gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Disbursement Details').classes('text-[10px] font-black uppercase text-purple-400 tracking-widest mb-4')
                    with ui.column().classes('w-full gap-4'):
                        input_refs['supplier'] = ui.input('Supplier Entity').props('readonly rounded outlined dense').classes('w-full glass-input')
                        input_refs['supplier'].on('click', select_supplier)

                        input_refs['balance'] = ui.number('Supplier Balance (USD)', value=0).props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        input_refs['balance_ll'] = ui.number('Balance LL', value=0).props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        with ui.row().classes('items-center gap-2 mb-2'):
                            input_refs['currency'] = ui.select(['LL', 'USD'], value='USD', label='Pay from').classes('w-32')
                        
                        with ui.row().classes('w-full items-end gap-2 mt-2'):
                            input_refs['amount'] = ui.input('Amount', value='0.00').props('readonly rounded outlined dense').classes('flex-1 glass-input')
                            input_refs['amount'].on('click', open_invoices_if_supplier_selected)
                            ui.button(icon='search', on_click=open_invoices_if_supplier_selected).props('round dense color=primary').classes('mb-1')

                        input_refs['total'] = ui.input('Total', value='0.00').props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        input_refs['method'] = ui.select(
                            ['Cash', 'Card', 'Visa', 'OMT'],
                            value='Cash',
                            label='Disbursement Channel'
                        ).classes('w-full glass-input mt-2').props('rounded outlined dense')

            # Center Column: History
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Payment Register').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')
                    
                    cols = [
                        {'headerName': 'ID', 'field': 'id', 'width': 80},
                        {'headerName': 'Date', 'field': 'date', 'flex': 1},
                        {'headerName': 'Vendor', 'field': 'supplier', 'flex': 1.5},
                        {'headerName': 'Amount', 'field': 'amount', 'width': 110, 'valueFormatter': '"$" + x.toLocaleString()'},
                        {'headerName': 'Channel', 'field': 'method', 'width': 100}
                    ]
                    
                    with ui.column().classes('w-full relative'):
                        history_table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark shadow-inner')

                        history_overlay = ui.element('div').classes(
                            'absolute inset-0 bg-black/60 flex items-center justify-center z-20 text-white text-xl font-bold p-4 shadow-2xl'
                        ).style('backdrop-filter: blur(6px); pointer-events: none; position: absolute; top: 0; left: 0; right: 0; bottom: 0;')
                        with history_overlay:
                            ui.label('🆕 NEW MODE: Click Supplier → Amount → Choose Pending Purchase Invoices → Save')
                        history_overlay.set_visibility(False)

                        input_refs['history_overlay'] = history_overlay
                        input_refs['history_table'] = history_table

                    input_refs['history_overlay'] = history_overlay
                    input_refs['history_table'] = history_table

                    async def load_payment(e):
                        try:
                            row_data = await history_table.get_selected_row()
                            if not row_data or not isinstance(row_data, dict):
                                return
                            exit_new_mode()
                            supplier_id = row_data.get('supplier_id')
                            supplier_name = row_data['supplier']
                            if not supplier_id:
                                ui.notify('No supplier ID found', color='warning')
                                return
                            state['selected_supplier'] = {'id': supplier_id, 'name': supplier_name}
                            input_refs['supplier'].set_value(supplier_name)
                            input_refs['amount'].set_value(f'{to_float(row_data["amount"]):.2f}')
                            input_refs['method'].set_value(row_data['method'])
                            input_refs['total'].set_value(f'{to_float(row_data["amount"]):.2f}')
                            load_supplier_draft_balance()
                            ui.notify(f'✅ Loaded: {supplier_name} | Amount: ${to_float(row_data["amount"]):.2f} | Current Pending: ${state["selected_supplier"]["balance"]:.2f}')
                        except Exception as ex:
                            ui.notify(f'Load error: {ex}', color='warning')

                    history_table.on('cellClicked', load_payment)

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                def handle_new():
                    clear_form(reset_supplier=True)
                    set_new_mode(True)
                    ui.notify('New mode: Click Supplier → click Amount → choose invoices → click Save', color='positive')

                ModernActionBar(
                    on_new=handle_new,
                    on_save=process_payment,
                    on_undo=lambda: [clear_form(reset_supplier=True), exit_new_mode()],
                    on_refresh=refresh_history,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        ui.timer(0.1, refresh_history, once=True)
        
    finally:
        if standalone:
            layout_container.__exit__(None, None, None)


@ui.page('/supplierpayment')
def supplier_payment_page_route():
    supplier_payment_page(standalone=True)
