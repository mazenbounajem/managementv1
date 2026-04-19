from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

def supplier_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}

    def refresh_table():
        data = []
        sql = """
            SELECT 
                s.id, s.name, s.contact_person, s.email, s.phone, s.address, s.city, 
                s.balance as balance_ll, s.balance_usd,
                ISNULL(SUM(CASE WHEN p.payment_status = 'pending' THEN p.total_amount ELSE 0 END), 0) as pending_invoices,
                s.is_active 
            FROM suppliers s 
            LEFT JOIN purchases p ON p.supplier_id = s.id
            GROUP BY s.id, s.name, s.contact_person, s.email, s.phone, s.address, s.city, s.balance, s.balance_usd, s.is_active 
            ORDER BY s.id DESC
        """
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'name', 'contact', 'email', 'phone', 'address', 'city', 'balance_ll', 'balance_usd', 'pending_invoices', 'is_active']
        for r in data:
            row_dict = {cols[i]: r[i] for i in range(len(cols))}
            rows.append(row_dict)
        table.options['rowData'] = rows
        table.update()

    def clear_inputs():
        for k, ref in input_refs.items():
            if k == 'is_active': ref.set_value(True)
            elif k in ['balance_ll', 'balance_usd']: ref.set_value(0)
            else: ref.set_value('')
        if table:
            table.classes(add='dimmed')
            table.run_method('deselectAll')
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_new_mode()

    def save_supplier():
        try:
            s_data = {k: ref.value for k, ref in input_refs.items()}
            if not s_data['name']:
                return ui.notify('Name required', color='negative')

            if s_data['id']:
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM suppliers WHERE name=? AND id!=?", dup_chk, params=[s_data['name'], s_data['id']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A supplier with this name already exists', color='negative')
                    
                sql = """UPDATE suppliers SET name=?, contact_person=?, email=?, phone=?, 
                         address=?, city=?, balance=?, balance_usd=?, is_active=? WHERE id=?"""
                params = (s_data['name'], s_data['contact'], s_data['email'], s_data['phone'],
                          s_data['address'], s_data['city'], float(s_data['balance_ll'] or 0),
                          float(s_data['balance_usd'] or 0),
                          bool(s_data['is_active']), s_data['id'])
            else:
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM suppliers WHERE name=?", dup_chk, params=[s_data['name']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A supplier with this name already exists', color='negative')
                
                import accounting_helpers
                aux_number = accounting_helpers.get_next_auxiliary('4011')
                accounting_helpers.register_auxiliary(aux_number, s_data['name'])

                sql = """INSERT INTO suppliers (name, contact_person, email, phone, address, city, 
                         balance, balance_usd, created_at, is_active, auxiliary_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?)"""
                params = (s_data['name'], s_data['contact'], s_data['email'], s_data['phone'],
                          s_data['address'], s_data['city'], float(s_data['balance_ll'] or 0),
                          float(s_data['balance_usd'] or 0),
                          bool(s_data['is_active']), aux_number)

            connection.insertingtodatabase(sql, params)
            ui.notify('Supplier saved', color='positive')
            clear_inputs()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Supplier Management", standalone=standalone):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Redundant Horizontal Action Bar removed

            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Supplier Profile').classes('text-lg font-bold mb-4')
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['name'] = ModernInput('Company Name', icon='business').style('color: #c05884')
                        input_refs['contact'] = ModernInput('Contact Person', icon='person').style('color: #c05884')
                        input_refs['email'] = ModernInput('Email', icon='email').style('color: #c05884')
                        input_refs['phone'] = ModernInput('Phone', icon='phone').style('color: #c05884')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Address & Status').classes('text-lg font-bold mb-4')
                        input_refs['address'] = ui.input('Address').style('color: #c05884').props('outlined dense').classes('w-full')
                        input_refs['city'] = ui.input('City').style('color: #c05884').props('outlined dense').classes('w-full mt-2')
                        input_refs['balance_ll'] = ui.number('Balance LL').style('color: #c05884').props('outlined dense').classes('w-full mt-2')
                        input_refs['balance_usd'] = ui.number('Balance USD').style('color: #c05884').props('outlined dense').classes('w-full mt-2')
                        input_refs['is_active'] = ui.checkbox('Active', value=True).classes('mt-2')

                # Right Column: List
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        with ui.row().classes('w-full justify-between items-center mb-4 ml-2'):
                            ui.label('Supplier List').classes('text-lg font-bold')
                            with ui.row().classes('items-center bg-white/10 rounded-full px-3 py-1 shadow-sm border border-gray-300 dark:border-gray-600'):
                                ui.icon('search', color='gray').classes('text-lg')
                                search_input = ui.input(placeholder='Search suppliers...').props('borderless dense').classes('ml-2 w-64 text-sm outline-none')
                        
                        cols = [
                            {'headerName': 'Company', 'field': 'name', 'flex': 2},
                            {'headerName': 'Contact', 'field': 'contact', 'flex': 1},
                            {'headerName': 'Phone', 'field': 'phone', 'width': 130},
                            {'headerName': 'Balance LL', 'field': 'balance_ll', 'width': 130, 'valueFormatter': '"L.L. " + Number(params.value || 0).toLocaleString()'},
                            {'headerName': 'Balance USD', 'field': 'balance_usd', 'width': 110, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                            {'headerName': 'Pending Invoices', 'field': 'pending_invoices', 'width': 110, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                            {'headerName': 'Active', 'field': 'is_active', 'cellRenderer': 'agCheckboxRenderer'}
                        ]
                        
                        table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')
                        
                        search_input.on('update:model-value', lambda e: (
                            table.options.update({'quickFilterText': e.sender.value}),
                            table.update()
                        ))

                        async def on_row():
                            row = await table.get_selected_row()
                            if row:
                                for k in input_refs:
                                    if k in row: input_refs[k].set_value(row[k])
                                if table:
                                    table.classes(remove='dimmed')
                                if hasattr(footer_container, 'action_bar'):
                                    footer_container.action_bar.enter_edit_mode()
                        table.on('cellClicked', on_row)

                # Action Bar Panel (Right Side of Editor)
                with ui.column().classes('w-80px items-center') as footer_container:
                    def view_supplier_transactions():
                        import accounting_helpers
                        sid = input_refs['id'].value
                        if not sid:
                            ui.notify('Please select a supplier first', color='warning')
                            return
                        aux_data = []
                        connection.contogetrows(f"SELECT auxiliary_number FROM suppliers WHERE id={sid}", aux_data)
                        if aux_data and aux_data[0][0]:
                            accounting_helpers.show_transactions_dialog(account_number=aux_data[0][0])
                        else:
                            ui.notify('No accounting transactions found.', color='warning')

                    def delete_supplier():
                        sid = input_refs['id'].value
                        if not sid: return ui.notify('Select a supplier to delete', color='warning')
                        tx_chk = []
                        connection.contogetrows("SELECT COUNT(*) FROM purchases WHERE supplier_id=?", tx_chk, params=[sid])
                        if tx_chk and tx_chk[0][0] > 0:
                            return ui.notify('Cannot delete supplier with existing transactions. Delete them or set to inactive.', color='negative')
                        try:
                            connection.deleterow("DELETE FROM suppliers WHERE id=?", [sid])
                            ui.notify('Supplier deleted successfully', color='positive')
                            clear_inputs()
                            refresh_table()
                        except Exception as e:
                            ui.notify(f'Delete error: {e}', color='negative')

                    from modern_ui_components import ModernActionBar
                    footer_container.action_bar = ModernActionBar(
                        on_new=clear_inputs,
                        on_save=save_supplier,
                        on_undo=lambda: footer_container.action_bar.reset_state(),
                        on_delete=delete_supplier,
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        on_view_transaction=view_supplier_transactions,
                        on_refresh=refresh_table,
                        target_table=table,
                        button_class='h-16',
                        classes=' '
                    )
                    footer_container.action_bar.style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    ui.timer(0.1, refresh_table, once=True)


@ui.page('/suppliers')
def supplier_page_route():
    supplier_page()

