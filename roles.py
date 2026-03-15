from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/roles')
def roles_page_route():
    with ModernPageLayout("Roles & Permissions"):
        RolesUI()

class RolesUI:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.available_pages = [
            'dashboard', 'employees', 'products', 'purchase', 'reports', 'sales-reports', 'stock-reports', 'sales',
            'suppliers', 'supplierpayment', 'category', 'consignment', 'customers',
            'customerreceipt', 'expenses', 'expensestype', 'accounting', 'roles', 'timespend',
            'stockoperations', 'cash-drawer', 'currencies', 'services', 'appointments'
        ]
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['id'].value = ''
        self.input_refs['name'].value = ''
        self.input_refs['description'].value = ''
        for page in self.available_pages:
            self.input_refs[f'perm_{page}'].value = False
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new role', color='info')

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
            self.clear_input_fields()
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def load_permissions(self, role_id):
        try:
            # Reset
            for p in self.available_pages:
                self.input_refs[f'perm_{p}'].value = False
            
            perms = []
            connection.contogetrows(f"SELECT page_name, can_access FROM role_permissions WHERE role_id={role_id}", perms)
            for p_name, can_acc in perms:
                if f'perm_{p_name}' in self.input_refs:
                    self.input_refs[f'perm_{p_name}'].value = bool(can_acc)
        except Exception as e:
            print(f"Error loading perms: {e}")

    def create_ui(self):
        # Action Bar
        with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
            with ui.row().classes('gap-3'):
                ModernButton('New Role', icon='add', on_click=self.clear_input_fields, variant='primary')
                ModernButton('Save Role', icon='save', on_click=self.save_role, variant='success')
                ModernButton('Delete Role', icon='delete', on_click=self.delete_role, variant='error')
            
            ModernButton('Refresh', icon='refresh', on_click=self.refresh_table, variant='outline').classes('text-white border-white/20')

        with ui.column().classes('w-full gap-6'):
            # Top: List
            with ModernCard(glass=True).classes('w-full p-6'):
                self.table = ui.aggrid({
                    'columnDefs': [
                        {'headerName': 'ID', 'field': 'id', 'width': 80},
                        {'headerName': 'Role Name', 'field': 'name', 'width': 200},
                        {'headerName': 'Description', 'field': 'description', 'width': 300, 'flex': 1}
                    ],
                    'rowData': [],
                    'defaultColDef': MDS.get_ag_grid_default_def(),
                    'rowSelection': 'single',
                }).classes('w-full h-64 ag-theme-quartz-dark')
                
                async def on_row_click():
                    selected = await self.table.get_selected_row()
                    if selected:
                        self.input_refs['id'].value = str(selected['id'])
                        self.input_refs['name'].value = selected['name']
                        self.input_refs['description'].value = selected['description']
                        self.load_permissions(selected['id'])
                        if self.table:
                            self.table.classes(remove='dimmed')
                self.table.on('cellClicked', on_row_click)

            # Bottom: Details & Permissions
            with ui.row().classes('w-full gap-6'):
                with ModernCard(glass=True).classes('flex-1 p-6'):
                    ui.label('Role Info').classes('text-xl font-black mb-6 text-white')
                    self.input_refs['name'] = ui.input('Role Name').classes('w-full glass-input mb-4').props('dark rounded outlined')
                    self.input_refs['description'] = ui.textarea('Description').classes('w-full glass-input h-32').props('dark rounded outlined')
                    self.input_refs['id'] = ui.input('Internal ID').classes('w-24 glass-input').props('dark rounded outlined readonly')

                with ModernCard(glass=True).classes('w-[500px] p-6'):
                    ui.label('Permissions').classes('text-xl font-black mb-6 text-white')
                    with ui.grid(columns=2).classes('w-full gap-x-4 gap-y-2 max-h-[400px] overflow-y-auto pr-2'):
                        for page in self.available_pages:
                            display = page.replace('-', ' ').title()
                            self.input_refs[f'perm_{page}'] = ui.checkbox(display).classes('text-white text-sm')

        ui.timer(0.1, self.refresh_table, once=True)
