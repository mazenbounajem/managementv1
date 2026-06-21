from nicegui import ui
from connection import connection
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput


def roles_content(standalone=False):
    """Content method for roles that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Roles & Permissions", standalone=standalone):
            RolesUI(standalone=False)
    else:
        RolesUI(standalone=False)


@ui.page('/roles')
def roles_page_route():
    roles_content(standalone=True)


class RolesUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self._all_rows = []
        self._selected_row_index = None
        self.search_input = None

        # Flat list is kept for DB read/write compatibility
        self.available_pages = [
            'dashboard', 'employees', 'products', 'purchase', 'reports', 'sales-reports', 'stock-reports', 'sales',
            'suppliers', 'supplierpayment', 'category', 'consignment', 'customers',
            'customerreceipt', 'expenses', 'expensestype', 'accounting', 'roles', 'timespend',
            'stockoperations', 'cash-drawer', 'currencies', 'services', 'appointments',
            'ledger', 'auxiliary', 'journal_voucher', 'voucher_subtype', 'company',
            'sales-returns', 'purchase-returns', 'hide-history',
            'business-track', 'accounting-transactions',
            'profit-analytics',
            'year-transition',
            'database-backup',
            'statistical-reports',
            'dashboard-kpis'
        ]

        # Group pages in a "permission tree" similar to the navigation grouping.
        # Keys/values are page routes stored in role_permissions.page_name.
        self.permission_tree = {
            'Dashboard': ['dashboard', 'dashboard-kpis'],
            'Employees & HR': ['employees', 'timespend', 'appointments'],
            'Customers': ['customers', 'customerreceipt'],
            'Suppliers': ['suppliers', 'supplierpayment'],
            'Sales': [
                'sales', 'sales-reports', 'sales-returns'
            ],
            'Purchases': [
                'purchase', 'purchase-returns'
            ],
            'Inventory & Stock': [
                'products', 'category', 'consignment', 'stockoperations', 'stock-reports'
            ],
            'Expenses': [
                'expenses', 'expensestype'
            ],
            'Services & Other Ops': [
                'services', 'cash-drawer', 'currencies', 'business-track', 'profit-analytics', 'hide-history'
            ],
            'Accounting': [
                'accounting', 'ledger', 'auxiliary', 'journal_voucher', 'voucher_subtype', 'company',
                'accounting-transactions'
            ],
            'Reports': [
                # General reports routes (keep them grouped even if they map to different underlying pages)
                'reports', 'statistical-reports'
            ],
            'Year Transition': [
                'year-transition'
            ],
            'Database Backup': [
                'database-backup'
            ],
            'Administration': [
                'roles'
            ],
        }

        # Any pages not included above will be appended to an "Other" group.
        grouped = set()
        for pages in self.permission_tree.values():
            grouped.update(pages)

        other_pages = [p for p in self.available_pages if p not in grouped]
        if other_pages:
            self.permission_tree['Other'] = other_pages

        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['id'].value = ''
        self.input_refs['name'].value = ''
        self.input_refs['description'].value = ''
        for page in self.available_pages:
            if f'perm_{page}' in self.input_refs:
                self.input_refs[f'perm_{page}'].value = False
        if self.table:
            self.table.classes(add='dimmed')
            self.table.selected = None
        self._selected_row_index = None
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
        ui.notify('Ready for new role', color='info')

    def _load_last_row(self):
        """Load the first row (last id DESC) into form and undim table"""
        if not getattr(self.table, 'rows', None):
            return
        if not self.table.rows:
            return
        row = self.table.rows[0]
        role_id = row['id']
        self._selected_row_index = 0
        self.input_refs['id'].value = str(role_id)
        self.input_refs['name'].value = row.get('name') or ''
        self.input_refs['description'].value = row.get('description') or ''
        self.load_permissions(role_id)
        if self.table:
            self.table.classes(remove='dimmed')
            self._apply_selected_row_color()
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_edit_mode()

    def save_role(self):
        name = self.input_refs['name'].value
        description = self.input_refs['description'].value
        id_val = self.input_refs['id'].value

        if not name:
            ui.notify('Role Name is required', color='warning')
            return

        try:
            if id_val:
                sql = "UPDATE roles SET name=?, description=?, updated_at=GETDATE() WHERE id=?"
                connection.insertingtodatabase(sql, (name, description, id_val))
                role_id = id_val
            else:
                sql = "INSERT INTO roles (name, description) VALUES (?, ?)"
                connection.insertingtodatabase(sql, (name, description))
                role_id = connection.getid("SELECT id FROM roles WHERE name=?", (name,))

            # Save Permissions
            for page in self.available_pages:
                can_access = 1 if self.input_refs[f'perm_{page}'].value else 0
                perm_exists = connection.getrow(
                    "SELECT id FROM role_permissions WHERE role_id=? AND page_name=?",
                    (role_id, page)
                )

                if perm_exists:
                    connection.insertingtodatabase(
                        "UPDATE role_permissions SET can_access=?, updated_at=GETDATE() WHERE role_id=? AND page_name=?",
                        (can_access, role_id, page)
                    )
                else:
                    connection.insertingtodatabase(
                        "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                        (role_id, page, can_access)
                    )

            ui.notify('Role and Permissions saved', color='positive')
            if hasattr(self, 'action_bar'):
                self.action_bar.reset_state()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

    def undo_changes(self):
        self.clear_input_fields()
        if self.table:
            self.table.classes(remove='dimmed')
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()
        ui.notify('Changes reverted', color='info')

    def delete_role(self):
        id_val = self.input_refs['id'].value
        if not id_val:
            ui.notify('Select a role to delete', color='warning')
            return

        # Check if role is assigned to any users
        users_count = connection.getrow("SELECT COUNT(*) FROM users WHERE role_id=?", (id_val,))
        if users_count and users_count[0] > 0:
            ui.notify('Cannot delete: Role is assigned to users', color='warning')
            return

        try:
            connection.deleterow("DELETE FROM role_permissions WHERE role_id=?", id_val)
            connection.deleterow("DELETE FROM roles WHERE id=?", id_val)
            ui.notify('Role deleted', color='positive')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT id, name, description FROM roles ORDER BY id DESC", data)
            rows = []
            for r in data:
                rows.append({'id': r[0], 'name': r[1], 'description': r[2]})
            self._all_rows = rows
            self._selected_row_index = None
            self.table.rows = rows
            self.table.update()
            self.row_data = rows
            self._load_last_row()
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def load_permissions(self, role_id):
        try:
            # Reset
            for p in self.available_pages:
                if f'perm_{p}' in self.input_refs:
                    self.input_refs[f'perm_{p}'].value = False

            perms = []
            connection.contogetrows(
                f"SELECT page_name, can_access FROM role_permissions WHERE role_id={role_id}",
                perms
            )
            for p_name, can_acc in perms:
                if f'perm_{p_name}' in self.input_refs:
                    self.input_refs[f'perm_{p_name}'].value = bool(can_acc)
        except Exception as e:
            print(f"Error loading perms: {e}")

    def _filter_table(self, query: str):
        if not getattr(self, 'table', None):
            return
        q = (query or "").strip().lower()
        if not q:
            self.table.rows = getattr(self, '_all_rows', [])
            self.table.update()
            self._load_last_row()
            return
        all_rows = getattr(self, '_all_rows', []) or []
        filtered = []
        for row in all_rows:
            name = str(row.get('name') or '').lower()
            if q in name:
                filtered.append(row)
        self.table.rows = filtered
        self.table.update()
        if self.table:
            self.table.classes(remove='dimmed')

    def _focus_first_row(self):
        if self.table and self.table.rows:
            role_id = self.table.rows[0].get('id')
            if role_id is not None:
                self._apply_row_from_id(role_id)

    def _apply_row_from_id(self, role_id):
        if not getattr(self, 'table', None):
            return
        rows = getattr(self.table, 'rows', None) or []
        target_index = next((i for i, r in enumerate(rows) if r.get('id') == role_id), None)
        if target_index is None:
            return
        row = rows[target_index]
        self._selected_row_index = target_index
        self.input_refs['id'].value = str(role_id)
        self.input_refs['name'].value = row.get('name') or ''
        self.input_refs['description'].value = row.get('description') or ''
        self.load_permissions(role_id)
        if self.table:
            self.table.classes(remove='dimmed')
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_edit_mode()
        self._apply_selected_row_color()

    def _apply_selected_row_color(self):
        if self._selected_row_index is None:
            return
        ui.run_javascript(f"""
        try {{
          const root = document.querySelector('.q-table');
          if (!root) return;
          const rows = root.querySelectorAll('tbody tr');
          if (!rows || rows.length === 0) return;
          const idx = Math.max(0, Math.min({self._selected_row_index} + 1, rows.length - 1));
          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});
          const selected = rows[idx];
          if (selected) {{
            selected.style.backgroundColor = '#facc15';
            selected.style.color = 'black';
            selected.classList.add('selected-highlight');
          }}
        }} catch (e) {{ console.error('Highlight error:', e); }}
        """)

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Roles & Permissions", standalone=True)
            layout_container.__enter__()

        try:
            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Role List
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Roles Directory')\
                            .classes('text-lg font-black mb-4 text-white uppercase tracking-widest opacity-70')

                        # Search UI
                        with ui.row().classes('w-full gap-3 mb-3 items-center'):
                            self.search_input = (
                                ui.input(placeholder='Search roles...')
                                .props('outlined dense')
                                .classes('flex-1 text-white bg-black')
                                .on('update:model-value', lambda e: self._filter_table(e.args))
                                .on('keydown.down', lambda: self._focus_first_row())
                            )

                        columns = [
                            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                            {'name': 'name', 'label': 'Role Name', 'field': 'name', 'align': 'left'},
                        ]

                        self.table = ui.table(
                            columns=columns,
                            rows=[],
                            row_key='id',
                            selection='single'
                        ).classes('w-full h-80 overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

                        def on_row_click(e):
                            try:
                                row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                if not isinstance(row, dict):
                                    if isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                        row = e.args[0]
                                if not row:
                                    return
                                role_id = row.get('id')
                                if role_id is None:
                                    return
                                self.input_refs['id'].value = str(role_id)
                                self.input_refs['name'].value = row.get('name') or ''
                                self.input_refs['description'].value = row.get('description') or ''
                                self.load_permissions(role_id)
                                if self.table:
                                    self.table.classes(remove='dimmed')
                                if hasattr(self, 'action_bar'):
                                    self.action_bar.enter_edit_mode()
                            except Exception as ex:
                                ui.notify(f'Error selecting row: {str(ex)}', color='negative')

                        def on_keydown(e):
                            try:
                                key = getattr(e, 'key', None) or getattr(e, 'args', {}).get('key', None)
                                if key not in ('ArrowDown', 'ArrowUp'):
                                    return
                                rows = getattr(self.table, 'rows', None) or []
                                if not rows:
                                    return
                                if self._selected_row_index is None:
                                    self._selected_row_index = 0
                                if key == 'ArrowDown':
                                    self._selected_row_index = min(self._selected_row_index + 1, len(rows) - 1)
                                else:
                                    self._selected_row_index = max(self._selected_row_index - 1, 0)
                                role_id = rows[self._selected_row_index].get('id')
                                if role_id is None:
                                    return
                                self._apply_row_from_id(role_id)
                            except Exception as ex:
                                ui.notify(f'Keyboard navigation error: {ex}', color='warning')

                        def _row_click_wrapper(e):
                            try:
                                row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                if not isinstance(row, dict):
                                    if isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                        row = e.args[0]
                                if isinstance(row, dict) and row.get('id') is not None:
                                    self._selected_row_index = next((i for i, r in enumerate(self.table.rows or []) if r.get('id') == row.get('id')), None)
                                    self._apply_selected_row_color()
                            except:
                                pass
                            on_row_click(e)

                        self.table.on('rowClick', _row_click_wrapper)

                        if self.table:
                            try:
                                self.table.on('keydown', on_keydown)
                            except Exception:
                                pass

                # Center Column: Details & Permissions
                with ui.column().classes('flex-1 gap-4'):
                    with ui.row().classes('w-full gap-6 items-start'):
                        # Info Card
                        with ModernCard(glass=True).classes('flex-1 p-6'):
                            ui.label('Role Definition').classes('text-xl font-black mb-6 text-white')
                            with ui.column().classes('w-full gap-4'):
                                self.input_refs['name'] = ui.input('Role Name')\
                                    .classes('w-full glass-input').props('dark rounded outlined dense')
                                self.input_refs['description'] = ui.textarea('Official Description')\
                                    .classes('w-full glass-input').props('dark rounded outlined h-32')
                                self.input_refs['id'] = ui.input('Reference ID')\
                                    .classes('w-48 glass-input opacity-50').props('dark rounded outlined readonly dense')

                # Permissions Card
                with ModernCard(glass=True).classes('w-[500px] p-6'):
                    ui.label('Page Permissions').classes('text-xl font-black mb-6 text-white')

                    # Tree-like grouped permissions UI
                    with ui.column().classes('w-full max-h-[520px] overflow-y-auto pr-4 scroll-slim gap-4'):
                        for group_name, pages in self.permission_tree.items():
                            with ui.expansion(group_name, icon='folder_open').classes('w-full border border-white/10 rounded-xl px-3 py-2'):
                                with ui.column().classes('w-full gap-2'):
                                    for page in pages:
                                        display = page.replace('-', ' ').title()
                                        with ui.row().classes('items-center justify-between w-full border-b border-white/5 pb-1'):
                                            ui.label(display).classes('text-white text-xs font-bold font-mono opacity-80')
                                            self.input_refs[f'perm_{page}'] = ui.checkbox('').classes('text-white scale-110')

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    self.action_bar = ModernActionBar(
                        on_new=self.clear_input_fields,
                        on_save=self.save_role,
                        on_undo=self.undo_changes,
                        on_delete=self.delete_role,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        on_refresh=self.refresh_table,
                        button_class='h-16',
                        target_table=self.table,
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_table, once=True)
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)
