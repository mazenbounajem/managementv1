from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable, ModernActionBar
from session_storage import session_storage
from datetime import datetime
import datetime as dt
import asyncio
import accounting_helpers

def customer_receipt_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    state = {
        'selected_customer': None,
        'unpaid_invoices': [],
        'selected_invoices': [],
        'receipt_data': [],
        'new_mode': False,
        'draft_receipt_id': None,
        'draft_amount': 0.0,
        'draft_method': 'Cash',
    }
    input_refs = {}

    def to_float(value):
        try:
            return round(float(value or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    def calculate_customer_pending(customer_id):
        """Calculate total pending amount from unpaid sales invoices"""
        result = []
        sql = """
            SELECT SUM(ISNULL(total_amount, 0)) 
            FROM sales s 
            INNER JOIN customers c ON c.id = s.customer_id 
            WHERE c.id = ? AND s.payment_status = 'pending' AND ISNULL(s.total_amount, 0) > 0
        """
        connection.contogetrows(sql, result, (customer_id,))
        return to_float(result[0][0]) if result and result[0][0] is not None else 0.0

    async def refresh_history():
        data = []
        sql = """SELECT cr.id, cr.payment_date, c.customer_name, cr.amount, cr.payment_method, c.id as customer_id 
                 FROM customer_receipt cr
                 JOIN customers c ON cr.customer_id = c.id
                 ORDER BY cr.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        for r in data:
            rows.append({
                'id': r[0],
                'date': r[1],
                'customer': r[2],
                'amount': to_float(r[3]),
                'method': r[4],
                'customer_id': r[5],
            })
        history_table.options['rowData'] = rows
        history_table.update()
        await load_last_receipt()

    def fetch_customer_balance(customer_id):
        """Get accurate pending balance from unpaid invoices"""
        return calculate_customer_pending(customer_id)

    def clear_draft_state(reset_customer=True):
        state['selected_invoices'] = []
        state['draft_receipt_id'] = None
        state['draft_amount'] = 0.0
        state['draft_method'] = input_refs['method'].value if 'method' in input_refs else 'Cash'
        if reset_customer:
            state['selected_customer'] = None

    def clear_form(reset_customer=True):
        if 'customer' in input_refs:
            input_refs['customer'].set_value('')
        if 'balance' in input_refs:
            input_refs['balance'].set_value(0)
        if 'amount' in input_refs:
            input_refs['amount'].set_value(0)
        if 'method' in input_refs:
            input_refs['method'].set_value('Cash')
        clear_draft_state(reset_customer=reset_customer)

    def set_new_mode(enabled):
        state['new_mode'] = enabled
        if 'history_overlay' in input_refs:
            input_refs['history_overlay'].set_visibility(enabled)

    def exit_new_mode():
        set_new_mode(False)

    def load_customer_draft_balance():
        customer = state.get('selected_customer')
        if customer:
            current_balance = fetch_customer_balance(customer['id'])
            customer['balance'] = current_balance
            if 'balance' in input_refs:
                input_refs['balance'].set_value(current_balance)

    def update_draft_amount_from_selected_invoices():
        total = sum(to_float(item.get('settlement_amount')) for item in state['selected_invoices'])
        total = round(total, 2)
        state['draft_amount'] = total
        if 'amount' in input_refs:
            input_refs['amount'].set_value(total)

    def allocate_receipt_to_invoices(selected_rows, pay_amount):
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

    def select_customer():
        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select Customer').classes('text-xl font-bold mb-4')

            c_data = []
            connection.contogetrows(
                "SELECT id, customer_name, balance FROM customers ORDER BY customer_name",
                c_data,
            )
            c_rows = [{'id': r[0], 'name': r[1], 'balance': to_float(r[2])} for r in c_data]

            grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Name', 'field': 'name', 'flex': 1, 'filter': 'agTextColumnFilter'},
                    {'headerName': 'Account Balance', 'field': 'balance', 'width': 150, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                ],
                'rowData': c_rows,
                'rowSelection': 'single',
                'defaultColDef': {'sortable': True, 'filter': True},
            }).classes('w-full h-80 ag-theme-quartz-dark')

            async def confirm():
                row = await grid.get_selected_row()
                if row:
                    state['selected_customer'] = {
                        'id': row['id'],
                        'name': row['name'],
                        'balance': row['balance'],
                    }
                    input_refs['customer'].set_value(row['name'])
                    if 'balance' in input_refs:
                        # Use dynamic pending balance for the form display
                        pending = calculate_customer_pending(row['id'])
                        input_refs['balance'].set_value(pending)
                    input_refs['amount'].set_value('0.00')
                    state['selected_invoices'] = []
                    state['draft_amount'] = 0.0
                    if 'total' in input_refs:
                        input_refs['total'].set_value('0.00')
                    d.close()
                    ui.notify('Customer selected. Click Amount to open pending sales invoices.', color='positive')
                else:
                    ui.notify('Select a customer', color='warning')

            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ModernButton('Cancel', on_click=d.close, variant='secondary')
                ModernButton('Select', on_click=confirm)

        d.open()

    def open_settlement_dialog(customer):
        state['unpaid_invoices'] = []
        load_customer_draft_balance()

        invoices_data = []
        sql = """
            SELECT s.id, s.invoice_number, s.total_amount, s.sale_date, s.payment_status, c.customer_name
            FROM sales s
            INNER JOIN customers c ON c.id = s.customer_id
            WHERE s.payment_status = 'pending'
              AND c.id = ?
              AND ISNULL(s.total_amount, 0) > 0
            ORDER BY s.sale_date ASC, s.id ASC
        """
        connection.contogetrows(sql, invoices_data, (customer['id'],))

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
                'customer_name': r[5] or customer['name'],
            }
            rows.append(row)
            total_due += amount

        total_due = round(total_due, 2)
        state['unpaid_invoices'] = rows

        if not rows:
            ui.notify('No pending sales invoices for this customer', color='info')
            return

        with ui.dialog() as settlement_dialog, ModernCard().classes('w-full max-w-5xl p-8'):
            ui.label(f'Pending Sales Invoices: {customer["name"]}').classes('text-2xl font-bold mb-2 text-white')
            ui.label(f'Customer Pending Balance: ${to_float(calculate_customer_pending(customer["id"])):.2f}').classes('text-lg mb-1 text-green-400 font-bold')
            ui.label('Tick the checkbox rows you want to receipt. Only pending sales invoices for the selected customer are shown here.').classes('text-sm mb-4 text-yellow-300')

            ui.label('📋 Invoice Selection Table - Check invoices to settle').classes('text-base font-bold mb-2 text-blue-300')

            invoice_grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Select', 'checkboxSelection': True, 'headerCheckboxSelection': True, 'width': 80},
                    {'headerName': 'Invoice #', 'field': 'invoice_number', 'flex': 1},
                    {'headerName': 'Customer', 'field': 'customer_name', 'width': 180},
                    {'headerName': 'Date', 'field': 'date', 'width': 130},
                    {'headerName': 'Amount', 'field': 'amount', 'width': 130, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                    {'headerName': 'Status', 'field': 'status', 'width': 120},
                ],
                'rowData': rows,
                'rowSelection': 'multiple',
                'suppressRowClickSelection': True,
                'defaultColDef': MDS.get_ag_grid_default_def(),
            }).classes('w-full h-96 ag-theme-quartz-dark mb-6')

            with ui.row().classes('items-center gap-4 mb-2'):
                ui.label('Receipt Amount:').classes('font-bold')
                max_allowed = total_due # For sales, we can receive any amount up to total due
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
                    ['Cash', 'Card', 'Transfer', 'USD Cash'],
                    value=input_refs['method'].value or 'Cash',
                ).classes('w-40')

            selected_total_label = ui.label('Total Selected: $0.00').classes('text-md mb-4 text-blue-300 font-bold')

            ui.label('🔍 Receipt Allocation Preview Table - Shows how receipt distributes').classes('text-base font-bold mb-2 text-green-300')

            preview_label = ui.label('Choose invoices, adjust receipt amount if needed, then click OK.').classes('text-sm text-gray-300 mb-2')
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

                if pay_amount > selected_total and selected_total > 0:
                    payment_amount_ref.set_value(selected_total)
                    pay_amount = selected_total

                allocations = allocate_receipt_to_invoices(selected_rows, pay_amount) if selected_rows and pay_amount > 0 else []

                preview_grid.options['rowData'] = allocations
                preview_grid.update()

                selected_total_label.text = f'Total Selected: ${selected_total:.2f}'
                if selected_rows:
                    preview_label.text = f'Selected invoices total: ${selected_total:.2f} | Planned receipt: ${pay_amount:.2f}'
                else:
                    preview_label.text = 'Select one or more pending sales invoices.'

            invoice_grid.on('selectionChanged', lambda e: recalculate_preview())
            payment_amount_ref.on('update:model-value', lambda e: recalculate_preview())

            async def confirm_settlement():
                selected_rows = await invoice_grid.get_selected_rows()
                if not selected_rows:
                    ui.notify('Select at least one invoice', color='warning')
                    return

                pay_amount = to_float(payment_amount_ref.value)
                if pay_amount <= 0:
                    ui.notify('Receipt amount must be greater than 0', color='warning')
                    return

                selected_total = round(sum(to_float(row.get('amount')) for row in selected_rows), 2)
                if pay_amount > selected_total:
                    ui.notify('Receipt amount cannot exceed selected invoices total', color='warning')
                    return

                allocations = allocate_receipt_to_invoices(selected_rows, pay_amount)
                if not allocations:
                    ui.notify('Nothing to receipt for the selected invoices', color='warning')
                    return

                state['selected_invoices'] = allocations
                state['draft_amount'] = pay_amount
                state['draft_method'] = payment_method_ref.value or 'Cash'

                input_refs['amount'].set_value(f'{pay_amount:.2f}')
                if 'total' in input_refs:
                    input_refs['total'].set_value(f'{selected_total:.2f}')
                input_refs['method'].set_value(state['draft_method'])

                ui.notify(f'Receipt prepared for {len(allocations)} invoice(s). Click Save to finalize.', color='positive')
                settlement_dialog.close()

            with ui.row().classes('w-full justify-end gap-4'):
                ModernButton('Cancel', on_click=settlement_dialog.close, variant='secondary')
                ModernButton('OK', on_click=confirm_settlement, variant='primary')

        settlement_dialog.open()

    def open_invoices_if_customer_selected():
        if not state.get('new_mode'):
            ui.notify('Click New first', color='warning')
            return
        if state.get('selected_customer'):
            open_settlement_dialog(state['selected_customer'])
        else:
            ui.notify('Select customer first, then click Amount to see pending invoices', color='warning')

    async def process_receipt():
        if not state['selected_customer']:
            ui.notify('Select customer first', color='negative')
            return

        # Refresh balance before check
        load_customer_draft_balance()

        if not state.get('new_mode'):
            ui.notify('Click New before saving a new receipt', color='warning')
            return

        try:
            customer = state['selected_customer']
            customer_id = customer['id']
            load_customer_draft_balance()

            pay_amount = to_float(input_refs['amount'].value)
            payment_method = input_refs['method'].value or state.get('draft_method') or 'Cash'
            selected_invoices = state.get('selected_invoices', [])

            if pay_amount <= 0:
                ui.notify('Amount must be greater than 0', color='warning')
                return

            if not selected_invoices:
                ui.notify('Click Amount and choose pending sales invoices before saving', color='warning')
                return

            allocated_total = round(sum(to_float(item.get('settlement_amount')) for item in selected_invoices), 2)
            if round(pay_amount, 2) != allocated_total:
                update_draft_amount_from_selected_invoices()
                ui.notify('Receipt amount was adjusted to match invoice allocation. Click Save again.', color='warning')
                return

            # Insert receipt record
            sql = """
                INSERT INTO customer_receipt (customer_id, amount, payment_date, payment_method, created_at)
                VALUES (?, ?, GETDATE(), ?, GETDATE())
            """
            connection.insertingtodatabase(sql, (customer_id, pay_amount, payment_method))
            receipt_id = connection.getid("SELECT MAX(id) FROM customer_receipt", [])
            state['draft_receipt_id'] = receipt_id

            # Update invoices
            for allocation in selected_invoices:
                invoice_id = allocation['id']
                invoice_total = to_float(allocation['amount'])
                settled_amount = to_float(allocation['settlement_amount'])
                remaining_amount = round(invoice_total - settled_amount, 2)
                new_status = 'completed' if remaining_amount <= 0 else 'pending'

                connection.insertingtodatabase(
                    "UPDATE sales SET total_amount = ?, payment_status = ?, payment_method = ? WHERE id = ?",
                    (remaining_amount, new_status, payment_method, invoice_id),
                )

            # Update customer balance
            connection.insertingtodatabase(
                "UPDATE customers SET balance = balance - ? WHERE id = ?",
                (pay_amount, customer_id)
            )

            # --- Accounting Entry: DR Cash / CR Customer Auxiliary ---
            try:
                import accounting_helpers
                cust_aux_res = []
                connection.contogetrows(
                    "SELECT auxiliary_number FROM customers WHERE id = ?", cust_aux_res, (customer_id,)
                )
                cust_aux = cust_aux_res[0][0] if cust_aux_res and cust_aux_res[0][0] else '4111.000001'
                accounting_helpers.save_accounting_transaction(
                    reference_type='Receipt',
                    reference_id=str(receipt_id),
                    lines=[
                        {'account': '5300.000001', 'debit': pay_amount, 'credit': 0},
                        {'account': cust_aux,      'debit': 0, 'credit': pay_amount},
                    ],
                    description=f"Customer Receipt #{receipt_id} - {customer['name']}"
                )
                
                # --- Cash Drawer Integration ---
                connection.update_cash_drawer_balance(
                    amount=pay_amount,
                    operation_type='In',
                    user_id=user.get('user_id'),
                    notes=f"Customer Receipt #{receipt_id} - {customer['name']}"
                )
            except Exception as acc_err:
                print(f"Accounting/CashDrawer error in customer receipt: {acc_err}")

            ui.notify(f'Receipt saved: ${pay_amount:.2f}', color='positive')
            await refresh_history()
            await load_last_receipt()
            exit_new_mode()
            if history_table:
                history_table.classes(remove='dimmed')

        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    # Wrap content in ModernPageLayout
    if standalone:
        layout_container = ModernPageLayout("Revenue Collection", standalone=standalone)
        layout_container.__enter__()
    
    try:
        with ui.row().classes('w-full gap-6 items-start animate-fade-in p-4'):
            # Left Column: Process Form
            with ui.column().classes('w-[360px] gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Deposit Details').classes('text-[10px] font-black uppercase text-purple-400 tracking-widest mb-4')
                    with ui.column().classes('w-full gap-4'):
                        input_refs['customer'] = ui.input('Customer Account').props('readonly rounded outlined dense').classes('w-full glass-input')
                        input_refs['customer'].on('click', select_customer)

                        input_refs['balance'] = ui.number('Pending Balance (USD)', value=0).props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        with ui.row().classes('w-full items-end gap-2 mt-2'):
                            input_refs['amount'] = ui.input('Receipt Amount', value='0.00').props('readonly rounded outlined dense').classes('flex-1 glass-input')
                            input_refs['amount'].on('click', open_invoices_if_customer_selected)
                            ui.button(icon='search', on_click=open_invoices_if_customer_selected).props('round dense color=primary').classes('mb-1')

                        input_refs['total'] = ui.input('Selected Total', value='0.00').props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        input_refs['method'] = ui.select(
                            ['Cash', 'Card', 'Transfer', 'USD Cash'],
                            value='Cash',
                            label='Collection Channel'
                        ).classes('w-full glass-input mt-2').props('rounded outlined dense')

            # Center Column: History
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Revenue Register').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')
                    
                    cols = [
                        {'headerName': 'ID', 'field': 'id', 'width': 80},
                        {'headerName': 'Date', 'field': 'date', 'flex': 1},
                        {'headerName': 'Customer', 'field': 'customer', 'flex': 1.5},
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
                            ui.label('🆕 NEW MODE: Click Customer → Amount → Choose Pending Sales Invoices → Save')
                        history_overlay.set_visibility(False)

                        input_refs['history_overlay'] = history_overlay
                        input_refs['history_table'] = history_table

                    async def on_cell_clicked(e):
                        if e.args.get('data'):
                            await perform_load_row(e.args['data'])

                    async def load_last_receipt():
                        await asyncio.sleep(0.1)
                        if history_table.options.get('rowData'):
                            first_row = history_table.options['rowData'][0]
                            await perform_load_row(first_row)

                    async def perform_load_row(row_data):
                        try:
                            exit_new_mode()
                            customer_id = row_data.get('customer_id')
                            customer_name = row_data.get('customer')
                            if not customer_id:
                                return
                            state['selected_customer'] = {'id': customer_id, 'name': customer_name}
                            input_refs['customer'].set_value(customer_name or '')
                            input_refs['amount'].set_value(f'{to_float(row_data.get("amount", 0)):.2f}')
                            input_refs['method'].set_value(row_data.get('method', 'Cash'))
                            input_refs['total'].set_value(f'{to_float(row_data.get("amount", 0)):.2f}')
                            load_customer_draft_balance()
                        except Exception as ex:
                            print(f"Load error: {ex}")

                    history_table.on('cellClicked', on_cell_clicked)

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                def handle_new():
                    clear_form(reset_customer=True)
                    set_new_mode(True)
                    ui.notify('New mode: Click Customer → click Amount → choose invoices → click Save', color='positive')

                ModernActionBar(
                    on_new=handle_new,
                    on_save=process_receipt,
                    on_undo=lambda: [clear_form(reset_customer=True), exit_new_mode()],
                    on_refresh=refresh_history,
                    on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                    on_view_transaction=lambda: (
                        accounting_helpers.show_transactions_dialog(
                            reference_type='Receipt',
                            reference_id=str(state['draft_receipt_id'])
                        ) if state.get('draft_receipt_id')
                        else ui.notify('Select a receipt to view its transaction', color='warning')
                    ),
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        ui.timer(0.1, refresh_history, once=True)
        ui.timer(0.2, load_last_receipt, once=True)
        
    finally:
        if standalone:
            layout_container.__exit__(None, None, None)


@ui.page('/customerreceipt')
def customer_receipt_page_route():
    customer_receipt_page(standalone=True)