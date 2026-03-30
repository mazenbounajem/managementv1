from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernActionBar
from uiaggridtheme import uiAggridTheme
from session_storage import session_storage
from datetime import datetime


def customer_receipt_page(standalone=False):
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    state = {
        'selected_customer': None,
        'unpaid_invoices': [],
        'selected_invoices': [],
        'new_mode': False,
        'draft_receipt_id': None,
        'draft_amount': 0.0,
        'draft_method': 'Cash',
    }
    input_refs = {}
    
    # Dialog references
    customer_dialog = None
    invoice_dialog = None
    invoice_table = None
    invoice_dialog_label = None
    total_label = None

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
        try:
            data = []
            sql = """
                SELECT cr.id, cr.payment_date, c.customer_name, cr.amount, cr.payment_method, c.id as customer_id
                FROM customer_receipt cr
                JOIN customers c ON cr.customer_id = c.id
                ORDER BY cr.id DESC
            """
            connection.contogetrows(sql, data)
            rows = []
            for r in data:
                rows.append({
                    'id': r[0],
                    'date': r[1],
                    'customer': r[2],
                    'amount': to_float(r[3]),                   'method': r[4],                  'customer_id': r[5],              })
            if 'history_table' in input_refs:
                input_refs['history_table'].options['rowData'] = rows
                input_refs['history_table'].update()
        except Exception as e:
            ui.notify(f'History refresh error: {e}', color='warning')

    def fetch_customer_balance(customer_id):
        """Get accurate pending balance from unpaid sales invoices"""
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
        total = sum(to_float(item.get('total_amount')) for item in state['selected_invoices'])
        total = round(total, 2)
        state['draft_amount'] = total
        if 'amount' in input_refs:
            input_refs['amount'].set_value(total)

    def open_customer_dialog():
        nonlocal customer_dialog
        with ui.dialog() as dialog:
            customer_dialog = dialog
            with ModernCard().classes('w-full max-w-2xl p-6'):
                ui.label('Select Customer').classes('text-xl font-bold mb-4')

                # Fetch customers with balance > 0
                c_data = []
                connection.contogetrows(
                    "SELECT id, customer_name, phone, balance FROM customers WHERE balance > 0 ORDER BY customer_name",
                    c_data,
                )
                
                headers = ['id', 'customer_name', 'phone', 'balance']
                columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                
                rows = []
                for row in c_data:
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if header == 'balance':
                            row_dict[header] = to_float(row[i])
                        else:
                            row_dict[header] = row[i]
                    rows.append(row_dict)
                
                # Create search input
                search_input = ui.input('Search').classes('w-full mb-4')
                
                # Create table
                table = ui.table(columns=columns, rows=rows, pagination=10).classes('w-full')
                search_input.bind_value(table, 'filter')
                
                def on_row_click(e):
                    selected_row = e.args[1]
                    state['selected_customer'] = {
                        'id': selected_row['id'],
                        'name': selected_row['customer_name'],
                        'balance': to_float(selected_row['balance']),
                    }
                    input_refs['customer'].set_value(selected_row['customer_name'])
                    if 'balance' in input_refs:
                        input_refs['balance'].set_value(to_float(selected_row['balance']))
                    input_refs['amount'].set_value('0.00')
                    state['selected_invoices'] = []
                    state['draft_amount'] = 0.0
                    dialog.close()
                    ui.notify('Customer selected. Click Amount to open pending invoices.', color='positive')
                
                table.on('rowClick', on_row_click)
                
                with ui.row().classes('w-full justify-end mt-4'):
                    ModernButton('Close', on_click=dialog.close, variant='secondary')
        
        dialog.open()

    def open_invoice_dialog(search_term=None):
        """Open invoice selection dialog - shows PAID invoices if receipt selected, PENDING if new"""
        if not state.get('selected_customer') or not state['selected_customer'].get('id'):
                                    ui.notify('Please select a customer first', color='warning')
                                    return
        
        # Toggle: paid invoices if viewing receipt, pending if new mode
        status_filter = 'completed' if not state.get('new_mode') else 'pending'
        dialog_title = f'{"Paid" if status_filter == "completed" else "Pending"} Invoices for {state["selected_customer"]["name"]}'
        
        nonlocal invoice_dialog, invoice_table, invoice_dialog_label, total_label
        
        # Fetch pending invoices for the selected customer
        invoices_data = []
        sql = """
            SELECT s.id, s.invoice_number, s.total_amount, s.sale_date, s.payment_status
            FROM sales s 
            WHERE s.customer_id = ? AND s.payment_status = ?
            ORDER BY s.sale_date ASC, s.id ASC
        """
        connection.contogetrows(sql, invoices_data, (state['selected_customer']['id'], status_filter))
        
        if not invoices_data:
            ui.notify('No pending invoices found for this customer', color='warning')
            return
        
        # Convert to list of dictionaries
        invoices = []
        for row in invoices_data:
            invoice_dict = {
                'id': row[0],
                'invoice_number': row[1],
                'total_amount': to_float(row[2]),
                'sale_date': str(row[3]),
                'payment_status': row[4] or 'pending'
            }
            invoices.append(invoice_dict)
        
        # Create or update the dialog
        with ui.dialog() as dialog:
            invoice_dialog = dialog
            with ModernCard().classes('w-full max-w-6xl p-8'):
                invoice_dialog_label = ui.label(dialog_title).classes('text-2xl font-bold mb-4 text-white')
                ui.label('Invoice Selection Table - Check invoices to settle').classes('text-sm mb-4 text-gray-300')
                        
                invoice_selection_label = ui.label('(Upper Table: Select invoices) | (Lower Table: Payment Preview)').classes('text-xs text-yellow-300 mb-2 italic')
                
                # Create AG Grid with checkboxes for invoice selection
                column_defs = [
                    {'headerName': 'Select', 'checkboxSelection': True, 'headerCheckboxSelection': True, 'width': 80},
                    {'headerName': 'Invoice #', 'field': 'invoice_number', 'flex': 2},
                    {'headerName': 'Amount', 'field': 'total_amount', 'width': 120, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                    {'headerName': 'Date', 'field': 'sale_date', 'width': 120},
                    {'headerName': 'Status', 'field': 'payment_status', 'width': 100},
                ]
                
                invoice_table = ui.aggrid({
                    'columnDefs': column_defs,
                    'rowData': invoices,
                    'rowSelection': 'multiple',
                    'suppressRowClickSelection': True,
                    'defaultColDef': MDS.get_ag_grid_default_def(),
                }).classes('w-full h-96 ag-theme-quartz-dark mb-4')
                
                preview_label = ui.label('Payment Allocation Preview Table').classes('text-sm text-gray-300 mb-2 font-bold text-purple-300')
                total_label = ui.label('Total Selected: $0.00').classes('text-lg font-bold mt-2 text-blue-300')
                
                async def update_total():
                    try:
                        selected_rows = await invoice_table.get_selected_rows()
                        state['selected_invoices'] = selected_rows
                        total = sum(float(inv['total_amount']) for inv in selected_rows)
                        total_label.text = f'Total Selected: ${total:.2f}'
                    except Exception as e:
                        ui.notify(f'Error calculating total: {str(e)}', color='warning')
                
                invoice_table.on('selectionChanged', lambda e: update_total())
                
                def confirm_selection():
                    if state['selected_invoices']:
                        total = sum(float(inv['total_amount']) for inv in state['selected_invoices'])
                        input_refs['amount'].set_value(f'{total:.2f}')
                        if 'total' in input_refs:
                            input_refs['total'].set_value(f'{total:.2f}')
                        dialog.close()
                        ui.notify(f'Selected {len(state["selected_invoices"])} invoices, Total: ${total:.2f}. Click Save to finalize.', color='positive')
                    else:
                        ui.notify('Please select at least one invoice', color='warning')
                
                with ui.row().classes('w-full justify-end gap-4 mt-4'):
                    ModernButton('Cancel', on_click=dialog.close, variant='secondary')
                    ModernButton('OK', on_click=confirm_selection, variant='primary')
        
        dialog.open()

    def process_receipt():
        if not state['selected_customer']:
            ui.notify('Select customer first', color='negative')
            return

        if not state.get('new_mode'):
            ui.notify('Click New before saving a new settlement', color='warning')
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

            if pay_amount > to_float(customer['balance']):
                ui.notify('Amount exceeds customer balance', color='warning')
                return

            if not selected_invoices:
                ui.notify('Click Amount and choose pending invoices before saving', color='warning')
                return

            # Calculate total from selected invoices
            invoices_total = sum(to_float(inv.get('total_amount')) for inv in selected_invoices)
            if round(pay_amount, 2) != round(invoices_total, 2):
                ui.notify('Amount must match the total of selected invoices', color='warning')
                return

            # Insert receipt record
            receipt_sql = """
                INSERT INTO customer_receipt (customer_id, amount, payment_date, payment_method, created_at)
                VALUES (?, ?, GETDATE(), ?, GETDATE())
            """
            connection.insertingtodatabase(receipt_sql, (customer_id, pay_amount, payment_method))
            receipt_id = connection.getid("SELECT MAX(id) FROM customer_receipt", [])
            state['draft_receipt_id'] = receipt_id

            # Update each invoice
            for invoice in selected_invoices:
                invoice_id = invoice['id']
                
                # Update sales status to completed
                connection.insertingtodatabase(
                    "UPDATE sales SET payment_status = 'completed', payment_method = ? WHERE id = ?",
                    (payment_method, invoice_id),
                )

            # No manual customer balance update - use dynamic pending calculation
            # refresh_history() called for table update
            load_customer_draft_balance()  # Update display with new pending sum

            ui.notify(f'Settlement saved: ${pay_amount:.2f}', color='positive')
            refresh_history()
            clear_form(reset_customer=True)
            exit_new_mode()

        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    if standalone:
        layout_container = ModernPageLayout("Revenue Collection", standalone=standalone)
        layout_container.__enter__()

    try:
        with ui.row().classes('w-full gap-6 items-start animate-fade-in'):
            with ui.column().classes('w-[360px] gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Deposit Details').classes('text-[10px] font-black uppercase text-purple-400 tracking-widest mb-4')
                    with ui.column().classes('w-full gap-4'):
                        input_refs['customer'] = ui.input('Customer').props('readonly rounded outlined dense').classes('w-full glass-input')
                        input_refs['customer'].on('click', open_customer_dialog)

                        input_refs['balance'] = ui.number('Customer Balance (USD)', value=0).props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        with ui.row().classes('w-full items-end gap-2 mt-2'):
                            input_refs['amount'] = ui.input('Amount', value='0.00').props('readonly rounded outlined dense').classes('flex-1 glass-input')
                            input_refs['amount'].on('click', open_invoice_dialog)
                            ui.button(icon='search', on_click=open_invoice_dialog).props('round dense color=primary').classes('mb-1')

                        input_refs['total'] = ui.input('Total', value='0.00').props('readonly rounded outlined dense').classes('w-full glass-input mt-2')

                        input_refs['method'] = ui.select(
                            ['Cash', 'Card', 'Transfer', 'USD Cash'],
                            value='Cash',
                            label='Payment Channel',
                        ).classes('w-full glass-input mt-2').props('rounded outlined dense')


            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Receipt Ledger').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')

                    cols = [
                        {'headerName': 'ID', 'field': 'id', 'width': 80},
                        {'headerName': 'Settlement Date', 'field': 'date', 'flex': 1},
                        {'headerName': 'Customer', 'field': 'customer', 'flex': 1.5},
                        {'headerName': 'Amount (USD)', 'field': 'amount', 'width': 140, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                        {'headerName': 'Method', 'field': 'method', 'width': 120},
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
                            ui.label('🆕 NEW MODE: Click Customer → Click Amount → Choose Pending Invoices → Save')
                        history_overlay.set_visibility(False)

                        input_refs['history_overlay'] = history_overlay
                        input_refs['history_table'] = history_table

                        async def load_receipt(e):
                            try:
                                selected_row = await input_refs['history_table'].get_selected_row()
                                if not selected_row:
                                    return
                                row_data = selected_row
                                
                                # Exit new mode for viewing
                                exit_new_mode()
                                
                                if customer_id:
                                    current_balance = fetch_customer_balance(customer_id)
                                    cust_data = []
                                    connection.contogetrows("SELECT customer_name FROM customers WHERE id = ?", cust_data, (customer_id,))
                                    customer_name = cust_data[0][0] if cust_data else 'Unknown'
                                    
                                    input_refs['customer'].set_value(customer_name)
                                    input_refs['balance'].set_value(current_balance)
                                
                                # Load receipt details
                                input_refs['amount'].set_value(f'{to_float(row_data["amount"]):.2f}')
                                if 'total' in input_refs:
                                    input_refs['total'].set_value(f'{to_float(row_data["amount"]):.2f}')
                                input_refs['method'].set_value(row_data['method'])
                                
                                ui.notify(f'Loaded receipt: ${row_data["amount"]:.2f} | Balance: ${input_refs["balance"].value if "balance" in input_refs else 0:.2f}', color='positive')
                                
                                if customer_id:
                                    # Load customer details
                                    cust_data = []
                                    connection.contogetrows("SELECT customer_name, balance FROM customers WHERE id = ?", cust_data, (customer_id,))
                                    if cust_data:
                                        cust_row = cust_data[0]
                                        input_refs['customer'].set_value(cust_row[0])
                                        input_refs['balance'].set_value(to_float(cust_row[1]))
                                
                                # Load receipt details
                                input_refs['amount'].set_value(f'{to_float(row_data["amount"]):.2f}')
                                if 'total' in input_refs:
                                    input_refs['total'].set_value(f'{to_float(row_data["amount"]):.2f}')
                                input_refs['method'].set_value(row_data['method'])
                                
                                ui.notify(f'Loaded receipt: ${row_data["amount"]:.2f} | Balance: ${input_refs["balance"].value if "balance" in input_refs else 0:.2f}')
                            except Exception as ex:
                                ui.notify(f'Load error: {ex}', color='warning')

                        history_table.on('cellClicked', load_receipt)

            with ui.column().classes('w-80px items-center'):
                def handle_new():
                    clear_form(reset_customer=True)
                    set_new_mode(True)
                    ui.notify('New mode: Click Customer → Click Amount → choose invoices → click Save', color='positive')

                ModernActionBar(
                    on_new=handle_new,
                    on_save=process_receipt,
                    on_undo=lambda: [clear_form(reset_customer=True), exit_new_mode()],
                    on_refresh=refresh_history,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    button_class='h-16',
                    classes=' ',
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        # Safe AG-Grid theme + delayed init (FIXES RACE)
        uiAggridTheme.addingtheme()
        ui.timer(1.0, refresh_history, once=True)

    finally:
        if standalone:
            layout_container.__exit__(None, None, None)


@ui.page('/customerreceipt')
def customer_receipt_page_route():
    customer_receipt_page(standalone=True)