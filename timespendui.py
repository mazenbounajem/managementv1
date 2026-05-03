from nicegui import ui
from connection import connection
from datetime import datetime, date
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernStats, ModernButton, ModernInput, ModernTable
import json

class TimeSpendUI:
    def __init__(self, show_header=True):
        self.from_date = date.today().strftime('%Y-%m-%d')
        self.to_date = date.today().strftime('%Y-%m-%d')
        self.hourly_rate = 0.0
        self.total_minutes = 0
        self.total_hours = 0.0
        self.total_cost = 0.0
        self.session_data = []

        # Initialize UI inside a Page Layout
        if show_header:
            with ModernPageLayout("Time Spend Analysis"):
                self.create_ui()
        else:
            self.create_ui()

    def create_ui(self):
        """Create the main UI layout with premium components."""
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # --- TOP SECTION: FILTERS ---
            with ModernCard().classes('w-full p-6'):
                with ui.row().classes('w-full items-center justify-between gap-4'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('calendar_today').classes('text-2xl text-accent')
                        ui.label('Analysis Period').classes('text-xl font-bold text-primary-dark')
                    
                    with ui.row().classes('items-center gap-4'):
                        self.user_select = ui.select(['All Users'], value='All Users', label='Select User').props('outlined dense').classes('w-44').props('with-input')
                        self.from_date_input = ui.input('From', value=self.from_date).props('type=date outlined dense').classes('w-44')
                        self.to_date_input = ui.input('To', value=self.to_date).props('type=date outlined dense').classes('w-44')
                        
                        ModernButton.create('Filter Data', icon='filter_alt', on_click=self.filter_data)
                        ui.button(icon='refresh', on_click=self.load_data).props('flat round color=primary').tooltip('Refresh original data')

            # --- MIDDLE SECTION: STATS CARDS ---
            with ui.row().classes('w-full gap-4'):
                self.sessions_card = ModernStats.create(
                    label='Total Sessions',
                    value='0',
                    icon='history',
                    color=MDS.SECONDARY
                ).classes('flex-1')
                
                self.hours_card = ModernStats.create(
                    label='Total Hours',
                    value='0.00',
                    icon='timer',
                    color=MDS.ACCENT
                ).classes('flex-1')
                
                self.cost_card = ModernStats.create(
                    label='Total Cost',
                    value='$0.00',
                    icon='payments',
                    color=MDS.SUCCESS
                ).classes('flex-1')

            # --- BOTTOM SECTION: DATA GRID & COST CALC ---
            with ui.row().classes('w-full gap-6 items-start'):
                # Data Grid Column
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4 overflow-hidden'):
                        ui.label('Session Details').classes('text-lg font-bold mb-4 ml-2')
                        
                        columns = [
                            {'headerName': 'Date', 'field': 'login_date', 'sortable': True, 'filter': True},
                            {'headerName': 'User', 'field': 'username', 'sortable': True, 'filter': True},
                            {'headerName': 'Login', 'field': 'login_time'},
                            {'headerName': 'Logout', 'field': 'logout_time'},
                            {'headerName': 'Duration (Min)', 'field': 'session_duration_minutes', 'type': 'numericColumn', 'sortable': True}
                        ]
                        
                        self.aggrid = ui.aggrid({
                            'columnDefs': columns,
                            'rowData': [],
                            'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[400px] ag-theme-quartz-dark')

                # Cost Calculation Column
                with ui.column().classes('w-80'):
                    with ModernCard().classes('w-full p-6'):
                        ui.icon('calculate').classes('text-3xl text-accent mb-2')
                        ui.label('Cost Calculator').classes('text-xl font-bold mb-4')
                        
                        ui.label('Set your hourly rate to estimate total labor costs for this period.').classes('text-sm text-muted mb-4')
                        
                        with ui.column().classes('gap-1 mb-4 p-3 bg-accent/5 rounded-lg border border-accent/10'):
                            with ui.row().classes('w-full justify-between'):
                                ui.label('Total Minutes:').classes('text-xs font-bold text-muted')
                                self.total_minutes_label = ui.label('0').classes('text-sm font-black text-accent')
                            with ui.row().classes('w-full justify-between'):
                                ui.label('Total Hours:').classes('text-xs font-bold text-muted')
                                self.total_hours_label = ui.label('0.00').classes('text-sm font-black text-accent')

                        self.hourly_rate_input = ui.number(
                            'Hourly Rate ($)', 
                            value=0.0, 
                            min=0, 
                            step=1.0,
                            format='%.2f',
                            on_change=self.calculate_cost
                        ).props('outlined dense prefix=$').classes('w-full mb-6')
                        
                        with ui.element('div').classes('p-4 rounded-xl bg-primary/5 border border-primary/10'):
                            ui.label('Estimated Expenditure').classes('text-xs font-bold uppercase tracking-widest text-muted mb-1')
                            self.summary_cost_label = ui.label('$0.00').classes('text-3xl font-black text-primary-dark')

            # Load initial data
            self.load_data()

    def load_data(self):
        """Load session data from database."""
        try:
            sql = """
            SELECT us.login_date, u.username, us.login_time, us.logout_date, us.logout_time, us.session_duration_minutes
            FROM user_sessions us
            INNER JOIN users u ON us.user_id = u.id
            ORDER BY us.login_date DESC, us.login_time DESC
            """
            raw_data = []
            connection.contogetrows(sql, raw_data)

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

            self.aggrid.options['rowData'] = self.session_data
            self.aggrid.update()
            self.calculate_totals(self.session_data)
            
            # Load users for dropdown
            users_sql = "SELECT DISTINCT username FROM users"
            users_data = []
            connection.contogetrows(users_sql, users_data)
            user_options = ['All Users'] + [row[0] for row in users_data if row[0]]
            self.user_select.options = user_options
            self.user_select.update()
            
            ui.notify(f'Loaded {len(self.session_data)} records', color='positive')

        except Exception as e:
            ui.notify(f'Error loading data: {str(e)}', color='negative')

    def filter_data(self):
        """Filter data based on date range."""
        try:
            from_date_str = self.from_date_input.value
            to_date_str = self.to_date_input.value

            if not from_date_str or not to_date_str:
                ui.notify('Select a valid date range', color='warning')
                return

            f_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            t_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

            selected_user = self.user_select.value

            filtered = [
                row for row in self.session_data 
                if row['login_date'] and f_date <= datetime.strptime(row['login_date'], '%Y-%m-%d').date() <= t_date
                and (selected_user == 'All Users' or row['username'] == selected_user)
            ]

            self.aggrid.options['rowData'] = filtered
            self.aggrid.update()
            self.calculate_totals(filtered)
            ui.notify(f'Displaying {len(filtered)} filtered records', color='info')

        except Exception as e:
            ui.notify(f'Filtering error: {str(e)}', color='negative')

    def calculate_totals(self, data):
        """Update stat cards and internal totals."""
        total_sessions = len(data)
        total_minutes = sum(row['session_duration_minutes'] for row in data)
        self.total_hours = total_minutes / 60.0

        self.total_minutes_label.set_text(str(total_minutes))
        self.total_hours_label.set_text(f"{self.total_hours:.2f}")

        self.sessions_card.update_value(str(total_sessions))
        self.hours_card.update_value(f"{self.total_hours:.2f}")
        self.calculate_cost()

    def calculate_cost(self):
        """Update cost visibility based on hourly rate."""
        try:
            rate = float(self.hourly_rate_input.value or 0)
            cost = self.total_hours * rate
            cost_str = f"${cost:,.2f}"
            self.cost_card.update_value(cost_str)
            self.summary_cost_label.set_text(cost_str)
        except ValueError:
            pass

@ui.page('/timespend')
def timespend_page_route():
    TimeSpendUI()
