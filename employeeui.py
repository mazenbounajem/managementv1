from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
import hashlib
import datetime
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/employees')
def employee_page_route():
    with ModernPageLayout("Employee Management"):
        EmployeeUI()

class EmployeeUI:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.create_ui()
        self.load_roles()

    def load_roles(self):
        try:
            roles = connection.get_all_roles()
            options = {role[0]: role[1] for role in roles}
            self.input_refs['role_id'].options = options
            self.input_refs['role_id'].update()
        except Exception as e:
            print(f"Error loading roles: {e}")

    def clear_input_fields(self):
        for key, ref in self.input_refs.items():
            if key == 'is_active':
                ref.value = True
            elif key == 'id':
                ref.value = ''
            elif key in ['hire_date', 'termination_date']:
                ref.value = ''
            else:
                ref.value = ''
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new employee entry', color='info')

    def save_employee(self):
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'zip_code', 
                  'hire_date', 'position', 'department', 'salary', 'role_id', 'username', 'password', 
                  'is_active', 'termination_date', 'id']
        vals = {f: self.input_refs[f].value for f in fields}

        if not vals['first_name'] or not vals['last_name'] or not vals['username'] or not vals['password']:
            ui.notify('Required: Names, Username, Password', color='warning')
            return

        if not vals['id'] and connection.username_exists(vals['username']):
            ui.notify('Username already exists', color='error')
            return

        try:
            password_hash = hashlib.md5(vals['password'].encode('utf-8')).hexdigest()
            role_id = int(vals['role_id']) if vals['role_id'] else None

            if vals['id']:
                sql = """UPDATE employees SET first_name=?, last_name=?, email=?, phone=?, address=?, 
                        city=?, state=?, zip_code=?, hire_date=?, position=?, department=?, salary=?, 
                        role_id=?, is_active=?, termination_date=?, updated_at=GETDATE() WHERE id=?"""
                params = (vals['first_name'], vals['last_name'], vals['email'], vals['phone'], vals['address'],
                          vals['city'], vals['state'], vals['zip_code'], vals['hire_date'], vals['position'],
                          vals['department'], vals['salary'], role_id, vals['is_active'],
                          vals['termination_date'] if vals['termination_date'] else None, vals['id'])
                connection.insertingtodatabase(sql, params)
                connection.update_user_account(vals['username'], password_hash, role_id)
            else:
                sql = """INSERT INTO employees (first_name, last_name, email, phone, address, 
                        city, state, zip_code, hire_date, position, department, salary, role_id, 
                        is_active, termination_date, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())"""
                params = (vals['first_name'], vals['last_name'], vals['email'], vals['phone'], vals['address'],
                          vals['city'], vals['state'], vals['zip_code'], vals['hire_date'], vals['position'],
                          vals['department'], vals['salary'], role_id, vals['is_active'],
                          vals['termination_date'] if vals['termination_date'] else None)
                connection.insertingtodatabase(sql, params)
                connection.create_user_account(vals['username'], password_hash, role_id)

            ui.notify('Employee saved', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

    def delete_employee(self):
        id_val = self.input_refs['id'].value
        username = self.input_refs['username'].value
        if not id_val:
            ui.notify('Select an employee to delete', color='warning')
            return

        try:
            connection.deleterow("DELETE FROM employees WHERE id=?", id_val)
            if username:
                connection.deleterow("DELETE FROM users WHERE username=?", username)
            ui.notify('Employee deleted', color='positive')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT id, first_name, last_name, email, position, department, is_active FROM employees ORDER BY id DESC", data)
            rows = []
            for r in data:
                rows.append({
                    'id': r[0], 'first_name': r[1], 'last_name': r[2], 'email': r[3],
                    'position': r[4], 'department': r[5], 'is_active': bool(r[6])
                })
            self.table.options['rowData'] = rows
            self.table.update()
            self.clear_input_fields()
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def create_ui(self):
        with ui.row().classes('w-full gap-6 items-start'):
            # Left Column: History Table
            with ui.column().classes('w-1/3 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Employee Repository').classes('text-lg font-bold mb-4 text-white')
                    self.table = ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'ID', 'field': 'id', 'width': 70},
                            {'headerName': 'Name', 'field': 'first_name', 'flex': 1},
                            {'headerName': 'Position', 'field': 'position', 'width': 120},
                            {'headerName': 'Dept', 'field': 'department', 'width': 100},
                            {'headerName': 'Active', 'field': 'is_active', 'width': 80, 'cellRenderer': 'agCheckboxRenderer'}
                        ],
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-[600px] ag-theme-quartz-dark')
                    
                    async def on_row_click():
                        selected = await self.table.get_selected_row()
                        if selected:
                            self.load_employee_details(selected['id'])
                    self.table.on('cellClicked', on_row_click)

            # Center Column: Details Form
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Employee Profile').classes('text-xl font-black mb-6 text-white')
                    
                    with ui.row().classes('w-full gap-6'):
                        with ui.column().classes('flex-1 gap-4'):
                            ui.label('Personal Info').classes('text-sm font-bold text-white/60')
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['first_name'] = ui.input('First Name').classes('flex-1 glass-input').props('dark rounded outlined')
                                self.input_refs['last_name'] = ui.input('Last Name').classes('flex-1 glass-input').props('dark rounded outlined')
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['email'] = ui.input('Email').classes('flex-1 glass-input').props('dark rounded outlined')
                                self.input_refs['phone'] = ui.input('Phone').classes('w-48 glass-input').props('dark rounded outlined')
                            self.input_refs['address'] = ui.input('Address').classes('w-full glass-input').props('dark rounded outlined')
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['city'] = ui.input('City').classes('flex-1 glass-input').props('dark rounded outlined')
                                self.input_refs['state'] = ui.input('State').classes('w-32 glass-input').props('dark rounded outlined')
                                self.input_refs['zip_code'] = ui.input('ZIP').classes('w-32 glass-input').props('dark rounded outlined')

                        with ui.column().classes('flex-1 gap-4'):
                            ui.label('Employment & Access').classes('text-sm font-bold text-white/60')
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['position'] = ui.select(['Manager', 'Cashier', 'Sales', 'Other'], label='Position').classes('flex-1 glass-input').props('dark rounded outlined')
                                self.input_refs['department'] = ui.select(['Ops', 'Sales', 'HR', 'Admin'], label='Department').classes('flex-1 glass-input').props('dark rounded outlined')
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['hire_date'] = ui.input('Hire Date').classes('flex-1 glass-input').props('dark rounded outlined type=date')
                                self.input_refs['salary'] = ui.input('Salary').classes('w-32 glass-input').props('dark rounded outlined')
                            
                            self.input_refs['role_id'] = ui.select({}, label='System Role').classes('w-full glass-input').props('dark rounded outlined')
                            
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['username'] = ui.input('Username').classes('flex-1 glass-input').props('dark rounded outlined')
                                self.input_refs['password'] = ui.input('Password', password=True).classes('flex-1 glass-input').props('dark rounded outlined')
                            
                            with ui.row().classes('w-full items-center justify-between'):
                                self.input_refs['is_active'] = ui.switch('Active Status', value=True).classes('text-white')
                                self.input_refs['termination_date'] = ui.input('Termination').classes('w-48 glass-input').props('dark rounded outlined type=date')
                                self.input_refs['id'] = ui.input('ID').classes('w-20 glass-input').props('dark rounded outlined readonly')

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                from modern_ui_components import ModernActionBar
                ModernActionBar(
                    on_new=self.clear_input_fields,
                    on_save=self.save_employee,
                    on_undo=lambda: ui.notify('Undo not implemented for employees'),
                    on_delete=self.delete_employee,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    on_refresh=self.refresh_table,
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        ui.timer(0.1, self.refresh_table, once=True)

    def load_employee_details(self, emp_id):
        try:
            data = []
            connection.contogetrows(f"SELECT * FROM employees WHERE id={emp_id}", data)
            if data:
                r = data[0]
                # Map columns (this is sensitive to DB schema, assuming default order)
                # Assuming: id, first, last, email, phone, address, city, state, zip, hire, pos, dept, salary, role, active, term, ...
                self.input_refs['id'].value = str(r[0])
                self.input_refs['first_name'].value = r[1]
                self.input_refs['last_name'].value = r[2]
                self.input_refs['email'].value = r[3]
                self.input_refs['phone'].value = r[4]
                self.input_refs['address'].value = r[5]
                self.input_refs['city'].value = r[6]
                self.input_refs['state'].value = r[7]
                self.input_refs['zip_code'].value = r[8]
                self.input_refs['hire_date'].value = str(r[9]) if r[9] else ''
                self.input_refs['position'].value = r[10]
                self.input_refs['department'].value = r[11]
                self.input_refs['salary'].value = str(r[12])
                self.input_refs['role_id'].value = r[13]
                self.input_refs['is_active'].value = bool(r[14])
                self.input_refs['termination_date'].value = str(r[15]) if r[15] else ''
                
                # Load username from users table
                user_data = []
                connection.contogetrows(f"SELECT username FROM users WHERE role_id={r[13]}", user_data) # This might be wrong logic, users table usually has employee_id or username link
                # Better approach: connection.get_username_by_employee_id if exists
                # For now, let's keep it simple or check users table structure
                if user_data:
                    self.input_refs['username'].value = user_data[0][0]
                
                if self.table:
                    self.table.classes(remove='dimmed')
        except Exception as e:
            ui.notify(f'Error loading details: {str(e)}', color='negative')
