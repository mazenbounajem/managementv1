from nicegui import ui
from reports import Reports, export_csv, ReportPDFGenerator
from datetime import datetime, date
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from connection import connection

class ReportsUI:
    def __init__(self):
        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        permissions = connection.get_user_permissions(user['role_id'])
        allowed_pages = {page for page, can_access in permissions.items() if can_access}

        # Create enhanced navigation instance
        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_drawer()  # Create drawer first
        navigation.create_navigation_header()  # Then create header with toggle button
        # Add print-specific CSS
        ui.add_head_html('''
            <style>
                @media print {
                    .no-print {
                        display: none !important;
                    }
                    .print-only {
                        display: block !important;
                    }
                    body {
                        margin: 0;
                        padding: 20px;
                    }
                    .print-header {
                        text-align: center;
                        margin-bottom: 20px;
                        border-bottom: 2px solid #333;
                        padding-bottom: 10px;
                    }
                    .print-title {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }
                    .print-subtitle {
                        font-size: 16px;
                        color: #666;
                    }
                    .print-date {
                        font-size: 14px;
                        color: #999;
                        margin-top: 10px;
                    }
                }
                .print-only {
                    display: none;
                }
            </style>
        ''')

        ui.label('Reports').classes('text-2xl font-bold mb-4 no-print')

        self.report_select = ui.select(
            ['Expenses', 'Sales', 'Stock'],
            value='Expenses',
            on_change=self.on_report_type_change
        ).classes('w-1/3 mb-4 no-print')

        # Date range inputs with calendar menu
        with ui.row().classes('w-full mb-4 gap-4 items-center no-print'):
            # From Date input with calendar
            with ui.input('From Date').classes('w-1/4') as from_date_input:
                with ui.menu().props('no-parent-event') as from_menu:
                    self.from_date = ui.date(value=date.today().replace(day=1)).bind_value(from_date_input)
                    with ui.row().classes('justify-end'):
                        ui.button('Close', on_click=from_menu.close).props('flat')
                with from_date_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', from_menu.open).classes('cursor-pointer')
            
            # To Date input with calendar
            with ui.input('To Date').classes('w-1/4') as to_date_input:
                with ui.menu().props('no-parent-event') as to_menu:
                    self.to_date = ui.date(value=date.today()).bind_value(to_date_input)
                    with ui.row().classes('justify-end'):
                        ui.button('Close', on_click=to_menu.close).props('flat')
                with to_date_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', to_menu.open).classes('cursor-pointer')
            
            ui.button('Apply Filter', on_click=self.load_report).props('color=primary')

        # Print-only header (hidden by default, shown only when printing)
        with ui.column().classes('print-only').style('display: none;'):
            with ui.column().classes('print-header'):
                ui.label('SALES MANAGEMENT SYSTEM').classes('print-title')
                ui.label('REPORT').classes('print-subtitle')
                self.print_date_label = ui.label('').classes('print-date')
                self.print_report_type_label = ui.label('').classes('print-subtitle')
                self.print_date_range_label = ui.label('').classes('print-date')

        self.grid = ui.aggrid({
            'columnDefs': [],
            'rowData': [],
            'defaultColDef': {'flex': 1, 'sortable': True, 'filter': True}
        }).classes('w-full h-96 mb-4')

        with ui.row().classes('gap-4 no-print'):
            ui.button('Refresh', on_click=self.load_report).props('color=secondary')
            ui.button('Export CSV', on_click=self.export_csv).props('color=primary')
            ui.button('Export PDF', on_click=self.export_pdf).props('color=secondary')
            ui.button('Print', on_click=self.print_report).props('color=primary')

        self.on_report_type_change()

    def on_report_type_change(self):
        # Show/hide date filters based on report type
        report_type = self.report_select.value
        if report_type in ['Expenses', 'Sales']:
            self.from_date.set_visibility(True)
            self.to_date.set_visibility(True)
        else:
            self.from_date.set_visibility(False)
            self.to_date.set_visibility(False)
        self.load_report()

    def load_report(self):
        report_type = self.report_select.value

        # Get date values if applicable
        from_date = None
        to_date = None
        if report_type in ['Expenses', 'Sales']:
            from_date = self.from_date.value.strftime('%Y-%m-%d') if self.from_date.value else None
            to_date = self.to_date.value.strftime('%Y-%m-%d') if self.to_date.value else None

        # Fetch data with date filtering
        if report_type == 'Expenses':
            data = Reports.fetch_expenses(from_date, to_date)
        elif report_type == 'Sales':
            data = Reports.fetch_sales(from_date, to_date)
        else:
            data = Reports.fetch_stock()

        # Get headers dynamically from the data (first row keys)
        if data:
            headers = list(data[0].keys())

            # Filter out ID columns that have corresponding name columns
            filtered_headers = []
            for header in headers:
                # For sales reports, exclude customer_id if customer_name exists
                if report_type == 'Sales' and header == 'customer_id' and 'customer_name' in headers:
                    continue
                # For stock reports, exclude category_id and supplier_id if name columns exist
                elif report_type == 'Stock':
                    if (header == 'category_id' and 'category_name' in headers) or \
                       (header == 'supplier_id' and 'supplier_name' in headers):
                        continue
                filtered_headers.append(header)

            headers = filtered_headers
            # Convert snake_case to Title Case for display
            display_headers = [h.replace('_', ' ').title() for h in headers]
        else:
            headers = []
            display_headers = []

        self.headers = display_headers
        self.data = data

        # Prepare column definitions and row data
        column_defs = [{'headerName': dh, 'field': h} for dh, h in zip(display_headers, headers)]
        row_data = data  # Data is already in the correct format

        self.grid.options['columnDefs'] = column_defs
        self.grid.options['rowData'] = row_data
        self.grid.update()

    def export_csv(self):
        csv_data = export_csv(self.data, self.headers)
        ui.download(csv_data, f'report_{self.report_select.value.lower()}_{datetime.now().strftime("%Y%m%d")}.csv')

    def export_pdf(self):
        pdf_gen = ReportPDFGenerator(f'{self.report_select.value} Report')
        pdf_data = pdf_gen.generate(self.headers, self.data)
        ui.download(pdf_data, f'report_{self.report_select.value.lower()}_{datetime.now().strftime("%Y%m%d")}.pdf')

    def print_report(self):
        # Update print header information
        report_type = self.report_select.value
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Set print header labels
        self.print_date_label.text = f'Generated: {current_time}'
        self.print_report_type_label.text = f'Report Type: {report_type}'
        
        # Set date range if applicable
        date_range_text = ''
        if report_type in ['Expenses', 'Sales']:
            from_date = self.from_date.value.strftime('%Y-%m-%d') if self.from_date.value else 'N/A'
            to_date = self.to_date.value.strftime('%Y-%m-%d') if self.to_date.value else 'N/A'
            date_range_text = f'Date Range: {from_date} to {to_date}'
        else:
            date_range_text = 'Date Range: All Data'
        
        self.print_date_range_label.text = date_range_text
        
        # Trigger browser print dialog
        ui.run_javascript('window.print()')

@ui.page('/reports')
def reports_page_route():
    ReportsUI()
