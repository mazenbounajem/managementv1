from nicegui import ui
from connection import connection
from datetime import datetime, date
from uiaggridtheme import uiAggridTheme

class TimeSpendUI:
    def __init__(self, show_header=True):
        self.from_date = None
        self.to_date = None
        self.hourly_rate = 0.0
        self.total_minutes = 0
        self.total_hours = 0.0
        self.total_cost = 0.0

        if show_header:
            with ui.header().classes('items-center justify-between'):
                ui.label('Time Spend Analysis').classes('text-2xl font-bold')
                ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

        # Initialize UI
        self.create_ui()

    def create_ui(self):
        """Create the main UI layout."""
        with ui.element('div').classes('flex w-full h-screen p-4'):
            # Filters section
            with ui.element('div').classes('w-full mb-4'):
                with ui.row().classes('w-full items-center gap-4 p-4 bg-blue-50 rounded-lg'):
                    ui.label('Date Filters:').classes('text-lg font-semibold')

                    # From date picker
                    self.from_date_input = ui.input('From Date', value=date.today().strftime('%Y-%m-%d')).classes('w-40')
                    self.from_date_input.props('type=date')

                    # To date picker
                    self.to_date_input = ui.input('To Date', value=date.today().strftime('%Y-%m-%d')).classes('w-40')
                    self.to_date_input.props('type=date')

                    # Filter button
                    ui.button('Filter Data', on_click=self.filter_data).props('color=primary').classes('px-6')

                    # Refresh button
                    ui.button('Refresh', on_click=self.load_data).props('color=secondary').classes('px-6')

            # AG Grid container
            with ui.element('div').classes('w-full h-[calc(100vh-400px)] border rounded-lg bg-white shadow-sm mb-4'):
                uiAggridTheme.addingtheme()

                # Define columns for the grid
                self.columns = [
                    {'headerName': 'Date', 'field': 'login_date', 'width': 120, 'filter': True, 'headerClass': 'green-header'},
                    {'headerName': 'User', 'field': 'username', 'width': 150, 'filter': True, 'headerClass': 'green-header'},
                    {'headerName': 'Login Time', 'field': 'login_time', 'width': 120, 'filter': True, 'headerClass': 'green-header'},
                    {'headerName': 'Logout Date', 'field': 'logout_date', 'width': 120, 'filter': True, 'headerClass': 'green-header'},
                    {'headerName': 'Logout Time', 'field': 'logout_time', 'width': 120, 'filter': True, 'headerClass': 'green-header'},
                    {'headerName': 'Duration (Minutes)', 'field': 'session_duration_minutes', 'width': 150, 'filter': True, 'headerClass': 'green-header'}
                ]

                # Create AG Grid
                self.aggrid = ui.aggrid({
                    'columnDefs': self.columns,
                    'rowData': [],
                    'defaultColDef': {'flex': 1, 'minWidth': 80, 'sortable': True, 'filter': True},
                    'rowSelection': 'single',
                    'domLayout': 'normal'
                }).classes('w-full h-full p-2 ag-theme-quartz-custom')

            # Summary section
            with ui.element('div').classes('w-full p-4 bg-gray-50 rounded-lg mb-4'):
                with ui.row().classes('w-full justify-between items-center'):
                    # Left side - totals
                    with ui.column().classes('gap-2'):
                        ui.label('Summary').classes('text-xl font-bold text-gray-700')
                        self.total_sessions_label = ui.label('Total Sessions: 0').classes('text-lg')
                        self.total_minutes_label = ui.label('Total Minutes: 0').classes('text-lg')
                        self.total_hours_label = ui.label('Total Hours: 0.00').classes('text-lg font-semibold text-blue-600')

                    # Right side - calculation system
                    with ui.column().classes('gap-2 items-end'):
                        ui.label('Cost Calculation').classes('text-xl font-bold text-gray-700')

                        with ui.row().classes('items-center gap-2'):
                            ui.label('Hourly Rate ($):').classes('text-lg')
                            self.hourly_rate_input = ui.number('Hourly Rate', value=0.0, min=0, step=0.01).classes('w-32')
                            self.hourly_rate_input.on('change', self.calculate_cost)

                        self.total_cost_label = ui.label('Total Cost: $0.00').classes('text-2xl font-bold text-green-600')

            # Load initial data
            self.load_data()

    def load_data(self):
        """Load session data from database."""
        try:
            # Query to get session data with user information
            sql = """
            SELECT
                us.login_date,
                u.username,
                us.login_time,
                us.logout_date,
                us.logout_time,
                us.session_duration_minutes
            FROM user_sessions us
            INNER JOIN users u ON us.user_id = u.id
            ORDER BY us.login_date DESC, us.login_time DESC
            """

            raw_data = []
            connection.contogetrows(sql, raw_data)

            # Convert to AG Grid format
            self.session_data = []
            for row in raw_data:
                self.session_data.append({
                    'login_date': str(row[0]) if row[0] else '',
                    'username': str(row[1]) if row[1] else '',
                    'login_time': str(row[2]) if row[2] else '',
                    'logout_date': str(row[3]) if row[3] else '',
                    'logout_time': str(row[4]) if row[4] else '',
                    'session_duration_minutes': int(row[5]) if row[5] else 0
                })

            # Update grid
            self.aggrid.options['rowData'] = self.session_data
            self.aggrid.update()

            # Calculate totals
            self.calculate_totals()

            ui.notify(f'Loaded {len(self.session_data)} session records', color='green')

        except Exception as e:
            ui.notify(f'Error loading data: {str(e)}', color='red')
            print(f'Error loading session data: {str(e)}')

    def filter_data(self):
        """Filter data based on date range."""
        try:
            from_date_str = self.from_date_input.value
            to_date_str = self.to_date_input.value

            if not from_date_str or not to_date_str:
                ui.notify('Please select both from and to dates', color='red')
                return

            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

            # Filter the data
            filtered_data = []
            for row in self.session_data:
                if row['login_date']:
                    try:
                        session_date = datetime.strptime(row['login_date'], '%Y-%m-%d').date()
                        if from_date <= session_date <= to_date:
                            filtered_data.append(row)
                    except ValueError:
                        continue

            # Update grid with filtered data
            self.aggrid.options['rowData'] = filtered_data
            self.aggrid.update()

            # Calculate totals for filtered data
            self.calculate_totals(filtered_data)

            ui.notify(f'Filtered to {len(filtered_data)} records between {from_date_str} and {to_date_str}', color='green')

        except Exception as e:
            ui.notify(f'Error filtering data: {str(e)}', color='red')
            print(f'Error filtering data: {str(e)}')

    def calculate_totals(self, data=None):
        """Calculate totals for the data."""
        if data is None:
            data = self.session_data

        total_sessions = len(data)
        total_minutes = sum(row['session_duration_minutes'] for row in data if row['session_duration_minutes'])
        total_hours = total_minutes / 60.0

        # Update labels
        self.total_sessions_label.text = f'Total Sessions: {total_sessions}'
        self.total_minutes_label.text = f'Total Minutes: {total_minutes}'
        self.total_hours_label.text = f'Total Hours: {total_hours:.2f}'

        # Store values for cost calculation
        self.total_minutes = total_minutes
        self.total_hours = total_hours

        # Recalculate cost if hourly rate is set
        self.calculate_cost()

    def calculate_cost(self):
        """Calculate total cost based on hourly rate."""
        try:
            hourly_rate = float(self.hourly_rate_input.value or 0)
            total_cost = self.total_hours * hourly_rate

            self.total_cost_label.text = f'Total Cost: ${total_cost:.2f}'

        except ValueError:
            self.total_cost_label.text = 'Total Cost: $0.00'

@ui.page('/timespend')
def timespend_page_route():
    TimeSpendUI()
