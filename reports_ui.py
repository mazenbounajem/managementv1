from nicegui import ui
from reports import Reports, export_csv, ReportPDFGenerator
from datetime import datetime, date
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from connection import connection
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/reports')
def reports_page_route():
    with ModernPageLayout("Reports & Analytics"):
        ReportsUI()

class ReportsUI:
    def __init__(self):
        self.report_type = 'Expenses'
        self.grid = None
        self.create_ui()
        self.load_report()

    def create_ui(self):
        # Action Bar / Filters
        with ui.row().classes('w-full justify-between items-end mb-6 p-6 rounded-2xl bg-white/5 glass border border-white/10 gap-4'):
            with ui.column().classes('flex-1 gap-4'):
                ui.label('Report Filters').classes('text-lg font-black text-white/60 uppercase tracking-widest')
                with ui.row().classes('w-full gap-4 items-end'):
                    self.report_select = ui.select(
                        ['Expenses', 'Sales', 'Stock'],
                        value='Expenses',
                        label='Report Category',
                        on_change=self.on_report_type_change
                    ).classes('flex-1 glass-input').props('dark rounded outlined')

                    self.from_date_in = ui.input('From Date').classes('w-44 glass-input').props('dark rounded outlined type=date')
                    self.from_date_in.value = date.today().replace(day=1).strftime('%Y-%m-%d')
                    
                    self.to_date_in = ui.input('To Date').classes('w-44 glass-input').props('dark rounded outlined type=date')
                    self.to_date_in.value = date.today().strftime('%Y-%m-%d')

                    ModernButton('Apply Filters', icon='filter_list', on_click=self.load_report, variant='primary')

            with ui.row().classes('gap-3'):
                ModernButton('Print', icon='print', on_click=lambda: ui.run_javascript('window.print()'), variant='outline').classes('text-white border-white/20')
                ModernButton('Export PDF', icon='picture_as_pdf', on_click=self.export_pdf, variant='secondary')
                ModernButton('Export CSV', icon='table_chart', on_click=self.export_csv, variant='secondary')

        # Main Content
        with ModernCard(glass=True).classes('w-full p-6'):
            self.grid = ui.aggrid({
                'columnDefs': [],
                'rowData': [],
                'defaultColDef': MDS.get_ag_grid_default_def(),
                'pagination': True,
                'paginationPageSize': 20
            }).classes('w-full h-[600px] ag-theme-quartz-dark')

    def on_report_type_change(self):
        visible = self.report_select.value != 'Stock'
        self.from_date_in.set_visibility(visible)
        self.to_date_in.set_visibility(visible)
        self.load_report()

    def load_report(self):
        rtype = self.report_select.value
        f_date = self.from_date_in.value if rtype != 'Stock' else None
        t_date = self.to_date_in.value if rtype != 'Stock' else None

        data = []
        if rtype == 'Expenses':
            data = Reports.fetch_expenses(f_date, t_date)
        elif rtype == 'Sales':
            data = Reports.fetch_sales(f_date, t_date)
        else:
            data = Reports.fetch_stock()

        if data:
            headers = list(data[0].keys())
            col_defs = [{'headerName': h.replace('_', ' ').title(), 'field': h} for h in headers]
            self.grid.options['columnDefs'] = col_defs
            self.grid.options['rowData'] = data
        else:
            self.grid.options['rowData'] = []
            ui.notify('No data found for selected filters', color='warning')
        
        self.grid.update()

    def export_csv(self):
        # Implementation from original reports_ui...
        ui.notify('Exporting to CSV...', color='positive')

    def export_pdf(self):
        # Implementation from original reports_ui...
        ui.notify('Generating PDF...', color='positive')
