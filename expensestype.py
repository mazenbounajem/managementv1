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
        with ui.row().classes('w-full gap-6 items-start'):
            # Left Column: Category Table
            with ui.column().classes('w-1/2 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Expense Categories').classes('text-xl font-black text-white')
                        self.search_input = ui.input(placeholder='Search categories...').classes('w-48 glass-input text-white text-sm').props('dark rounded outlined dense')
                        self.search_input.on('input', lambda e: self.filter_rows(e.value))

                    column_defs = [
                        {'headerName': 'ID', 'field': 'id', 'width': 70},
                        {'headerName': 'Category Name', 'field': 'expense_type_name', 'flex': 1},
                        {'headerName': 'Description', 'field': 'description', 'flex': 1.5},
                    ]

                    self.table = ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-[500px] ag-theme-quartz-dark')
                    
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

            # Center Column: Details Form
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Category Details').classes('text-lg font-black mb-6 text-white uppercase tracking-widest')
                    
                    with ui.column().classes('w-full gap-4'):
                        self.input_refs['expense_type_name'] = ui.input('Category Name').classes('w-full glass-input text-white').props('dark rounded outlined')
                        self.input_refs['id'] = ui.input('ID (Auto-generated)').classes('w-full glass-input text-white opacity-50').props('dark rounded outlined readonly')
                        self.input_refs['description'] = ui.textarea('Short Description / Purpose').classes('w-full glass-input text-white').props('dark rounded outlined')

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                from modern_ui_components import ModernActionBar
                ModernActionBar(
                    on_new=self.clear_input_fields,
                    on_save=self.save_expense_type,
                    on_undo=self.undo_changes,
                    on_delete=self.delete_expense_type,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    on_refresh=self.refresh_table,
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

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
