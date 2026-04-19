from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

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
        self.available_pages = [
            'dashboard', 'employees', 'products', 'purchase', 'reports', 'sales-reports', 'stock-reports', 'sales',
            'suppliers', 'supplierpayment', 'category', 'consignment', 'customers',
            'customerreceipt', 'expenses', 'expensestype', 'accounting', 'roles', 'timespend',
            'stockoperations', 'cash-drawer', 'currencies', 'services', 'appointments',
            'ledger', 'auxiliary', 'journal_voucher', 'voucher_subtype', 'company'
        ]
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
            self.table.run_method('deselectAll')
        ui.notify('Ready for new role', color='info')

    def _load_last_row(self):
        """Load the first row (last id DESC) into form and undim table"""
        if not self.table:
            return
        self.table.classes(remove='dimmed')
        try:
            data = []
            connection.contogetrows("SELECT TOP 1 id, name, description FROM roles ORDER BY id DESC", data)
            if data:
                r = data[0]
                self.input_refs['id'].value = str(r[0])
                self.input_refs['name'].value = r[1] or ''
                self.input_refs['description'].value = r[2] or ''
                self.load_permissions(r[0])
        except Exception as e:
            print(f"Error loading last role: {e}")

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
                perm_exists = connection.getrow("SELECT id FROM role_permissions WHERE role_id=? AND page_name=?", (role_id, page))
                
                if perm_exists:
                    connection.insertingtodatabase("UPDATE role_permissions SET can_access=?, updated_at=GETDATE() WHERE role_id=? AND page_name=?", (can_access, role_id, page))
                else:
                    connection.insertingtodatabase("INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)", (role_id, page, can_access))

            ui.notify('Role and Permissions saved', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

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
            self.table.options['rowData'] = rows
            self.table.update()
            # Load last entry into form and undim
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
            connection.contogetrows(f"SELECT page_name, can_access FROM role_permissions WHERE role_id={role_id}", perms)
            for p_name, can_acc in perms:
                if f'perm_{p_name}' in self.input_refs:
                    self.input_refs[f'perm_{p_name}'].value = bool(can_acc)
        except Exception as e:
            print(f"Error loading perms: {e}")

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
                        ui.label('Roles Directory').classes('text-lg font-black mb-4 text-white uppercase tracking-widest opacity-70')
                        self.table = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'ID', 'field': 'id', 'width': 70},
                                {'headerName': 'Role Name', 'field': 'name', 'flex': 1},
                            ],
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark shadow-inner')
                        
                        def on_row_click(e):
                            selected = e.args.get('data', {})
                            if selected:
                                self.input_refs['id'].value = str(selected['id'])
                                self.input_refs['name'].value = selected['name'] or ''
                                self.input_refs['description'].value = selected.get('description') or ''
                                self.load_permissions(selected['id'])
                                if self.table:
                                    self.table.classes(remove='dimmed')
                        self.table.on('cellClicked', on_row_click)

                # Center Column: Details & Permissions
                with ui.column().classes('flex-1 gap-4'):
                    with ui.row().classes('w-full gap-6 items-start'):
                        # Info Card
                        with ModernCard(glass=True).classes('flex-1 p-6'):
                            ui.label('Role Definition').classes('text-xl font-black mb-6 text-white')
                            with ui.column().classes('w-full gap-4'):
                                self.input_refs['name'] = ui.input('Role Name').classes('w-full glass-input').props('dark rounded outlined dense')
                                self.input_refs['description'] = ui.textarea('Official Description').classes('w-full glass-input').props('dark rounded outlined h-32')
                                self.input_refs['id'] = ui.input('Reference ID').classes('w-48 glass-input opacity-50').props('dark rounded outlined readonly dense')

                        # Permissions Card
                        with ModernCard(glass=True).classes('w-[500px] p-6'):
                            ui.label('Page Permissions').classes('text-xl font-black mb-6 text-white')
                            with ui.grid(columns=2).classes('w-full gap-x-6 gap-y-3 max-h-[500px] overflow-y-auto pr-4 scroll-slim'):
                                for page in self.available_pages:
                                    display = page.replace('-', ' ').title()
                                    with ui.row().classes('items-center justify-between w-full border-b border-white/5 pb-2'):
                                        ui.label(display).classes('text-white text-xs font-bold font-mono opacity-80')
                                        self.input_refs[f'perm_{page}'] = ui.checkbox('').classes('text-white scale-110')

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_input_fields,
                        on_save=self.save_role,
                        on_undo=lambda: ui.notify('Undo not implemented for roles'),
                        on_delete=self.delete_role,
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        on_refresh=self.refresh_table,
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_table, once=True)
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)