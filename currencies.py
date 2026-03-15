from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/currencies')
def currencies_page():
    with ModernPageLayout("Currency Management"):
        CurrencyUI()

class CurrencyUI:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['currency_code'].value = ''
        self.input_refs['currency_name'].value = ''
        self.input_refs['symbol'].value = ''
        self.input_refs['exchange_rate'].value = 1.0
        self.input_refs['is_active'].value = True
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new currency', color='info')

    def save_currency(self):
        currency_code = self.input_refs['currency_code'].value.upper()
        currency_name = self.input_refs['currency_name'].value
        symbol = self.input_refs['symbol'].value
        exchange_rate = float(self.input_refs['exchange_rate'].value) if self.input_refs['exchange_rate'].value else 1.0
        is_active = self.input_refs['is_active'].value
        id_value = self.input_refs['id'].value

        if not currency_code or not currency_name:
            ui.notify('Currency Code and Name are required', color='warning')
            return

        try:
            if id_value:
                sql = "UPDATE currencies SET currency_code=?, currency_name=?, symbol=?, exchange_rate=?, is_active=?, updated_at=GETDATE() WHERE id=?"
                values = (currency_code, currency_name, symbol, exchange_rate, is_active, id_value)
            else:
                sql = "INSERT INTO currencies (currency_code, currency_name, symbol, exchange_rate, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())"
                values = (currency_code, currency_name, symbol, exchange_rate, is_active)

            connection.insertingtodatabase(sql, values)
            ui.notify('Currency saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving currency: {str(e)}', color='negative')

    def undo_changes(self):
        for field in ['currency_code', 'currency_name', 'symbol', 'exchange_rate', 'is_active', 'id']:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')

    def delete_currency(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Please select a currency to delete', color='warning')
            return

        try:
            sql = "DELETE FROM currencies WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Currency deleted successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting currency: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active, created_at FROM currencies ORDER BY id DESC", data)

            new_row_data = []
            for row in data:
                new_row_data.append({
                    'id': row[0],
                    'currency_code': row[1],
                    'currency_name': row[2],
                    'symbol': row[3] or '',
                    'exchange_rate': float(row[4]) if row[4] is not None else 1.0,
                    'is_active': bool(row[5]),
                    'created_at': str(row[6])
                })

            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()
                self.table.classes(remove='dimmed')

            self.row_data = new_row_data
            self.clear_input_fields()
        except Exception as e:
            ui.notify(f'Error refreshing data: {str(e)}', color='negative')

    def load_max_currency(self):
        try:
            data = []
            connection.contogetrows("SELECT TOP 1 id, currency_code, currency_name, symbol, exchange_rate, is_active FROM currencies ORDER BY id DESC", data)
            if data:
                row = data[0]
                self.input_refs['id'].value = str(row[0])
                self.input_refs['currency_code'].value = row[1]
                self.input_refs['currency_name'].value = row[2]
                self.input_refs['symbol'].value = row[3] or ''
                self.input_refs['exchange_rate'].value = float(row[4]) if row[4] is not None else 1.0
                self.input_refs['is_active'].value = bool(row[5])
                
                self.initial_values = {
                    'currency_code': row[1],
                    'currency_name': row[2],
                    'symbol': row[3] or '',
                    'exchange_rate': float(row[4]) if row[4] is not None else 1.0,
                    'is_active': bool(row[5]),
                    'id': str(row[0])
                }
        except Exception as e:
            print(f"Error loading max currency: {e}")

    def create_ui(self):
        # Action Bar
        with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
            with ui.row().classes('gap-3'):
                ModernButton('New Currency', icon='add', on_click=self.clear_input_fields, variant='primary')
                ModernButton('Save', icon='save', on_click=self.save_currency, variant='success')
                ModernButton('Undo', icon='undo', on_click=self.undo_changes, variant='secondary')
                ModernButton('Delete', icon='delete', on_click=self.delete_currency, variant='error')
            
            ModernButton('Refresh', icon='refresh', on_click=self.refresh_table, variant='outline').classes('text-white border-white/20')

        with ui.column().classes('w-full gap-6'):
            # Top: List
            with ModernCard(glass=True).classes('w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Currencies').classes('text-xl font-black text-white')
                    self.search_input = ui.input(placeholder='Search currencies...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                    self.search_input.on('input', lambda e: self.filter_rows(e.value))

                column_defs = [
                    {'headerName': 'ID', 'field': 'id', 'width': 80},
                    {'headerName': 'Code', 'field': 'currency_code', 'width': 100},
                    {'headerName': 'Currency Name', 'field': 'currency_name', 'width': 200},
                    {'headerName': 'Symbol', 'field': 'symbol', 'width': 80},
                    {'headerName': 'Rate', 'field': 'exchange_rate', 'width': 100},
                    {'headerName': 'Status', 'field': 'is_active', 'width': 100, 'cellRenderer': 'params => params.value ? "Active" : "Inactive"'},
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
                            self.input_refs['currency_code'].value = selected_row['currency_code']
                            self.input_refs['currency_name'].value = selected_row['currency_name']
                            self.input_refs['symbol'].value = selected_row['symbol']
                            self.input_refs['exchange_rate'].value = selected_row['exchange_rate']
                            self.input_refs['is_active'].value = selected_row['is_active']
                            
                            self.initial_values = {
                                'currency_code': selected_row['currency_code'],
                                'currency_name': selected_row['currency_name'],
                                'symbol': selected_row['symbol'],
                                'exchange_rate': selected_row['exchange_rate'],
                                'is_active': selected_row['is_active'],
                                'id': str(selected_row['id'])
                            }
                            ui.notify(f'Selected: {selected_row["currency_code"]}', color='info')
                    except Exception as e:
                        ui.notify(f'Error selecting currency: {str(e)}', color='negative')
                
                self.table.on('cellClicked', on_row_click)

            # Bottom: Details Form
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Currency Details').classes('text-lg font-black mb-6 text-white')
                with ui.row().classes('w-full gap-6 items-center'):
                    self.input_refs['currency_code'] = ui.input('Currency Code').classes('w-48 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['currency_name'] = ui.input('Currency Name').classes('flex-1 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['symbol'] = ui.input('Symbol').classes('w-32 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['exchange_rate'] = ui.number('Exchange Rate').classes('w-48 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['is_active'] = ui.checkbox('Active').classes('text-white').props('dark')
                    self.input_refs['id'] = ui.input('ID (Auto)').classes('w-32 glass-input text-white').props('dark rounded outlined readonly')

        ui.timer(0.1, self.refresh_table, once=True)
        ui.timer(0.2, self.load_max_currency, once=True)

    def filter_rows(self, search_text):
        if not search_text:
            self.table.options['rowData'] = self.row_data
        else:
            search_text = search_text.lower()
            filtered = [row for row in self.row_data if any(search_text in str(v).lower() for v in row.values())]
            self.table.options['rowData'] = filtered
        self.table.update()

@ui.page('/currencies')
def currencies_page_route():
    currencies_page()
