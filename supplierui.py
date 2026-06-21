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

    input_refs = {}
    table = None
    footer_container = None

    _all_rows = []
    _selected_row_index = None
    # Back-compat for existing helpers that refer to id
    _selected_row_id = None

    _filter_text = ''
    _filter_status = ''

    def refresh_table():
        nonlocal _all_rows, _selected_row_index, _selected_row_id
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
            rows.append({cols[i]: r[i] for i in range(len(cols))})

        _all_rows = rows
        if table:
            table.rows = rows
            table.update()
            _load_last_row()

    def _load_last_row():
        nonlocal _selected_row_index, _selected_row_id
        if not table or not getattr(table, 'rows', None):
            return
        if not table.rows:
            return
        row = table.rows[0]
        cid = row['id']
        _selected_row_index = 0
        _selected_row_id = cid

        input_refs['id'].set_value(str(cid))
        for k in ['name', 'contact', 'email', 'phone', 'address', 'city', 'balance_ll', 'balance_usd', 'is_active']:
            if k in row:
                input_refs[k].set_value(row[k])

        table.classes(remove='dimmed')
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_edit_mode()

        _apply_selected_row_color()

    def clear_inputs():
        nonlocal _selected_row_index, _selected_row_id
        for k, ref in input_refs.items():
            if k == 'is_active':
                ref.set_value(True)
            elif k in ['balance_ll', 'balance_usd']:
                ref.set_value(0)
            else:
                ref.set_value('')
        if table:
            table.classes(add='dimmed')
            table.run_method('deselectAll')
        _selected_row_index = None
        _selected_row_id = None
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_new_mode()

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

          // +1 offset: NiceGUI's tbody tr set may include an extra structural row
          // depending on table mode/headers; category.py uses an offset to align.
          const safeIdx = Math.max(0, Math.min({idx}, rows.length - 1));

          // Clear previous highlights
          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});

          // Apply target highlight by index (matches category.py approach)
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
        input_refs['name'].set_value(row.get('name') or '')
        input_refs['contact'].set_value(row.get('contact') or '')
        input_refs['email'].set_value(row.get('email') or '')
        input_refs['phone'].set_value(row.get('phone') or '')
        input_refs['address'].set_value(row.get('address') or '')
        input_refs['city'].set_value(row.get('city') or '')
        input_refs['balance_ll'].set_value(row.get('balance_ll') or 0)
        input_refs['balance_usd'].set_value(row.get('balance_usd') or 0)
        input_refs['is_active'].set_value(bool(row.get('is_active')))

        table.classes(remove='dimmed')
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_edit_mode()
        _apply_selected_row_color()

    def save_supplier():
        try:
            s_data = {k: ref.value for k, ref in input_refs.items()}
            if not s_data['name']:
                return ui.notify('Name required', color='negative')

            if s_data['id']:
                dup_chk = []
                connection.contogetrows(
                    "SELECT COUNT(*) FROM suppliers WHERE name=? AND id!=?",
                    dup_chk,
                    params=[s_data['name'], s_data['id']]
                )
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A supplier with this name already exists', color='negative')

                sql = """UPDATE suppliers SET name=?, contact_person=?, email=?, phone=?, 
                         address=?, city=?, balance=?, balance_usd=?, is_active=? WHERE id=?"""
                params = (
                    s_data['name'], s_data['contact'], s_data['email'], s_data['phone'],
                    s_data['address'], s_data['city'],
                    float(s_data['balance_ll'] or 0),
                    float(s_data['balance_usd'] or 0),
                    bool(s_data['is_active']), s_data['id']
                )
            else:
                dup_chk = []
                connection.contogetrows(
                    "SELECT COUNT(*) FROM suppliers WHERE name=?",
                    dup_chk,
                    params=[s_data['name']]
                )
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A supplier with this name already exists', color='negative')

                import accounting_helpers

                def get_next_4011_aux_number():
                    max_seq_rows = []
                    connection.contogetrows(
                        """
                        SELECT MAX(
                            TRY_CAST(
                                SUBSTRING(number, CHARINDEX('.', number) + 1, 50) AS INT
                            )
                        )
                        FROM auxiliary
                        WHERE auxiliary_id = '4011' AND number LIKE '4011.%'
                        """,
                        max_seq_rows
                    )
                    max_seq = max_seq_rows[0][0] if max_seq_rows and max_seq_rows[0][0] is not None else 0
                    candidate_seq = int(max_seq) + 1

                    while True:
                        candidate_aux = f"4011.{candidate_seq}"
                        exists = []
                        connection.contogetrows(
                            "SELECT COUNT(*) FROM auxiliary WHERE number = ?",
                            exists,
                            params=[candidate_aux]
                        )
                        if exists and exists[0][0] == 0:
                            return candidate_aux
                        candidate_seq += 1

                aux_number = get_next_4011_aux_number()
                accounting_helpers.register_auxiliary(aux_number, s_data['name'])

                sql = """INSERT INTO suppliers (name, contact_person, email, phone, address, city, 
                         balance, balance_usd, created_at, is_active, auxiliary_number) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?)"""
                params = (
                    s_data['name'], s_data['contact'], s_data['email'], s_data['phone'],
                    s_data['address'], s_data['city'],
                    float(s_data['balance_ll'] or 0),
                    float(s_data['balance_usd'] or 0),
                    bool(s_data['is_active']), aux_number
                )

            connection.insertingtodatabase(sql, params)

            # Fetch the new supplier ID to use for the VAT auxiliary
            new_id_data = []
            connection.contogetrows("SELECT MAX(id) FROM suppliers", new_id_data)
            new_id = new_id_data[0][0] if new_id_data and new_id_data[0][0] else None

            if new_id and s_data['name'] and not s_data.get('id'):
                import accounting_helpers
                curr_aux_number = s_data.get('auxiliary_number') or new_id
                aux_fetch = []
                connection.contogetrows(
                    "SELECT auxiliary_number FROM suppliers WHERE id = ?",
                    aux_fetch,
                    params=[new_id]
                )
                if aux_fetch and aux_fetch[0][0]:
                    curr_aux_number = aux_fetch[0][0]
                accounting_helpers.ensure_vat_auxiliary('Supplier', new_id, s_data['name'], curr_aux_number)

            ui.notify('Supplier saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    def delete_supplier():
        sid = input_refs['id'].value
        if not sid:
            return ui.notify('Select a supplier to delete', color='warning')
        tx_chk = []
        connection.contogetrows("SELECT COUNT(*) FROM purchases WHERE supplier_id=?", tx_chk, params=[sid])
        if tx_chk and tx_chk[0][0] > 0:
            return ui.notify(
                'Cannot delete supplier with existing transactions. Delete them or set to inactive.',
                color='negative'
            )
        payment_chk = []
        connection.contogetrows("SELECT COUNT(*) FROM supplier_payment WHERE supplier_id=?", payment_chk, params=[sid])
        if payment_chk and payment_chk[0][0] > 0:
            return ui.notify('Cannot delete supplier with existing payments.', color='negative')
        try:
            connection.deleterow("DELETE FROM suppliers WHERE id=?", [sid])
            ui.notify('Supplier deleted successfully', color='positive')
            clear_inputs()
            refresh_table()
        except Exception as e:
            ui.notify(f'Delete error: {e}', color='negative')

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

    def filter_table(query: str = None, status_filter: str = None):
        nonlocal _all_rows, _selected_row_index, _selected_row_id, _filter_text, _filter_status
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
            if q and q not in str(r.get('name') or '').lower() and q not in str(r.get('contact') or '').lower() and q not in str(r.get('phone') or '').lower():
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

    with ModernPageLayout("Supplier Management", standalone=standalone):
        with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
            with ui.column().classes('flex-1 gap-4'):
                with ui.splitter(horizontal=True, value=40).classes('w-full h-[850px]') as splitter:
                    with splitter.before:
                        with ModernCard(glass=True).classes('w-full p-4'):
                            with ui.row().classes('w-full justify-between items-center mb-4 ml-2'):
                                ui.label('Supplier List').classes('text-lg font-bold')
                                with ui.row().classes('items-center bg-white/10 rounded-full px-3 py-1 shadow-sm border border-gray-300 dark:border-gray-600'):
                                    ui.icon('search', color='gray').classes('text-lg')
                                    search_input = ui.input(
                                        placeholder='Search suppliers...'
                                    ).props('borderless dense').classes('ml-2 w-64 text-sm outline-none')
                                    def make_status_filter():
                                        s = ui.select(['All', 'Active', 'Inactive'], label='Status', value='All').classes('w-32').props('outlined dense dark stack-label clearable').style(f'color: {MDS.ACCENT_DARK}')
                                        def on_change(e):
                                            nonlocal _filter_status
                                            val = e.sender.value if hasattr(e, 'sender') else (e.args if isinstance(e.args, str) else '')
                                            _filter_status = 'active' if val == 'Active' else ('inactive' if val == 'Inactive' else '')
                                            filter_table(status_filter=_filter_status)
                                        s.on('update:model-value', on_change)
                                    make_status_filter()

                            search_input.on('update:model-value', lambda e: filter_table(query=e.sender.value))

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
                                {'name': 'name', 'label': 'Company', 'field': 'name', 'align': 'left', 'sortable': True},
                                {'name': 'contact', 'label': 'Contact', 'field': 'contact', 'align': 'left', 'sortable': True},
                                {'name': 'phone', 'label': 'Phone', 'field': 'phone', 'align': 'left', 'sortable': True},
                                {'name': 'balance_ll', 'label': 'Balance LL', 'field': 'balance_ll', 'align': 'left', 'sortable': True},
                                {'name': 'balance_usd', 'label': 'Balance USD', 'field': 'balance_usd', 'align': 'left', 'sortable': True},
                                {'name': 'pending_invoices', 'label': 'Pending Invoices', 'field': 'pending_invoices', 'align': 'left', 'sortable': True},
                                {'name': 'is_active', 'label': 'Active', 'field': 'is_active', 'align': 'left', 'sortable': True},
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
                              if (!root.__bb_sup_arrow_nav) {
                                root.__bb_sup_arrow_nav = true;
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
                            with ModernCard(glass=True).classes('w-[300px] p-6'):
                                ui.label('Supplier Profile').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                input_refs['id'] = ui.input('ID').props('readonly outlined dense dark').classes('hidden')
                                input_refs['name'] = ModernInput('Company Name', icon='business').style('color: #c05884')
                                input_refs['contact'] = ModernInput('Contact Person', icon='person').style('color: #c05884')
                                input_refs['email'] = ModernInput('Email', icon='email').style('color: #c05884')
                                input_refs['phone'] = ModernInput('Phone', icon='phone').style('color: #c05884')

                            with ModernCard(glass=True).classes('flex-1 p-6'):
                                ui.label('Address & Status').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                input_refs['address'] = ui.input('Address').style('color: #c05884').props('outlined dense dark').classes('w-full')
                                input_refs['city'] = ui.input('City').style('color: #c05884').props('outlined dense dark').classes('w-full mt-2')
                                input_refs['balance_ll'] = ui.number('Balance LL').style('color: #c05884').props('outlined dense dark').classes('w-full mt-2')
                                input_refs['balance_usd'] = ui.number('Balance USD').style('color: #c05884').props('outlined dense dark').classes('w-full mt-2')
                                input_refs['is_active'] = ui.checkbox('Active', value=True).classes('mt-2')

            with ui.column().classes('w-80px items-center shrink-0') as footer_container:
                def _show_statement():
                    sid = input_refs['id'].value
                    sname = input_refs['name'].value
                    if not sid:
                        ui.notify('Please select a supplier first', color='warning')
                        return
                    today = datetime.now()
                    default_from = f'{today.year}-01-01'
                    default_to = today.strftime('%Y-%m-%d')
                    from supplier_reports import report_single_supplier_statement
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
                            report_single_supplier_statement(
                                from_date.value, to_date.value, int(sid), sname)
                        ui.button('Generate Statement', on_click=generate).classes(
                            'mt-6 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-8 py-3 rounded-xl font-bold w-full')
                    dlg.open()

                from modern_ui_components import ModernActionBar
                footer_container.action_bar = ModernActionBar(
                    on_new=clear_inputs,
                    on_save=save_supplier,
                    on_undo=lambda: footer_container.action_bar.reset_state(),
                    on_delete=delete_supplier,
                    on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                    on_print=_show_statement,
                    on_print_special=lambda: __import__('supplier_reports').open_print_special_dialog(
                        supplier_id=input_refs['id'].value,
                        supplier_name=input_refs['name'].value
                    ),
                    on_view_transaction=view_supplier_transactions,
                    on_refresh=refresh_table,
                    target_table=table,
                    button_class='h-16',
                    classes=' '
                )
                footer_container.action_bar.style('width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    ui.timer(0.1, refresh_table, once=True)


@ui.page('/suppliers')
def supplier_page_route():
    supplier_page()

