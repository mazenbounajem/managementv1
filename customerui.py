from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime
import base64
import io

def customer_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}
    table = None
    footer_container = None
    # Removed customer_photos cache to keep memory lightweight

    def to_float(value):
        try:
            return round(float(value or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    def handle_photo_upload(e):
        try:
            content = e.content.read()
            # Determine mime type or just assume png/jpeg
            base64_str = base64.b64encode(content).decode('ascii')
            mime_type = "image/png" # Default, could be refined
            input_refs['photo'].set_value(f"data:{mime_type};base64,{base64_str}")
            photo_preview.set_source(f"data:{mime_type};base64,{base64_str}")
            ui.notify('Photo uploaded', color='positive')
            e.sender.reset() # Clear the upload list
        except Exception as ex:
            ui.notify(f'Upload error: {ex}', color='negative')

    def remove_photo():
        input_refs['photo'].set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in input_refs:
            input_refs['uploader'].reset()
        ui.notify('Photo removed from form')

    # Table state for ui.table (replaces ag-grid)
    _all_rows = []
    _selected_row_index = None
    _selected_row_id = None
    _filter_status = ''
    _filter_text = ''

    def refresh_table():
        nonlocal _all_rows, _selected_row_index, _selected_row_id
        data = []
        sql = """SELECT id, customer_name, email, phone, address, city, balance, is_active, 
                 CASE WHEN photo IS NOT NULL AND photo != '' THEN 1 ELSE 0 END as has_photo,
                 instagram, facebook, twitter, tiktok,
                 COALESCE((SELECT SUM(ISNULL(s.total_amount, 0)) FROM sales s WHERE s.customer_id = c.id AND s.payment_status = 'pending'), 0)
                 - COALESCE((SELECT SUM(ISNULL(r.total_amount, 0)) FROM sales_returns r WHERE r.customer_id = c.id AND r.payment_status = 'pending'), 0) as pending_sales,
                 is_default
                 FROM customers c ORDER BY id DESC"""
        connection.contogetrows(sql, data)

        rows = []
        for r in data:
            rows.append({
                'id': r[0],
                'customer_name': r[1],
                'email': r[2],
                'phone': r[3],
                'address': r[4],
                'city': r[5],
                'balance': r[6],
                'is_active': r[7],
                'has_photo': bool(r[8]),
                'instagram': r[9],
                'facebook': r[10],
                'twitter': r[11],
                'tiktok': r[12],
                'pending_sales': to_float(r[13]),
                'is_default': bool(r[14]),
            })

        _all_rows = rows
        _selected_row_index = None
        _selected_row_id = None

        if table:
            table.rows = rows
            table.update()
            _load_last_row()

    def filter_table(query: str = None, status_filter: str = None):
        nonlocal _all_rows, _selected_row_index, _selected_row_id, _filter_status, _filter_text
        if query is not None:
            _filter_text = query
        if status_filter is not None:
            _filter_status = status_filter
        q = (_filter_text if query is None else query or '').strip().lower()
        st = (_filter_status if status_filter is None else status_filter or '').strip().lower()
        if not table:
            return
        filtered = []
        for r in (_all_rows or []):
            if q and q not in str(r.get('name') or '').lower() and q not in str(r.get('email') or '').lower() and q not in str(r.get('phone') or '').lower() and q not in str(r.get('city') or '').lower():
                continue
            if st:
                is_active = bool(r.get('is_active'))
                if st == 'active' and not is_active:
                    continue
                if st == 'inactive' and is_active:
                    continue
            filtered.append(r)
        table.rows = filtered
        table.update()
        table.classes(remove='dimmed')
        if filtered:
            _apply_row_from_id(filtered[0].get('id'))

    def _apply_selected_row_color():
        if _selected_row_index is None:
            return

        idx = _selected_row_index
        ui.run_javascript(f"""
        try {{
          const root = document.querySelector('.q-table');
          if (!root) return;

          const rows = root.querySelectorAll('tbody tr');
          if (!rows || rows.length === 0) return;

          const safeIdx = Math.max(0, Math.min({idx}, rows.length - 1));

          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});

          const selected = rows[safeIdx];
          if (selected) {{
            selected.style.backgroundColor = '#facc15';
            selected.style.color = 'black';
            selected.classList.add('selected-highlight');
          }}
        }} catch (e) {{ }}
        """)

    def _apply_row_from_id(cid):
        nonlocal _selected_row_index, _selected_row_id
        if not table:
            return
        rows = getattr(table, 'rows', None) or []
        target_index = next((i for i, r in enumerate(rows) if r.get('id') == cid), None)
        if target_index is None:
            return

        _selected_row_index = target_index
        _selected_row_id = cid

        row = rows[_selected_row_index]
        input_refs['id'].set_value(str(cid))
        for k in ['customer_name', 'email', 'phone', 'address', 'city', 'balance', 'is_active', 'instagram', 'facebook', 'twitter', 'tiktok', 'is_default']:
            if k in row:
                input_refs[k].set_value(row[k])

        photo_data = []
        connection.contogetrows(f"SELECT photo FROM customers WHERE id = {cid}", photo_data)
        full_photo = photo_data[0][0] if photo_data else None
        input_refs['photo'].set_value(full_photo or '')
        if full_photo:
            photo_preview.set_source(full_photo)
        else:
            photo_preview.set_source('https://via.placeholder.com/150')

        table.classes(remove='dimmed')
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_edit_mode()
        _apply_selected_row_color()

    def _focus_first_row_from_search():
        try:
            ui.run_javascript("""
            try {
              const root = document.querySelector('.q-table');
              if (root) { root.tabIndex = 0; root.focus(); }
            } catch (e) {}
            """)
            if table and getattr(table, 'rows', None) and len(table.rows) > 0:
                first_id = table.rows[0].get('id')
                if first_id is not None:
                    _apply_row_from_id(first_id)
        except:
            pass

    def clear_inputs():
        nonlocal _selected_row_index, _selected_row_id
        _selected_row_index = None
        _selected_row_id = None
        for k, ref in input_refs.items():
            if k == 'is_active':
                ref.set_value(True)
            elif k == 'is_default':
                ref.set_value(False)
            elif k == 'balance':
                ref.set_value(0)
            elif k == 'uploader':
                continue
            else:
                ref.set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in input_refs:
            input_refs['uploader'].reset()
        if table:
            table.classes(add='dimmed')
            try:
                table.run_method('deselectAll')
            except:
                pass
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_new_mode()

    def _load_last_row():
        """Load the most recent customer into the form and undim table"""
        if not table or not getattr(table, 'rows', None):
            return
        if not table.rows:
            return
        row = table.rows[0]
        cid = row['id']
        _apply_row_from_id(cid)

    def save_customer():
        try:
            c_data = {k: ref.value for k, ref in input_refs.items() if k != 'uploader'}
            if not c_data['customer_name']:
                return ui.notify('Customer name required', color='negative')

            if c_data['id']:
                # If setting this customer as default, uncheck others
                if bool(c_data['is_default']):
                    connection.insertingtodatabase("UPDATE customers SET is_default = 0")
                
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM customers WHERE customer_name=? AND id!=?", dup_chk, params=[c_data['customer_name'], c_data['id']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A customer with this name already exists', color='negative')
                    
                sql = """UPDATE customers SET customer_name=?, email=?, phone=?, address=?, 
                         city=?, balance=?, is_active=?, photo=?, instagram=?, facebook=?, twitter=?, tiktok=?, is_default=? WHERE id=?"""
                params = (c_data['customer_name'], c_data['email'], c_data['phone'], c_data['address'],
                          c_data['city'], float(c_data['balance'] or 0), bool(c_data['is_active']), 
                          c_data['photo'], c_data['instagram'], c_data['facebook'], c_data['twitter'], c_data['tiktok'],
                          bool(c_data['is_default']), c_data['id'])
            else:
                # If setting this customer as default, uncheck others
                if bool(c_data['is_default']):
                    connection.insertingtodatabase("UPDATE customers SET is_default = 0")
                
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM customers WHERE customer_name=?", dup_chk, params=[c_data['customer_name']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A customer with this name already exists', color='negative')

                import accounting_helpers

                # Compute next sequential suffix from AUXILIARY table for base 4111.
                # This guarantees uniqueness against auxiliary.number and auxiliary.auxiliary_id.
                def get_next_4111_aux_number():
                    max_seq_rows = []
                    connection.contogetrows(
                        """
                        SELECT MAX(
                            TRY_CAST(
                                SUBSTRING(number, CHARINDEX('.', number) + 1, 50) AS INT
                            )
                        )
                        FROM auxiliary
                        WHERE auxiliary_id = '4111' AND number LIKE '4111.%'
                        """,
                        max_seq_rows
                    )
                    max_seq = max_seq_rows[0][0] if max_seq_rows and max_seq_rows[0][0] is not None else 0
                    candidate_seq = int(max_seq) + 1

                    # If candidate already exists (legacy data), increment until free.
                    while True:
                        candidate_aux = f"4111.{candidate_seq}"
                        exists = []
                        connection.contogetrows(
                            "SELECT COUNT(*) FROM auxiliary WHERE number = ?",
                            exists,
                            params=[candidate_aux]
                        )
                        if exists and exists[0][0] == 0:
                            return candidate_aux
                        candidate_seq += 1

                # If Cash Client already exists, reuse its existing auxiliary_number to avoid duplicating the same customer.
                if c_data['customer_name'] == 'Cash Client':
                    existing_cash = []
                    connection.contogetrows(
                        "SELECT auxiliary_number FROM customers WHERE customer_name = ?",
                        existing_cash,
                        params=['Cash Client']
                    )
                    if existing_cash and existing_cash[0][0]:
                        aux_number = str(existing_cash[0][0]).strip()
                    else:
                        aux_number = get_next_4111_aux_number()
                        accounting_helpers.register_auxiliary(aux_number, 'Cash Client')
                else:
                    aux_number = get_next_4111_aux_number()
                    accounting_helpers.register_auxiliary(aux_number, c_data['customer_name'])

                sql = """INSERT INTO customers (customer_name, email, phone, address, city, balance, 
                         created_at, is_active, photo, instagram, facebook, twitter, tiktok, auxiliary_number, is_default) 
                         VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?, ?, ?, ?, ?)"""
                params = (c_data['customer_name'], c_data['email'], c_data['phone'], c_data['address'],
                          c_data['city'], float(c_data['balance'] or 0), bool(c_data['is_active']),
                          c_data['photo'], c_data['instagram'], c_data['facebook'], c_data['twitter'], c_data['tiktok'],
                          aux_number, bool(c_data['is_default']))

            connection.insertingtodatabase(sql, params)
            
            # Fetch the new customer ID to use for the VAT auxiliary
            new_id_data = []
            connection.contogetrows("SELECT MAX(id) FROM customers", new_id_data)
            new_id = new_id_data[0][0] if new_id_data and new_id_data[0][0] else None
            
            if new_id and c_data['customer_name'] and not c_data['id']:
                # Ensure the VAT auxiliary is created for the new customer
                import accounting_helpers
                aux_number = c_data.get('auxiliary_number') or new_id # Use the created one
                # Retrieve the full inserted row to get the exact auxiliary number if possible
                aux_fetch = []
                connection.contogetrows("SELECT auxiliary_number FROM customers WHERE id = ?", aux_fetch, params=[new_id])
                if aux_fetch and aux_fetch[0][0]:
                     aux_number = aux_fetch[0][0]
                accounting_helpers.ensure_vat_auxiliary('Customer', new_id, c_data['customer_name'], aux_number)
            
            ui.notify('Customer saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Customer Management", standalone=standalone):
        with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
            with ui.column().classes('flex-1 gap-4'):
                with ui.splitter(horizontal=True, value=40).classes('w-full h-[850px]') as splitter:
                    with splitter.before:
                        with ModernCard(glass=True).classes('w-full p-4'):
                            with ui.row().classes('w-full justify-between items-center mb-4 ml-2'):
                                ui.label('Client Repository').classes('text-lg font-bold')
                                with ui.row().classes('items-center bg-white/10 rounded-full px-3 py-1 shadow-sm border border-gray-300 dark:border-gray-600'):
                                    ui.icon('search', color='gray').classes('text-lg')
                                    search_input = ui.input(
                                        placeholder='Search customers...'
                                    ).props('borderless dense').classes('ml-2 w-64 text-sm outline-none')
                                    def make_status_filter():
                                        s = ui.select(['All', 'Active', 'Inactive'], label='Status', value='All').classes('w-32').props('outlined dense dark stack-label clearable')
                                        def on_change(e):
                                            nonlocal _filter_status
                                            val = e.sender.value if hasattr(e, 'sender') else (e.args if isinstance(e.args, str) else '')
                                            _filter_status = 'active' if val == 'Active' else ('inactive' if val == 'Inactive' else '')
                                            filter_table(status_filter=_filter_status)
                                        s.on('update:model-value', on_change)
                                    make_status_filter()

                            def on_search(e):
                                nonlocal _filter_text
                                _filter_text = e.sender.value if hasattr(e, 'sender') else (e.args if isinstance(e.args, str) else '')
                                filter_table(query=_filter_text)
                            search_input.on('update:model-value', on_search)

                            def _focus_first_row_from_search():
                                try:
                                    ui.run_javascript("""
                                    try {
                                      const root = document.querySelector('.q-table');
                                      if (root) { root.tabIndex = 0; root.focus(); }
                                    } catch (e) {}
                                    """)
                                    if table and getattr(table, 'rows', None) and len(table.rows) > 0:
                                        first_id = table.rows[0].get('id')
                                        if first_id is not None:
                                            _apply_row_from_id(first_id)
                                except:
                                    pass
                            search_input.on('keydown.down', lambda: _focus_first_row_from_search())

                            columns = [
                                {'name': 'customer_name', 'label': 'Name', 'field': 'customer_name', 'align': 'left', 'sortable': True},
                                {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left', 'sortable': True},
                                {'name': 'phone', 'label': 'Phone', 'field': 'phone', 'align': 'left', 'sortable': True},
                                {'name': 'pending_sales', 'label': 'Pending Balance', 'field': 'pending_sales', 'align': 'left', 'sortable': True},
                                {'name': 'balance', 'label': 'Account Balance', 'field': 'balance', 'align': 'left', 'sortable': True},
                                {'name': 'is_default', 'label': 'Default', 'field': 'is_default', 'align': 'left', 'sortable': True},
                                {'name': 'is_active', 'label': 'Status', 'field': 'is_active', 'align': 'left', 'sortable': True},
                            ]

                            table = ui.table(
                                columns=columns,
                                rows=[],
                                row_key='id',
                                selection='single',
                                pagination={'rowsPerPage': 10}
                            ).classes('w-full h-80 overflow-hidden').props('flat bordered dense')

                            def on_row_click(e):
                                row = None
                                try:
                                    row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                    if not isinstance(row, dict) and isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                        row = e.args[0]
                                except:
                                    pass
                                if not isinstance(row, dict):
                                    return
                                cid = row.get('id')
                                if cid is None:
                                    return
                                _apply_row_from_id(cid)

                            table.on('rowClick', on_row_click)

                            ui.run_javascript("""
                            try {
                              const root = document.querySelector('.q-table');
                              if (!root) return;
                              root.tabIndex = 0;
                              if (!root.__bb_cust_arrow_nav) {
                                root.__bb_cust_arrow_nav = true;
                                root.addEventListener('keydown', (ev) => {
                                  if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
                                  ev.preventDefault();
                                  const rows = root.querySelectorAll('tbody tr');
                                  const visibleRows = Array.from(rows).filter(r => r && r.offsetParent !== null);
                                  if (!visibleRows.length) return;
                                  let currentIndex = visibleRows.findIndex(r => r.classList && r.classList.contains('selected-highlight'));
                                  if (currentIndex < 0) currentIndex = 0;
                                  const nextIndex = ev.key === 'ArrowDown'
                                    ? Math.min(currentIndex + 1, visibleRows.length - 1)
                                    : Math.max(currentIndex - 1, 0);
                                  const target = visibleRows[nextIndex];
                                  if (target) target.click();
                                });
                              }
                            } catch (e) {}
                            """)

                    with splitter.after:
                        with ui.row().classes('w-full gap-4 pt-4'):
                            with ModernCard(glass=True).classes('w-[280px] p-6 flex flex-col items-center'):
                                ui.label('Photo Profile').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4 w-full text-center')
                                photo_preview = ui.image('https://via.placeholder.com/150').classes('w-32 h-32 rounded-full border-4 border-white/10 shadow-xl object-cover mb-4')
                                with ui.row().classes('w-full gap-2 mb-2'):
                                    input_refs['photo'] = ui.input().classes('hidden')
                                    input_refs['uploader'] = ui.upload(on_upload=handle_photo_upload, auto_upload=True).props('flat bordered dark dense label="Upload Photo" accept=".jpg,.png,.jpeg"').classes('flex-1')
                                    ui.button(icon='delete', on_click=remove_photo).props('flat round color=red').tooltip('Remove photo')

                            with ModernCard(glass=True).classes('flex-1 p-6'):
                                ui.label('Client Details').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                input_refs['id'] = ui.input('ID').props('readonly outlined dense dark').classes('hidden')
                                input_refs['customer_name'] = ModernInput('Full Name', icon='person')
                                input_refs['email'] = ModernInput('Email', icon='email')
                                input_refs['phone'] = ModernInput('Phone', icon='phone')

                            with ModernCard(glass=True).classes('w-[280px] p-6'):
                                ui.label('Social Accounts').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                input_refs['instagram'] = ModernInput('Instagram', icon='camera_alt', placeholder='@username')
                                input_refs['facebook'] = ModernInput('Facebook', icon='facebook')
                                input_refs['twitter'] = ModernInput('X (Twitter)', icon='close')
                                input_refs['tiktok'] = ModernInput('TikTok', icon='music_note')

                            with ModernCard(glass=True).classes('flex-1 p-6'):
                                ui.label('Profile Settings').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                input_refs['address'] = ui.input('Address').props('outlined dense dark').classes('w-full')
                                input_refs['city'] = ui.input('City').props('outlined dense dark').classes('w-full mt-2')
                                input_refs['balance'] = ui.number('Account Balance').props('outlined dense dark').classes('w-full mt-2')
                                with ui.row().classes('w-full items-center gap-4 mt-2'):
                                    input_refs['is_active'] = ui.checkbox('Active', value=True)
                                    input_refs['is_default'] = ui.checkbox('Default Sales Customer', value=False)

            with ui.column().classes('w-80px items-center shrink-0') as footer_container:
                def view_customer_transactions():
                    import accounting_helpers
                    cid = input_refs['id'].value
                    if not cid:
                        ui.notify('Please select a customer first', color='warning')
                        return
                    aux_data = []
                    connection.contogetrows(f"SELECT auxiliary_number FROM customers WHERE id={cid}", aux_data)
                    if aux_data and aux_data[0][0]:
                        accounting_helpers.show_transactions_dialog(account_number=aux_data[0][0])
                    else:
                        ui.notify('No accounting transactions found.', color='warning')

                def _show_statement():
                    cid = input_refs['id'].value
                    cname = input_refs['customer_name'].value
                    if not cid:
                        ui.notify('Please select a customer first', color='warning')
                        return
                    today = datetime.now()
                    default_from = f'{today.year}-01-01'
                    default_to = today.strftime('%Y-%m-%d')
                    from customer_reports import report_single_customer_statement
                    with ui.dialog() as dlg, ui.card().classes(
                            'w-full max-w-md glass p-6 border border-white/10').style(
                            'background: rgba(15,15,25,0.95); border-radius: 2rem;'):
                        ui.label('Statement of Account').classes(
                            'text-2xl font-black mb-6 text-white')
                        from_date = ui.input('From Date').classes(
                            'w-full glass-input').props('dark rounded outlined type=date')
                        from_date.value = default_from
                        to_date = ui.input('To Date').classes(
                            'w-full glass-input mt-3').props('dark rounded outlined type=date')
                        to_date.value = default_to
                        def generate():
                            dlg.close()
                            report_single_customer_statement(
                                from_date.value, to_date.value, int(cid), cname)
                        ui.button('Generate Statement', on_click=generate).classes(
                            'mt-6 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-8 py-3 rounded-xl font-bold w-full')
                    dlg.open()


                def delete_customer():
                    cid = input_refs['id'].value
                    if not cid: return ui.notify('Select a customer to delete', color='warning')
                    tx_chk = []
                    connection.contogetrows("SELECT COUNT(*) FROM sales WHERE customer_id=?", tx_chk, params=[cid])
                    if tx_chk and tx_chk[0][0] > 0:
                        return ui.notify('Cannot delete customer with existing transactions.', color='negative')
                    receipt_chk = []
                    connection.contogetrows("SELECT COUNT(*) FROM customer_receipt WHERE customer_id=?", receipt_chk, params=[cid])
                    if receipt_chk and receipt_chk[0][0] > 0:
                        return ui.notify('Cannot delete customer with existing receipts.', color='negative')
                    try:
                        connection.deleterow("DELETE FROM customers WHERE id=?", [cid])
                        ui.notify('Customer deleted successfully', color='positive')
                        clear_inputs()
                        refresh_table()
                    except Exception as e:
                        ui.notify(f'Delete error: {e}', color='negative')

                from modern_ui_components import ModernActionBar
                footer_container.action_bar = ModernActionBar(
                    on_new=clear_inputs,
                    on_save=save_customer,
                    on_undo=lambda: footer_container.action_bar.reset_state(),
                    on_delete=delete_customer,
                    on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                    on_refresh=refresh_table,
                    on_print=_show_statement,
                    on_print_special=lambda: __import__('customer_reports').open_print_special_dialog(
                        customer_id=int(input_refs['id'].value) if input_refs['id'].value else None,
                        customer_name=input_refs['customer_name'].value
                    ),
                    on_view_transaction=view_customer_transactions,
                    target_table=table,
                    button_class='h-16',
                    classes=' '
                )
                footer_container.action_bar.style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
    refresh_table()


@ui.page('/customers')
def customer_page_route():
    customer_page()
