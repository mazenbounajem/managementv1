from nicegui import ui
from reports import Reports, export_csv, ReportPDFGenerator
from datetime import datetime, date
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from connection import connection
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

def reports_content(standalone=False):
    """Content method for reports that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Reports & Analytics", standalone=standalone):
            ReportsUI(standalone=False)
    else:
        ReportsUI(standalone=False)

@ui.page('/reports')
def reports_page_route():
    reports_content(standalone=True)

class ReportsUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.report_type = 'Expenses'
        self.grid = None
        self.report_select = None
        self.from_date_in = None
        self.to_date_in = None
        self.create_ui()
        self.load_report()

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Reports & Analytics", standalone=True)
            layout_container.__enter__()
        
        try:
            # Action Bar / Filters
            with ui.row().classes('w-full justify-between items-end mb-6 p-6 rounded-2xl bg-white/5 glass border border-white/10 gap-4'):
                with ui.column().classes('flex-1 gap-4'):
                    ui.label('Report Filters').classes('text-lg font-black text-white/60 uppercase tracking-widest')
                    with ui.row().classes('w-full gap-4 items-end'):
                        self.report_select = ui.select(
                            ['Expenses', 'Sales', 'Stock', 'User Discounts', 'Trial Balance'],
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
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def on_report_type_change(self):
        visible = self.report_select.value not in ['Stock', 'Trial Balance']
        self.from_date_in.set_visibility(visible)
        self.to_date_in.set_visibility(visible)
        self.load_report()

    def load_report(self):
        rtype = self.report_select.value
        f_date = self.from_date_in.value if rtype not in ['Stock', 'Trial Balance'] else None
        t_date = self.to_date_in.value if rtype not in ['Stock', 'Trial Balance'] else None

        data = []
        if rtype == 'Expenses':
            data = Reports.fetch_expenses(f_date, t_date)
        elif rtype == 'Sales':
            data = Reports.fetch_sales(f_date, t_date)
        elif rtype == 'Stock':
            data = Reports.fetch_stock()
        elif rtype == 'User Discounts':
            data = Reports.fetch_user_discounts(f_date, t_date)
        elif rtype == 'Trial Balance':
            data = Reports.fetch_trial_balance()

        if data:
            headers = list(data[0].keys())
            col_defs = [{'headerName': h.replace('_', ' ').title(), 'field': h, 'sortable': True, 'filter': True} for h in headers]
            self.grid.options['columnDefs'] = col_defs
            self.grid.options['rowData'] = data
        else:
            self.grid.options['rowData'] = []
            ui.notify('No data found for selected filters', color='warning')
        
        self.grid.update()

    def export_csv(self):
        rtype = self.report_select.value
        f_date = self.from_date_in.value if rtype not in ['Stock', 'Trial Balance'] else None
        t_date = self.to_date_in.value if rtype not in ['Stock', 'Trial Balance'] else None

        data = []
        if rtype == 'Expenses':
            data = Reports.fetch_expenses(f_date, t_date)
        elif rtype == 'Sales':
            data = Reports.fetch_sales(f_date, t_date)
        elif rtype == 'Stock':
            data = Reports.fetch_stock()
        elif rtype == 'User Discounts':
            data = Reports.fetch_user_discounts(f_date, t_date)
        elif rtype == 'Trial Balance':
            data = Reports.fetch_trial_balance()

        if data:
            headers = list(data[0].keys())
            csv_data = export_csv(data, headers)
            ui.download(csv_data, f'{rtype.lower().replace(" ", "_")}_report.csv')
            ui.notify('CSV export started', color='positive')
        else:
            ui.notify('No data to export', color='warning')

    def export_pdf(self):
        rtype = self.report_select.value
        f_date = self.from_date_in.value if rtype not in ['Stock', 'Trial Balance'] else None
        t_date = self.to_date_in.value if rtype not in ['Stock', 'Trial Balance'] else None

        data = []
        if rtype == 'Expenses':
            data = Reports.fetch_expenses(f_date, t_date)
        elif rtype == 'Sales':
            data = Reports.fetch_sales(f_date, t_date)
        elif rtype == 'Stock':
            data = Reports.fetch_stock()
        elif rtype == 'User Discounts':
            data = Reports.fetch_user_discounts(f_date, t_date)
        elif rtype == 'Trial Balance':
            data = Reports.fetch_trial_balance()

        if data:
            headers = list(data[0].keys())
            generator = ReportPDFGenerator(f'{rtype} Report')
            pdf_data = generator.generate(headers, data)
            ui.download(pdf_data, f'{rtype.lower().replace(" ", "_")}_report.pdf')
            ui.notify('PDF export started', color='positive')
        else:
            ui.notify('No data to export', color='warning')