from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from datetime import datetime
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

def journal_voucher_content(standalone=False):
    """Content method for journal vouchers that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Journal Vouchers", standalone=standalone):
            JournalVoucherUI(standalone=False)
    else:
        JournalVoucherUI(standalone=False)

@ui.page('/journal_voucher')
def journal_voucher_page_route():
    journal_voucher_content(standalone=True)

class JournalVoucherUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.current_header_id = None
        self.header_inputs = {}
        self.lines_inputs = {}
        self.headers_grid = None
        self.lines_grid = None
        self.create_ui()
        self.refresh_headers_table()

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Journal Vouchers", standalone=True)
            layout_container.__enter__()
        
        try:
            # Action Bar
            with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
                with ui.row().classes('gap-3'):
                    ModernButton('New Voucher', icon='add', on_click=self.clear_all, variant='primary')
                    ModernButton('Save Header', icon='save', on_click=self.save_header, variant='success')
                    ModernButton('Delete Voucher', icon='delete', on_click=self.delete_header, variant='error')
                
                ModernButton('Refresh Headers', icon='refresh', on_click=self.refresh_headers_table, variant='outline').classes('text-white border-white/20')

            with ui.column().classes('w-full gap-8'):
                # Header Section (Master)
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Voucher Header').classes('text-xl font-black mb-6 text-white')
                    
                    with ui.row().classes('w-full gap-6'):
                        # Header Grid
                        self.headers_grid = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'ID', 'field': 'id', 'width': 80},
                                {'headerName': 'Date', 'field': 'date', 'width': 120},
                                {'headerName': 'Voucher #', 'field': 'voucher_number', 'width': 150},
                                {'headerName': 'Subtype', 'field': 'subtype_code', 'width': 100},
                                {'headerName': 'Ref', 'field': 'manual_reference', 'width': 150}
                            ],
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('flex-1 h-64 ag-theme-quartz-dark')
                        self.headers_grid.on('cellClicked', lambda e: self.load_header_data(e.args['data']['id']))

                        # Header Form
                        with ui.column().classes('w-80 gap-4'):
                            self.header_inputs['date'] = ui.input('Date').classes('w-full glass-input').props('dark rounded outlined type=date')
                            self.header_inputs['date'].value = str(datetime.now().date())
                            self.header_inputs['voucher_number'] = ui.input('Voucher #').classes('w-full glass-input').props('dark rounded outlined')
                            
                            subtype_data = []
                            connection.contogetrows("SELECT code, name FROM subtype", subtype_data)
                            subtype_options = {row[0]: f"{row[0]} - {row[1]}" for row in subtype_data}
                            self.header_inputs['subtype'] = ui.select(subtype_options, label='Subtype').classes('w-full glass-input').props('dark rounded outlined')
                            
                            self.header_inputs['manual_reference'] = ui.input('Reference').classes('w-full glass-input').props('dark rounded outlined')

                # Lines Section (Detail)
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Voucher Lines').classes('text-xl font-black mb-6 text-white')
                    
                    # Inline Add Line Form
                    with ui.row().classes('w-full gap-4 items-end mb-6'):
                        account_data = []
                        connection.contogetrows("SELECT number, account_name FROM auxiliary", account_data)
                        account_options = {row[0]: f"{row[0]} - {row[1]}" for row in account_data}
                        self.lines_inputs['account'] = ui.select(account_options, label='Account').classes('w-64 glass-input').props('dark rounded outlined')
                        
                        currency_data = []
                        connection.contogetrows("SELECT currency_code FROM currencies", currency_data)
                        currency_options = [row[0] for row in currency_data]
                        self.lines_inputs['currency'] = ui.select(currency_options, label='Cur').classes('w-24 glass-input').props('dark rounded outlined')
                        
                        self.lines_inputs['debit'] = ui.number('Debit', value=0.0).classes('w-32 glass-input').props('dark rounded outlined')
                        self.lines_inputs['credit'] = ui.number('Credit', value=0.0).classes('w-32 glass-input').props('dark rounded outlined')
                        ModernButton('Add Line', icon='add', on_click=self.add_line, variant='primary').classes('h-14')

                    # Lines Grid
                    self.lines_grid = ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'Account', 'field': 'account', 'width': 150},
                            {'headerName': 'Cur', 'field': 'currency_code', 'width': 80},
                            {'headerName': 'Debit', 'field': 'debit', 'width': 100, 'valueFormatter': "'$' + x.toLocaleString()"},
                            {'headerName': 'Credit', 'field': 'credit', 'width': 100, 'valueFormatter': "'$' + x.toLocaleString()"},
                            {'headerName': 'Remark', 'field': 'remark', 'width': 200, 'flex': 1},
                        ],
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-80 ag-theme-quartz-dark')
                    
                    async def delete_line():
                        selected = await self.lines_grid.get_selected_row()
                        if selected:
                            try:
                                connection.deleterow("DELETE FROM journal_voucher_lines WHERE id=?", selected['id'])
                                ui.notify('Line deleted', color='positive')
                                self.refresh_lines_table()
                            except Exception as e:
                                ui.notify(f'Error deleting line: {str(e)}', color='negative')
                    
                    with ui.row().classes('w-full justify-end mt-4'):
                        ModernButton('Delete Selected Line', icon='delete', on_click=delete_line, variant='error').classes('text-white')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def clear_all(self):
        self.current_header_id = None
        self.header_inputs['date'].value = str(datetime.now().date())
        self.header_inputs['voucher_number'].value = ''
        self.header_inputs['subtype'].value = None
        self.header_inputs['manual_reference'].value = ''
        self.lines_grid.options['rowData'] = []
        self.lines_grid.update()
        ui.notify('New voucher entry', color='info')

    def save_header(self):
        date = self.header_inputs['date'].value
        voucher_number = self.header_inputs['voucher_number'].value
        subtype_code = self.header_inputs['subtype'].value
        manual_reference = self.header_inputs['manual_reference'].value

        if not voucher_number or not subtype_code:
            ui.notify('Voucher # and Subtype are required', color='warning')
            return

        try:
            if self.current_header_id:
                sql = "UPDATE journal_voucher_header SET date=?, voucher_number=?, subtype_code=?, manual_reference=? WHERE id=?"
                values = (date, voucher_number, subtype_code, manual_reference, self.current_header_id)
            else:
                sql = "INSERT INTO journal_voucher_header (date, voucher_number, subtype_code, manual_reference) VALUES (?, ?, ?, ?)"
                values = (date, voucher_number, subtype_code, manual_reference)

            connection.insertingtodatabase(sql, values)
            
            if not self.current_header_id:
                # Get the new header ID
                id_data = []
                connection.contogetrows("SELECT MAX(id) FROM journal_voucher_header", id_data)
                self.current_header_id = id_data[0][0] if id_data else None

            ui.notify('Header saved successfully', color='positive')
            self.refresh_headers_table()
        except Exception as e:
            ui.notify(f'Error saving header: {str(e)}', color='negative')

    def add_line(self):
        if not self.current_header_id:
            ui.notify('Save header first', color='warning')
            return

        account = self.lines_inputs['account'].value
        currency = self.lines_inputs['currency'].value
        debit = float(self.lines_inputs['debit'].value or 0)
        credit = float(self.lines_inputs['credit'].value or 0)

        if not account:
            ui.notify('Select an account', color='warning')
            return
        
        if debit == 0 and credit == 0:
            ui.notify('Either Debit or Credit must be greater than 0', color='warning')
            return

        try:
            sql = "INSERT INTO journal_voucher_lines (header_id, account, currency_code, debit, credit) VALUES (?, ?, ?, ?, ?)"
            values = (self.current_header_id, account, currency, debit, credit)
            connection.insertingtodatabase(sql, values)
            ui.notify('Line added', color='positive')
            self.refresh_lines_table()
            self.lines_inputs['debit'].value = 0
            self.lines_inputs['credit'].value = 0
        except Exception as e:
            ui.notify(f'Error adding line: {str(e)}', color='negative')

    def delete_header(self):
        if not self.current_header_id:
            ui.notify('No voucher selected', color='warning')
            return

        try:
            connection.deleterow("DELETE FROM journal_voucher_lines WHERE header_id=?", self.current_header_id)
            connection.deleterow("DELETE FROM journal_voucher_header WHERE id=?", self.current_header_id)
            ui.notify('Voucher deleted', color='positive')
            self.clear_all()
            self.refresh_headers_table()
        except Exception as e:
            ui.notify(f'Error deleting: {str(e)}', color='negative')

    def refresh_headers_table(self):
        try:
            data = []
            connection.contogetrows("SELECT id, date, voucher_number, subtype_code, manual_reference FROM journal_voucher_header ORDER BY id DESC", data)
            rows = []
            for r in data:
                rows.append({'id': r[0], 'date': str(r[1]), 'voucher_number': r[2], 'subtype_code': r[3], 'manual_reference': r[4]})
            self.headers_grid.options['rowData'] = rows
            self.headers_grid.update()
        except Exception as e:
            ui.notify(f'Error refreshing headers: {str(e)}', color='negative')

    def refresh_lines_table(self):
        try:
            data = []
            connection.contogetrows(f"SELECT id, account, currency_code, debit, credit, remark FROM journal_voucher_lines WHERE header_id={self.current_header_id}", data)
            rows = []
            for r in data:
                rows.append({'id': r[0], 'account': r[1], 'currency_code': r[2], 'debit': float(r[3] or 0), 'credit': float(r[4] or 0), 'remark': r[5] or ''})
            self.lines_grid.options['rowData'] = rows
            self.lines_grid.update()
        except Exception as e:
            ui.notify(f'Error refreshing lines: {str(e)}', color='negative')

    def load_header_data(self, header_id):
        self.current_header_id = header_id
        try:
            data = []
            connection.contogetrows(f"SELECT date, voucher_number, subtype_code, manual_reference FROM journal_voucher_header WHERE id={header_id}", data)
            if data:
                r = data[0]
                self.header_inputs['date'].value = str(r[0])
                self.header_inputs['voucher_number'].value = r[1]
                self.header_inputs['subtype'].value = r[2]
                self.header_inputs['manual_reference'].value = r[3]
                self.refresh_lines_table()
        except Exception as e:
            ui.notify(f'Error loading voucher: {str(e)}', color='negative')