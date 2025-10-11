from nicegui import ui
from connection import connection
import datetime

# Import content methods
from category_content_method import category_content
from sales_content_method import sales_content
from customer_content_method import customer_content
from product_content_method import product_content
from supplier_content_method import supplier_content
from purchase_content_method import purchase_content
from employee_content_method import employee_content
from database_content_method import database_content

# Import existing modules for authentication
from config import config
from logger import app_logger, handle_errors
from auth_service import AuthService
from navigation_improvements import EnhancedNavigation

# Add session storage for logged-in user
session_storage = {}

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

@ui.page('/tabbed-dashboard')
def tabbed_dashboard_page():
    """Tabbed dashboard with all modules in tabs"""
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access the dashboard', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    # Get user permissions
    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    # Create enhanced navigation instance
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_drawer()  # Create drawer first
    navigation.create_navigation_header()  # Then create header with toggle button

    # Define available tabs based on permissions
    tab_definitions = [
        ('Dashboard', 'dashboard', lambda: create_dashboard_content()),
        ('Sales', 'sales', sales_content),
        ('Purchase', 'purchase', purchase_content),
        ('Products', 'products', product_content),
        ('Customers', 'customers', customer_content),
        ('Suppliers', 'suppliers', supplier_content),
        ('Categories', 'category', category_content),
        ('Employees', 'employees', employee_content),
        ('Backup', 'backup', database_content),
    ]

    # Filter tabs based on permissions
    available_tabs = []
    tab_objects = []

    for tab_name, page_key, content_func in tab_definitions:
        if page_key in allowed_pages or page_key == 'dashboard':
            tab_obj = ui.tab(tab_name)
            tab_objects.append((tab_obj, content_func))
            available_tabs.append(tab_name)

    # Create tab panels
    global current_tab_panels, global_tab_objects
    current_tab_panels = ui.tab_panels(tab_objects[0][0] if tab_objects else None, value=tab_objects[0][0] if tab_objects else None).classes('w-full flex-1')
    global_tab_objects = tab_objects

    for tab_obj, content_func in tab_objects:
        with ui.tab_panel(tab_obj):
            try:
                # Call the content function
                content_func()
            except Exception as e:
                ui.notify(f'Error loading {tab_obj._text}: {str(e)}', color='red')
                with ui.column().classes('p-4 w-full items-center justify-center'):
                    ui.label(f'Error loading {tab_obj._text}').classes('text-xl font-bold text-red-600 mb-4')
                    ui.label('Please try refreshing the page.').classes('text-lg text-gray-600')

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

def create_dashboard_content():
    """Create the dashboard content with overview cards"""
    with ui.column().classes('p-4 w-full'):
        ui.label('Welcome to the Dashboard').classes('text-3xl font-light mb-6 text-center')

        # Quick stats cards
        with ui.grid(columns=4).classes('w-full gap-4 mb-6'):
            # Sales today
            with ui.card().classes('p-4'):
                ui.label('Today\'s Sales').classes('text-lg font-semibold mb-2')
                sales_today = connection.get_today_sales()
                ui.label(f'${sales_today:.2f}').classes('text-2xl font-bold text-green-600')

            # Total products
            with ui.card().classes('p-4'):
                ui.label('Total Products').classes('text-lg font-semibold mb-2')
                total_products = connection.get_total_products()
                ui.label(str(total_products)).classes('text-2xl font-bold text-blue-600')

            # Total customers
            with ui.card().classes('p-4'):
                ui.label('Total Customers').classes('text-lg font-semibold mb-2')
                total_customers = connection.get_total_customers()
                ui.label(str(total_customers)).classes('text-2xl font-bold text-purple-600')

            # Low stock items
            with ui.card().classes('p-4'):
                ui.label('Low Stock Items').classes('text-lg font-semibold mb-2')
                low_stock = connection.get_low_stock_count()
                ui.label(str(low_stock)).classes('text-2xl font-bold text-red-600')

        # Quick action buttons
        ui.label('Quick Actions').classes('text-xl font-semibold mb-4')

        with ui.grid(columns=3).classes('w-full gap-4'):
            ui.button('New Sale', icon='add_shopping_cart').classes('p-4 bg-green-500 text-white')
            ui.button('Add Product', icon='add_box').classes('p-4 bg-blue-500 text-white')
            ui.button('View Reports', icon='analytics').classes('p-4 bg-purple-500 text-white')

# Keep the existing authentication pages
@ui.page('/')
def home_page():
    """Home page that redirects to login"""
    ui.run_javascript('window.location.href = "/login";')

@ui.page('/login')
def login_page():
    """Dedicated login page"""
    # Check if user is already logged in
    if session_storage.get('user'):
        ui.run_javascript('window.location.href = "/tabbed-dashboard";')
        return

    with ui.card().classes('w-96 mx-auto my-16 p-8 shadow-lg rounded-lg'):
        ui.label('Login').classes('text-3xl font-bold text-center mb-6')

        with ui.column().classes('w-full items-center'):
            username_input = ui.input('Username').classes('w-full mb-4')
            password_input = ui.input('Password', password=True).classes('w-full mb-6')

            ui.button('Login', on_click=lambda: handle_login(
                username_input.value,
                password_input.value
            )).classes('w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')

            ui.link('Sign Up', '/signup').classes('text-sm text-blue-500 cursor-pointer mt-2')

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
            # Redirect to the tabbed dashboard
            ui.run_javascript('window.location.href = "/tabbed-dashboard";')
        else:
            ui.notify('Invalid username or password, or user not approved', color='red')

    except Exception as e:
        app_logger.log_error(e, "handle_login")
        ui.notify('An error occurred during login. Please try again.', color='red')

# Include other necessary pages (signup, logout, etc.)
@ui.page('/signup')
def signup_page():
    """Dedicated signup page"""
    with ui.card().classes('w-96 mx-auto my-16 p-8 shadow-lg rounded-lg'):
        ui.label('Sign Up').classes('text-3xl font-bold text-center mb-6')

        with ui.column().classes('w-full items-center'):
            username_input = ui.input('Username').classes('w-full mb-4')
            email_input = ui.input('Email').classes('w-full mb-4')
            password_input = ui.input('Password', password=True).classes('w-full mb-4')
            confirm_password_input = ui.input('Confirm Password', password=True).classes('w-full mb-6')

            ui.button('Sign Up', on_click=lambda: handle_signup(
                username_input.value,
                email_input.value,
                password_input.value,
                confirm_password_input.value
            )).classes('w-full bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded')

            ui.link('Already have an account? Login', '/login').classes('text-sm text-blue-500 cursor-pointer mt-2')

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

# Global variables to store tab panels and tab objects
current_tab_panels = None
global_tab_objects = []

def switch_to_tab(tab_name):
    """Switch to a specific tab by name"""
    global current_tab_panels, global_tab_objects
    if current_tab_panels and global_tab_objects:
        # Find the tab object with the matching name
        for tab_obj, _ in global_tab_objects:
            if tab_obj._text == tab_name:
                current_tab_panels.value = tab_obj
                break

# Export the session storage for use in other modules
__all__ = ['session_storage', 'check_page_access', 'require_login', 'get_current_user', 'switch_to_tab']
