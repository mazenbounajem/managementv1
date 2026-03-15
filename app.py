from nicegui import ui
from reports_ui import reports_page_route
from connection import connection
import datetime
import os
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Import new modules
from config import config
from logger import app_logger, handle_errors
from auth_service import AuthService
from navigation_improvements import EnhancedNavigation

# Add session storage for logged-in user
from session_storage import session_storage

# Import existing modules
from category import category_page_route
from customerui import customer_page_route
from productui import product_page_route
from supplierui import supplier_page_route
from salesui_aggrid_compact import sales_page_route
from purchaseui import purchase_page_route
from employeeui import employee_page_route
from supplier_payment_ui_fixed_v2 import supplier_payment_page_route
from customer_receipt_ui_fixed_v2 import customer_receipt_page_route
from expenses import expenses_page_route
from expensestype import expensestype_page_route
from accounting_finance import accounting_finance_page_route
from roles import roles_page_route
from company_ui import company_page_route
from timespendui import timespend_page_route
from stockoperationui import stock_operations_page_route
from currencies import currencies_page_route
from session_methods import SessionManager
from statisticalreports import statistical_reports_page
from cashdrawer_ui import cash_drawer_page

# Import appointments route
from appointments_ui import appointments_page_route

# Import services route
from services_ui import services_page_route

# Import ledger UI route
from ledgerui import ledger_page_route

# Import auxiliary, journal, and voucher routes
from auxiliaryui import auxiliary_page_route
from journal_voucher_ui import journal_voucher_page_route
from voucher_subtype_ui import voucher_subtype_page_route

# Import modern design system pages
from modern_sales_ui import modern_sales_page

# Stock Reports page
@ui.page('/stock-reports')
def stock_reports_page():
    """Stock Reports page with dropdown to select and view reports"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    # Check permissions
    if not check_page_access('reports'):
        ui.notify('You do not have permission to access reports', color='red')
        ui.run_javascript('window.location.href = "/dashboard"')
        return

    # Get user permissions and create navigation
    permissions = connection.get_user_permissions(user['role_id'])
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_header()
    navigation.create_navigation_drawer()

    with ui.column().classes('p-6 w-full max-w-4xl mx-auto'):
        ui.label('Stock Reports').classes('text-3xl font-bold mb-6 text-center')

        # Stock Reports folder link
        with ui.row().classes('mb-6 items-center'):
            ui.label('Stock Reports Folder:').classes('text-lg font-medium mr-4')
            ui.link('📁 Open Stock Reports Folder', '/stock-reports-folder', new_tab=True).classes('text-blue-600 hover:text-blue-800 underline')

        # Report selection section
        with ui.card().classes('p-6 w-full'):
            ui.label('View Reports').classes('text-xl font-semibold mb-4')

            # Get available PDF reports from stockreports folder
            reports_dir = 'stockreports'
            available_reports = []

            if os.path.exists(reports_dir):
                for file in os.listdir(reports_dir):
                    if file.endswith('.pdf'):
                        available_reports.append(file)

            if not available_reports:
                ui.label('No stock reports available. Please generate reports first.').classes('text-red-600')
                ui.button('Generate All Reports', on_click=lambda: generate_stock_reports_and_refresh()).classes('mt-4 bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded')
            else:
                # Report selection dropdown
                report_select = ui.select(
                    options=available_reports,
                    label='Select Stock Report',
                    value=available_reports[0] if available_reports else None
                ).classes('w-full mb-4')

                # View Report button
                ui.button(
                    'View Report',
                    on_click=lambda: view_selected_stock_report(report_select.value)
                ).classes('bg-green-500 hover:bg-green-700 text-white px-6 py-2 rounded font-medium')

                # Report descriptions
                with ui.column().classes('mt-6 space-y-2'):
                    ui.label('Available Stock Reports:').classes('font-medium')
                    for report in available_reports:
                        if report == 'inventory_report.pdf':
                            ui.label('• Inventory Report - Current stock levels, low stock alerts, and turnover analysis').classes('text-sm text-gray-600')
                        elif report == 'low_stock_alert_report.pdf':
                            ui.label('• Low Stock Alert Report - Items requiring immediate attention and restocking').classes('text-sm text-gray-600')
                        elif report == 'stock_movement_report.pdf':
                            ui.label('• Stock Movement Report - Daily stock inflow/outflow and movement trends read from table products').classes('text-sm text-gray-600')
                        elif report == 'category_inventory_report.pdf':
                            ui.label('• Category Inventory Report - Inventory breakdown by product categories').classes('text-sm text-gray-600')

def generate_stock_reports_and_refresh():
    """Generate all stock reports and refresh the page"""
    try:
        # Import and run the report generation
        import subprocess
        import sys

        # Run the report generation script
        result = subprocess.run([sys.executable, 'Reports/generate_all_reports.py'],
                              capture_output=True, text=True, cwd=os.getcwd())

        if result.returncode == 0:
            ui.notify('Stock reports generated successfully!', color='green')
            # Refresh the page to show new reports
            ui.run_javascript('window.location.reload()')
        else:
            ui.notify('Error generating stock reports. Check console for details.', color='red')
            print("Stock report generation error:", result.stderr)

    except Exception as e:
        ui.notify(f'Error: {str(e)}', color='red')
        print(f"Error in generate_stock_reports_and_refresh: {e}")

def view_selected_stock_report(report_name):
    """Generate and open the selected stock report (always with fresh data)"""
    if not report_name:
        ui.notify('Please select a stock report first', color='orange')
        return

    try:
        # Determine which report to generate based on the selected file
        if 'category_inventory_report' in report_name:
            # Always generate fresh Category Inventory Report
            ui.notify('Generating Category Inventory Report...', color='blue')
            from stockreports.category_inventory_report import CategoryInventoryReport

            # Generate to fixed filename
            report = CategoryInventoryReport()
            report_path = 'stockreports/category_inventory_report.pdf'
            report.generate_report(report_path)
            generated_filename = 'category_inventory_report.pdf'
            ui.notify('Category Inventory Report generated successfully!', color='green')

        elif 'low_stock_alert_report' in report_name:
            # Always generate fresh Low Stock Alert Report
            ui.notify('Generating Low Stock Alert Report...', color='blue')
            from stockreports.low_stock_alert_report import LowStockAlertReport

            # Generate to fixed filename
            report = LowStockAlertReport()
            report_path = 'stockreports/low_stock_alert_report.pdf'
            report.generate_report(report_path)
            generated_filename = 'low_stock_alert_report.pdf'
            ui.notify('Low Stock Alert Report generated successfully!', color='green')

        elif 'stock_movement_report' in report_name:
            # Always generate fresh Stock Movement Report
            ui.notify('Generating Stock Movement Report...', color='blue')
            from stockreports.stock_movement_report import StockMovementReport

            # Generate to fixed filename
            report = StockMovementReport()
            report_path = 'stockreports/stock_movement_report.pdf'
            report.generate_report(report_path)
            generated_filename = 'stock_movement_report.pdf'
            ui.notify('Stock Movement Report generated successfully!', color='green')

        elif 'inventory_report' in report_name:
            # Always generate fresh Inventory Report
            ui.notify('Generating Inventory Report...', color='blue')
            try:
                from Reports.inventory_report import InventoryReport

                # Generate to fixed filename
                report = InventoryReport()
                report_path = 'Reports/inventory_report.pdf'
                success = report.generate_report(report_path)

                if success:
                    generated_filename = 'inventory_report.pdf'
                    ui.notify('Inventory Report generated successfully!', color='green')
                else:
                    ui.notify('Error generating inventory report', color='red')
                    return
            except ImportError:
                ui.notify('Inventory report module not found', color='red')
                return

        else:
            ui.notify('Unknown report type selected', color='red')
            return

        # Now open the report
        if os.path.exists(report_path):
            import webbrowser
            full_path = os.path.abspath(report_path)

            # Try to open with default PDF viewer
            try:
                webbrowser.open(f'file://{full_path}')
                ui.notify(f'Opening {generated_filename}...', color='green')
            except Exception as e:
                # Fallback: show download link
                ui.notify('Could not open PDF automatically. File is available in stockreports folder.', color='orange')
                print(f"Could not open PDF: {e}")
        else:
            ui.notify('Report file not found', color='red')

    except Exception as e:
        ui.notify(f'Error generating/viewing stock report: {str(e)}', color='red')
        print(f"Error in view_selected_stock_report: {e}")

# Stock Reports folder route
@ui.page('/stock-reports-folder')
def stock_reports_folder_page():
    """Page to display stock reports folder contents"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    if not check_page_access('reports'):
        ui.notify('You do not have permission to access reports', color='red')
        ui.run_javascript('window.location.href = "/dashboard"')
        return

    # Get user permissions and create navigation
    permissions = connection.get_user_permissions(user['role_id'])
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_header()
    navigation.create_navigation_drawer()

    with ui.column().classes('p-6 w-full max-w-4xl mx-auto'):
        ui.label('Stock Reports Folder').classes('text-3xl font-bold mb-6 text-center')

        reports_dir = 'stockreports'

        if os.path.exists(reports_dir):
            ui.label(f'Contents of {reports_dir} folder:').classes('text-lg mb-4')

            # List all files in stockreports directory
            files = os.listdir(reports_dir)
            files.sort()  # Sort alphabetically

            with ui.grid(columns=1).classes('w-full gap-2'):
                for file in files:
                    file_path = os.path.join(reports_dir, file)

                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        file_size_mb = file_size / (1024 * 1024) if file_size > 1024*1024 else file_size / 1024
                        size_unit = 'MB' if file_size > 1024*1024 else 'KB'

                        with ui.card().classes('p-4 hover:shadow-md transition-shadow'):
                            with ui.row().classes('items-center justify-between w-full'):
                                with ui.row().classes('items-center'):
                                    # File icon based on extension
                                    if file.endswith('.pdf'):
                                        ui.label('📄').classes('text-2xl mr-3')
                                    elif file.endswith('.py'):
                                        ui.label('🐍').classes('text-2xl mr-3')
                                    else:
                                        ui.label('📁').classes('text-2xl mr-3')

                                    ui.label(file).classes('font-medium')

                                with ui.row().classes('items-center space-x-4'):
                                    ui.label(f'{file_size_mb:.1f} {size_unit}').classes('text-sm text-gray-500')

                                    if file.endswith('.pdf'):
                                        ui.button(
                                            'View',
                                            on_click=lambda f=file: view_selected_stock_report(f)
                                        ).classes('bg-blue-500 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm')
        else:
            ui.label('Stock reports folder does not exist.').classes('text-red-600')

# Sales Reports page
@ui.page('/sales-reports')
def sales_reports_page():
    """Sales Reports page with dropdown to select and view reports"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    # Check permissions
    if not check_page_access('reports'):
        ui.notify('You do not have permission to access reports', color='red')
        ui.run_javascript('window.location.href = "/dashboard"')
        return

    # Get user permissions and create navigation
    permissions = connection.get_user_permissions(user['role_id'])
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_header()
    navigation.create_navigation_drawer()

    with ui.column().classes('p-6 w-full max-w-4xl mx-auto'):
        ui.label('Sales Reports').classes('text-3xl font-bold mb-6 text-center')

        # Reports folder link
        with ui.row().classes('mb-6 items-center'):
            ui.label('Reports Folder:').classes('text-lg font-medium mr-4')
            ui.link('📁 Open Reports Folder', '/reports-folder', new_tab=True).classes('text-blue-600 hover:text-blue-800 underline')

        # Report selection section
        with ui.card().classes('p-6 w-full'):
            ui.label('View Reports').classes('text-xl font-semibold mb-4')

            # Get available PDF reports
            reports_dir = 'Reports'
            available_reports = []

            if os.path.exists(reports_dir):
                for file in os.listdir(reports_dir):
                    if file.endswith('.pdf'):
                        available_reports.append(file)

            if not available_reports:
                ui.label('No reports available. Please generate reports first.').classes('text-red-600')
                ui.button('Generate All Reports', on_click=lambda: generate_and_refresh()).classes('mt-4 bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded')
            else:
                # Report selection dropdown
                report_select = ui.select(
                    options=available_reports,
                    label='Select Report',
                    value=available_reports[0] if available_reports else None
                ).classes('w-full mb-4')

                # View Report button
                ui.button(
                    'View Report',
                    on_click=lambda: view_selected_report(report_select.value)
                ).classes('bg-green-500 hover:bg-green-700 text-white px-6 py-2 rounded font-medium')

                # Report descriptions
                with ui.column().classes('mt-6 space-y-2'):
                    ui.label('Available Reports:').classes('font-medium')
                    for report in available_reports:
                        if 'sales_performance' in report:
                            ui.label('• Sales Performance Report - Comprehensive sales analysis with trends and top products').classes('text-sm text-gray-600')
                        elif 'inventory' in report:
                            ui.label('• Inventory Report - Stock levels, low stock alerts, and turnover analysis').classes('text-sm text-gray-600')
                        elif 'financial' in report:
                            ui.label('• Financial Report - Revenue, expenses, and profit analysis').classes('text-sm text-gray-600')

def generate_and_refresh():
    """Generate all reports and refresh the page"""
    try:
        # Import and run the report generation
        import subprocess
        import sys

        # Run the report generation script
        result = subprocess.run([sys.executable, 'Reports/generate_all_reports.py'],
                              capture_output=True, text=True, cwd=os.getcwd())

        if result.returncode == 0:
            ui.notify('Reports generated successfully!', color='green')
            # Refresh the page to show new reports
            ui.run_javascript('window.location.reload()')
        else:
            ui.notify('Error generating reports. Check console for details.', color='red')
            print("Report generation error:", result.stderr)

    except Exception as e:
        ui.notify(f'Error: {str(e)}', color='red')
        print(f"Error in generate_and_refresh: {e}")

def view_selected_report(report_name):
    """Open the selected report in a new tab"""
    if not report_name:
        ui.notify('Please select a report first', color='orange')
        return

    try:
        # Create a route to serve the PDF file
        report_path = f'Reports/{report_name}'

        if os.path.exists(report_path):
            # For local development, we'll open the file directly
            # In production, you'd serve it through FastAPI
            import webbrowser
            full_path = os.path.abspath(report_path)

            # Try to open with default PDF viewer
            try:
                webbrowser.open(f'file://{full_path}')
                ui.notify(f'Opening {report_name}...', color='green')
            except Exception as e:
                # Fallback: show download link
                ui.notify('Could not open PDF automatically. File is available in Reports folder.', color='orange')
                print(f"Could not open PDF: {e}")
        else:
            ui.notify('Report file not found', color='red')

    except Exception as e:
        ui.notify(f'Error opening report: {str(e)}', color='red')
        print(f"Error in view_selected_report: {e}")

# Reports folder route
@ui.page('/reports-folder')
def reports_folder_page():
    """Page to display reports folder contents"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    if not check_page_access('reports'):
        ui.notify('You do not have permission to access reports', color='red')
        ui.run_javascript('window.location.href = "/dashboard"')
        return

    # Get user permissions and create navigation
    permissions = connection.get_user_permissions(user['role_id'])
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_header()
    navigation.create_navigation_drawer()

    with ui.column().classes('p-6 w-full max-w-4xl mx-auto'):
        ui.label('Reports Folder').classes('text-3xl font-bold mb-6 text-center')

        reports_dir = 'Reports'

        if os.path.exists(reports_dir):
            ui.label(f'Contents of {reports_dir} folder:').classes('text-lg mb-4')

            # List all files in Reports directory
            files = os.listdir(reports_dir)
            files.sort()  # Sort alphabetically

            with ui.grid(columns=1).classes('w-full gap-2'):
                for file in files:
                    file_path = os.path.join(reports_dir, file)

                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        file_size_mb = file_size / (1024 * 1024) if file_size > 1024*1024 else file_size / 1024
                        size_unit = 'MB' if file_size > 1024*1024 else 'KB'

                        with ui.card().classes('p-4 hover:shadow-md transition-shadow'):
                            with ui.row().classes('items-center justify-between w-full'):
                                with ui.row().classes('items-center'):
                                    # File icon based on extension
                                    if file.endswith('.pdf'):
                                        ui.label('📄').classes('text-2xl mr-3')
                                    elif file.endswith('.py'):
                                        ui.label('🐍').classes('text-2xl mr-3')
                                    else:
                                        ui.label('📁').classes('text-2xl mr-3')

                                    ui.label(file).classes('font-medium')

                                with ui.row().classes('items-center space-x-4'):
                                    ui.label(f'{file_size_mb:.1f} {size_unit}').classes('text-sm text-gray-500')

                                    if file.endswith('.pdf'):
                                        ui.button(
                                            'View',
                                            on_click=lambda f=file: view_selected_report(f)
                                        ).classes('bg-blue-500 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm')
        else:
            ui.label('Reports folder does not exist.').classes('text-red-600')

# Permission guard function
def check_page_access(page_name):
    """Check if current user has access to a specific page"""
    user = session_storage.get('user')
    if not user:
        return False
    return connection.check_page_permission(user['role_id'], page_name)

def require_login():
    """Check if user is logged in"""
    return session_storage.get('user') is not None

def get_current_user():
    """Get current logged-in user info"""
    return session_storage.get('user')

# Signup functionality using AuthService
def signup_user(username, password):
    success, message = AuthService.create_user(username, password, role_id=2)  # Default to regular user role
    if success:
        ui.notify(message, color='green')
        app_logger.log_security_event('USER_SIGNUP_SUCCESS', details={'username': username})
    else:
        ui.notify(message, color='red')
        app_logger.log_security_event('USER_SIGNUP_FAILED', details={'username': username, 'reason': message})

@ui.page('/')
def home_page():
    """Home page that redirects to login"""
    ui.run_javascript('window.location.href = "/login";')

@ui.page('/login')
def login_page_route():
    """Dedicated login page using modern split-screen layout"""
    # Check if user is already logged in
    from session_storage import session_storage
    if session_storage.get('user'):
        ui.run_javascript('window.location.href = "/dashboard";')
        return

    from login_page import login_page as modern_login_page
    modern_login_page()

@ui.page('/signup')
def signup_page_route():
    """Dedicated signup page with premium design"""
    from signup_page import signup_page as modern_signup_page
    modern_signup_page()

@ui.page('/logout')
def logout_page():
    """Dedicated logout page"""
    try:
        # Handle logout using AuthService
        user = session_storage.get('user')
        session_id = session_storage.get('session_id')

        if session_id:
            success = AuthService.logout_user(session_id, user)
            if success:
                app_logger.log_user_action(
                    user['user_id'] if user else None,
                    'LOGOUT_SUCCESS',
                    {'session_id': session_id}
                )
            else:
                app_logger.log_error(
                    Exception("Failed to logout user"),
                    "logout_page"
                )

        # Clear session storage
        session_storage.pop('user', None)
        session_storage.pop('session_id', None)

        with ui.card().classes('w-96 mx-auto my-16 p-8 shadow-lg rounded-lg'):
            ui.label('Logged Out Successfully').classes('text-2xl font-bold text-center mb-6 text-green-600')
            ui.label('Thank you for using the system.').classes('text-center mb-4')

            ui.button('Login Again', on_click=lambda: ui.run_javascript('window.location.href = "/login";')).classes(
                'w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded'
            )

    except Exception as e:
        app_logger.log_error(e, "logout_page")
        ui.notify('An error occurred during logout. Please try again.', color='red')

@handle_errors
def handle_login(username, password):
    """Handle user login using AuthService"""
    try:
        # Use AuthService for authentication
        success, user_data = AuthService.authenticate_user(username, password)

        if success and user_data:
            # Store user info in session storage
            session_storage['user'] = user_data

            # Create user session entry using AuthService
            session_id = AuthService.create_user_session(user_data)
            if session_id:
                session_storage['session_id'] = session_id

            ui.notify(f'Login successful. Welcome {username}!', color='green')
            # Redirect to the modern sales page as landing page
            ui.run_javascript('window.location.href = "/modern-sales";')
        else:
            ui.notify('Invalid username or password, or user not approved', color='red')

    except Exception as e:
        app_logger.log_error(e, "handle_login")
        ui.notify('An error occurred during login. Please try again.', color='red')

@handle_errors
def handle_signup(username, email, password, confirm_password):
    """Handle user signup using AuthService"""
    try:
        if not username or not password:
            ui.notify('Username and password are required', color='red')
            return

        if password != confirm_password:
            ui.notify('Passwords do not match', color='red')
            return

        # Use AuthService for user creation
        success, message = AuthService.create_user(username, password, email=email, role_id=2)

        if success:
            ui.notify(message, color='green')
            app_logger.log_security_event('USER_SIGNUP_SUCCESS', details={'username': username})
            # Redirect to login page
            ui.run_javascript('window.location.href = "/login";')
        else:
            ui.notify(message, color='red')
            app_logger.log_security_event('USER_SIGNUP_FAILED', details={'username': username, 'reason': message})

    except Exception as e:
        app_logger.log_error(e, "handle_signup")
        ui.notify('An error occurred during signup. Please try again.', color='red')

@ui.page('/dashboard')
def dashboard_page():
    """Dashboard now redirects to modern-sales as the main landing page"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return
    
    # Redirect to modern-sales as the new landing page
    ui.run_javascript('window.location.href = "/modern-sales";')
    return

    # Get user permissions
    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    # Create enhanced navigation instance
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_header()
    navigation.create_navigation_drawer()

    # Main content area with tabs
    with ui.tabs().classes('w-full') as tabs:
        dashboard_tab = ui.tab('Dashboard')
        timespend_tab = ui.tab('Time Spend Analysis')

    with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full'):
        with ui.tab_panel(dashboard_tab):
            with ui.column().classes('p-4 w-full'):
                ui.label('Welcome to the Dashboard').classes('text-3xl font-light mb-6 text-center')

                # The icon map from your original app, redesigned as a responsive grid
                icon_map = {
                    'Employee': ('/employees', 'images/employee.png'),
                    'Products': ('/products', 'images/products.png'),
                    'Purchase': ('/purchase', 'images/purchase.png'),
                    'Stock Operations': ('/stockoperations', 'images/products.png'),
                    'Reports': ('/reports', 'images/reports.png'),
                    'Sales Reports': ('/sales-reports', 'images/reports.png'),
                    'Stock Reports': ('/stock-reports', 'images/reports.png'),
                    'Sales': ('/sales', 'images/sales.png'),
                    'Supplier': ('/suppliers', 'images/supplier.png'),
                    'Supplier Payment': ('/supplierpayment', 'images/supplierpayment.png'),
                    'Category': ('/category', 'images/category.png'),
                    'Consignment': ('/consignment', 'images/consignment.png'),
                    'Customers': ('/customers', 'images/customer.png'),
                    'Customer Receipt': ('/customerreceipt', 'images/customerrecipt.png'),
                    'Expenses': ('/expenses', 'images/expenses.png'),
                    'Expense Types': ('/expensestype', 'images/expenses.png'),
                    'Accounting & Finance': ('/accounting', 'images/accounting.png'),
                    'Company': ('/company', 'images/company.png'),
                    'Login': ('/login', 'images/login.png'),
                    'Exit': ('/logout', 'images/exit.png'),
                    'Currencies': ('/currencies', 'images/expenses.png'),
                    'Cash Drawer': ('/cash-drawer', 'images/expenses.png'),
                    'Services': ('/services', 'images/services.png'),
                    'Ledger': ('/ledger', 'images/accounting.png'),
                }

                # Function to handle navigation: open in new tab except for Login and Exit
                def navigate_or_open(label, path):
                    if label in ['Login', 'Exit']:
                        ui.navigate.to(path)
                    else:
                        ui.run_javascript(f'window.open("{path}", "_blank")')

                # Create a responsive grid of cards with inline images and text
                with ui.grid(columns=4).classes('w-full gap-4'):
                    for label, (path, icon_path) in icon_map.items():
                        # Show only if user has permission for the page (except Login and Exit)
                        page_key = path.lstrip('/').lower()
                        if page_key in allowed_pages or page_key in ['login', 'logout']:
                            with ui.card().classes('items-center cursor-pointer hover:shadow-xl transition-shadow p-4').on('click', lambda l=label, p=path: navigate_or_open(l, p)):
                                with ui.row().classes('items-center'):
                                    ui.image(icon_path).classes('w-8 h-8 object-contain')
                                    ui.label(label).classes('ml-2 text-gray-600 font-medium text-sm')

        with ui.tab_panel(timespend_tab):
            # Check if user has permission to access timespend
            if 'timespend' in allowed_pages:
                # Import and display the TimeSpendUI
                from timespendui import TimeSpendUI
                TimeSpendUI(show_header=False)
            else:
                with ui.column().classes('p-4 w-full items-center justify-center'):
                    ui.label('Access Denied').classes('text-2xl font-bold text-red-600 mb-4')
                    ui.label('You do not have permission to access Time Spend Analysis.').classes('text-lg text-gray-600')
                    ui.button('Back to Dashboard', on_click=lambda: tabs.set_value(dashboard_tab)).classes('mt-4')


    # Footer with system time, company name, and username
    with ui.footer().classes('flex justify-between items-center p-4 bg-gray-100 text-sm text-gray-600'):
        # System time
        def update_time():
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            time_label.set_text(f'System Time: {now}')
        time_label = ui.label()
        update_time()
        ui.timer(1.0, update_time)

        # Company name from database
        company_info = connection.get_company_info()
        company_name = company_info.get('company_name') if company_info else 'Company Name'
        ui.label(f'Company: {company_name}')

        # Username
        username = user.get('username') if user else 'Guest'
        ui.label(f'User: {username}')

# Category page with grid, search and filtering

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Add Jinja template route
@ui.page('/sample-template')
def sample_template_page():
    """Sample page demonstrating Jinja template rendering"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    # Sample data for template
    template_data = {
        'title': 'Management System Report',
        'user': {
            'username': user.get('username', 'Guest'),
            'role': user.get('role_name', 'User'),
            'last_login': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'items': [
            {'name': 'Product A', 'description': 'High-quality product', 'price': 29.99},
            {'name': 'Product B', 'description': 'Premium service', 'price': 49.99},
            {'name': 'Product C', 'description': 'Basic package', 'price': 19.99}
        ],
        'current_date': datetime.datetime.now().strftime('%B %d, %Y')
    }

    # Render template and display as HTML
    html_content = templates.TemplateResponse("sample_page.html", {"request": None, **template_data}).body.decode('utf-8')
    ui.html(html_content)

if __name__ in {"__main__", "__mp_main__"}:
    # Create users table on app startup
    connection.create_users_table()
    # Create roles and permissions tables
    connection.create_roles_tables()
    # Create default admin user
    connection.create_default_admin_user()
    # Create user_sessions table (only if it doesn't exist)
    # try:
    #     from create_user_sessions_table_fixed import create_user_sessions_table
    #     create_user_sessions_table()
    # except Exception as e:
    #     if "already an object named 'user_sessions'" in str(e):
    #         # Table already exists, skip creation
    #         pass
    #     else:
    #         print(f"Error creating user_sessions table: {str(e)}")

    # Create cash drawer tables (only if they don't exist)
    # try:
    #     from create_cash_drawer_tables_sqlserver import create_cash_drawer_tables_sqlserver
    #     create_cash_drawer_tables_sqlserver()
    # except Exception as e:
    #     print(f"Error creating cash drawer tables: {str(e)}")

    # Create currencies table (only if it doesn't exist)
    # try:
    #     from create_currencies_table import create_currencies_table
    #     create_currencies_table()
    # except Exception as e:
    #     print(f"Error creating currencies table: {str(e)}")

  
   

    # Ensure services permission for all roles
    try:
        connection.ensure_services_permission()
    except Exception as e:
        print(f"Error ensuring services permission: {str(e)}")

    # Ensure ledger permission for all roles
    try:
        connection.ensure_ledger_permission()
        connection.ensure_auxiliary_permission()
    except Exception as e:
        print(f"Error ensuring ledger permission or auxiliary permission: {str(e)}")

    # The following page routes are already registered via @ui.page decorators
    # and do not need to be called manually.
    
    # You can add authentication logic here before opening the dashboard
    # For now, we'll just run the app
    ui.run()
