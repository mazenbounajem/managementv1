from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/expensestype')
def expensestype_page():
    with ModernPageLayout("Expense Categories"):
        ExpenseTypeUI()

class ExpenseTypeUI:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['expense_type_name'].value = ''
        self.input_refs['description'].value = ''
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new category', color='info')

    def save_expense_type(self):
        expense_type_name = self.input_refs['expense_type_name'].value
        description = self.input_refs['description'].value
        id_value = self.input_refs['id'].value
        
        if not expense_type_name:
            ui.notify('Expense category name is required', color='warning')
            return
        
        try:
            if id_value:
                sql = "UPDATE expense_types SET expense_type_name=?, description=? WHERE id=?"
                values = (expense_type_name, description, id_value)
            else:
                sql = "INSERT INTO expense_types (expense_type_name, description, created_at) VALUES (?, ?, GETDATE())"
                values = (expense_type_name, description)
            
            connection.insertingtodatabase(sql, values)
            ui.notify('Expense category saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving category: {str(e)}', color='negative')

    def undo_changes(self):
        for field in ['expense_type_name', 'description', 'id']:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')

    def delete_expense_type(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Please select a category to delete', color='warning')
            return
        
        try:
            sql = "DELETE FROM expense_types WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Category deleted successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting category: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT id, expense_type_name, description, created_at FROM expense_types ORDER BY id DESC", data)
            
            new_row_data = []
            for row in data:
                new_row_data.append({
                    'id': row[0],
                    'expense_type_name': row[1],
                    'description': row[2],
                    'created_at': str(row[3])
                })
            
            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()
                self.table.classes(remove='dimmed')
            
            self.row_data = new_row_data
            self.clear_input_fields()
        except Exception as e:
            ui.notify(f'Error refreshing data: {str(e)}', color='negative')

    def create_ui(self):
        # Action Bar
        with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
            with ui.row().classes('gap-3'):
                ModernButton('New Category', icon='add', on_click=self.clear_input_fields, variant='primary')
                ModernButton('Save', icon='save', on_click=self.save_expense_type, variant='success')
                ModernButton('Undo', icon='undo', on_click=self.undo_changes, variant='secondary')
                ModernButton('Delete', icon='delete', on_click=self.delete_expense_type, variant='error')
            
            ModernButton('Refresh', icon='refresh', on_click=self.refresh_table, variant='outline').classes('text-white border-white/20')

        with ui.column().classes('w-full gap-6'):
            # Top: List
            with ModernCard(glass=True).classes('w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Expense Categories').classes('text-xl font-black text-white')
                    self.search_input = ui.input(placeholder='Search categories...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                    self.search_input.on('input', lambda e: self.filter_rows(e.value))

                column_defs = [
                    {'headerName': 'ID', 'field': 'id', 'width': 80},
                    {'headerName': 'Category Name', 'field': 'expense_type_name', 'width': 250},
                    {'headerName': 'Description', 'field': 'description', 'width': 350},
                    {'headerName': 'Created At', 'field': 'created_at', 'width': 180}
                ]

                self.table = ui.aggrid({
                    'columnDefs': column_defs,
                    'rowData': [],
                    'defaultColDef': MDS.get_ag_grid_default_def(),
                    'rowSelection': 'single',
                }).classes('w-full h-80 ag-theme-quartz-dark')
                
                async def on_row_click():
                    try:
                        selected_row = await self.table.get_selected_row()
                        if selected_row:
                            self.input_refs['id'].value = str(selected_row['id'])
                            self.input_refs['expense_type_name'].value = selected_row['expense_type_name']
                            self.input_refs['description'].value = selected_row['description']
                            
                            self.initial_values = {
                                'expense_type_name': selected_row['expense_type_name'],
                                'description': selected_row['description'],
                                'id': str(selected_row['id'])
                            }
                            ui.notify(f'Selected: {selected_row["expense_type_name"]}', color='info')
                    except Exception as e:
                        ui.notify(f'Error selecting category: {str(e)}', color='negative')
                
                self.table.on('cellClicked', on_row_click)

            # Bottom: Details Form
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Category Details').classes('text-lg font-black mb-6 text-white')
                with ui.row().classes('w-full gap-6'):
                    self.input_refs['expense_type_name'] = ui.input('Category Name').classes('flex-1 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['id'] = ui.input('ID (Auto)').classes('w-32 glass-input text-white').props('dark rounded outlined readonly')
                
                self.input_refs['description'] = ui.textarea('Description').classes('w-full mt-4 glass-input text-white').props('dark rounded outlined')

        ui.timer(0.1, self.refresh_table, once=True)

    def filter_rows(self, search_text):
        if not search_text:
            self.table.options['rowData'] = self.row_data
        else:
            search_text = search_text.lower()
            filtered = [row for row in self.row_data if any(search_text in str(v).lower() for v in row.values())]
            self.table.options['rowData'] = filtered
        self.table.update()

@ui.page('/expensestype')
def expensestype_page_route():
    expensestype_page()
