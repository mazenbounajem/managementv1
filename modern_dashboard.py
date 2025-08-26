from nicegui import ui
from datetime import datetime
import random

class ModernDashboard:
    def __init__(self):
        self.setup_theme()
        self.create_dashboard()
    
    def setup_theme(self):
        """Setup unified theme and styling"""
        ui.add_head_html('''
            <style>
                .gradient-bg {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .glass-card {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 15px;
                }
                .hover-scale {
                    transition: transform 0.3s ease;
                }
                .hover-scale:hover {
                    transform: scale(1.05);
                }
                .stat-card {
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    border-radius: 15px;
                    padding: 20px;
                    color: white;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                }
                .nav-item {
                    transition: all 0.3s ease;
                    border-radius: 10px;
                    margin: 5px 0;
                }
                .nav-item:hover {
                    background: rgba(255, 255, 255, 0.1);
                    transform: translateX(5px);
                }
            </style>
        ''')
    
    def create_dashboard(self):
        """Create modern dashboard with unified styling"""
        with ui.header().classes('gradient-bg text-white'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('POS Management System').classes('text-2xl font-bold')
                with ui.row().classes('items-center gap-4'):
                    ui.label(f'Welcome, Admin!').classes('text-lg')
                    ui.button('Logout', icon='logout', on_click=lambda: ui.navigate.to('/login')).props('flat color=white')
        
        with ui.row().classes('w-full h-screen'):
            # Sidebar Navigation
            with ui.column().classes('w-64 bg-gradient-to-b from-purple-600 to-blue-600 text-white p-4'):
                ui.label('Navigation').classes('text-xl font-bold mb-4')
                
                nav_items = [
                    ('dashboard', 'Dashboard', 'dashboard'),
                    ('shopping_cart', 'Sales', 'sales'),
                    ('inventory', 'Products', 'products'),
                    ('people', 'Customers', 'customers'),
                    ('local_shipping', 'Suppliers', 'suppliers'),
                    ('category', 'Categories', 'categories'),
                    ('receipt', 'Reports', 'reports'),
                    ('settings', 'Settings', 'settings')
                ]
                
                for icon, label, route in nav_items:
                    with ui.row().classes('nav-item p-3 cursor-pointer items-center gap-3').on('click', lambda r=route: ui.navigate.to(f'/{r}')):
                        ui.icon(icon).classes('text-xl')
                        ui.label(label).classes('text-lg')
            
            # Main Content Area
            with ui.column().classes('flex-1 p-6 bg-gray-50 overflow-y-auto'):
                # Stats Cards
                with ui.row().classes('w-full gap-6 mb-6'):
                    stats = [
                        ('Total Sales', '$12,450', 'trending_up', 'green'),
                        ('Products', '1,234', 'inventory', 'blue'),
                        ('Customers', '567', 'people', 'purple'),
                        ('Suppliers', '89', 'local_shipping', 'orange')
                    ]
                    
                    for title, value, icon, color in stats:
                        with ui.card().classes(f'stat-card hover-scale flex-1'):
                            with ui.row().classes('items-center justify-between'):
                                with ui.column():
                                    ui.label(title).classes('text-sm opacity-80')
                                    ui.label(value).classes('text-2xl font-bold')
                                ui.icon(icon).classes('text-3xl opacity-80')
                
                # Quick Actions
                with ui.row().classes('w-full gap-6 mb-6'):
                    ui.label('Quick Actions').classes('text-2xl font-bold text-gray-800')
                    
                    actions = [
                        ('New Sale', 'point_of_sale', 'green'),
                        ('Add Product', 'add_box', 'blue'),
                        ('New Customer', 'person_add', 'purple'),
                        ('View Reports', 'analytics', 'orange')
                    ]
                    
                    for label, icon, color in actions:
                        ui.button(label, icon=icon).props(f'flat color={color}').classes('hover-scale')
                
                # Recent Activity
                with ui.row().classes('w-full gap-6'):
                    # Recent Sales
                    with ui.card().classes('flex-1'):
                        ui.label('Recent Sales').classes('text-xl font-bold mb-4')
                        columns = [
                            {'name': 'id', 'label': 'ID', 'field': 'id'},
                            {'name': 'customer', 'label': 'Customer', 'field': 'customer'},
                            {'name': 'amount', 'label': 'Amount', 'field': 'amount'},
                            {'name': 'date', 'label': 'Date', 'field': 'date'}
                        ]
                        
                        # Mock data
                        rows = [
                            {'id': '#1001', 'customer': 'John Doe', 'amount': '$125.50', 'date': '2024-01-15'},
                            {'id': '#1002', 'customer': 'Jane Smith', 'amount': '$89.99', 'date': '2024-01-15'},
                            {'id': '#1003', 'customer': 'Bob Johnson', 'amount': '$234.00', 'date': '2024-01-14'}
                        ]
                        
                        ui.table(columns=columns, rows=rows).classes('w-full')
                    
                    # Low Stock Alert
                    with ui.card().classes('flex-1'):
                        ui.label('Low Stock Alert').classes('text-xl font-bold mb-4')
                        columns = [
                            {'name': 'product', 'label': 'Product', 'field': 'product'},
                            {'name': 'stock', 'label': 'Stock', 'field': 'stock'},
                            {'name': 'status', 'label': 'Status', 'field': 'status'}
                        ]
                        
                        # Mock data
                        rows = [
                            {'product': 'iPhone 15', 'stock': '5', 'status': 'Low'},
                            {'product': 'Samsung S24', 'stock': '3', 'status': 'Critical'},
                            {'product': 'iPad Pro', 'stock': '8', 'status': 'Low'}
                        ]
                        
                        ui.table(columns=columns, rows=rows).classes('w-full')

# Create modern login page
class ModernLoginPage:
    def __init__(self):
        self.create_login_ui()
    
    def create_login_ui(self):
        with ui.row().classes('w-full h-screen items-center justify-center gradient-bg'):
            with ui.card().classes('glass-card p-8 w-96'):
                ui.label('Welcome Back').classes('text-3xl font-bold text-white mb-2 text-center')
                ui.label('Sign in to your POS system').classes('text-white opacity-80 mb-6 text-center')
                
                username = ui.input('Username').classes('w-full mb-4').props('bg-color=white outlined')
                password = ui.input('Password', password=True).classes('w-full mb-6').props('bg-color=white outlined')
                
                ui.button('Sign In', 
                         on_click=lambda: self.handle_login(username.value, password.value)
                ).classes('w-full bg-white text-purple-600 font-bold py-3').props('rounded')
                
                ui.label('Forgot password?').classes('text-white opacity-80 text-center mt-4 cursor-pointer hover:opacity-100')
    
    def handle_login(self, username, password):
        if username and password:
            ui.notify('Login successful!', color='positive')
            ui.navigate.to('/dashboard')
        else:
            ui.notify('Please enter username and password', color='negative')

# Theme configuration
class ThemeConfig:
    @staticmethod
    def apply_theme():
        """Apply unified theme across all pages"""
        ui.colors(primary='#667eea', secondary='#764ba2', accent='#f093fb', 
                 positive='#4caf50', negative='#f44336', info='#2196f3', 
                 warning='#ff9800')

# Routes
@ui.page('/')
def index():
    ModernLoginPage()

@ui.page('/dashboard')
def dashboard():
    ModernDashboard()

@ui.page('/login')
def login():
    ModernLoginPage()

# Apply theme globally
ThemeConfig.apply_theme()
ui.run()
