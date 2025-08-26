from nicegui import ui, app
from connection import connection
import hashlib
# Import the category page
from category import category_page_route
from customerui import customer_page_route
from productui import product_page_route
from supplierui import supplier_page_route
from salesui_aggrid_compact import sales_page_route
from purchaseui import purchase_page_route
from employeeui import employee_page_route
from supplier_payment_ui_fixed_v2 import supplier_payment_page_route
# Signup functionality
def signup_user(username, password):
    # Create MD5 hash of the password
    password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
    
    sql = "INSERT INTO users (username, password) VALUES (?, ?)"
    values = (username, password_hash)
    
    try:
        connection.insertingtodatabase(sql, values)
        ui.notify('User created successfully', color='green')
    except Exception as e:
        ui.notify(f'Error creating user: {str(e)}', color='red')

@ui.page('/')
def login_signup_page():
    # Store input references
    username_login_ref = {}
    password_login_ref = {}
    
    username_signup_ref = {}
    email_signup_ref = {}  # Keep email field as in original
    password_signup_ref = {}
    confirm_password_signup_ref = {}
    
    with ui.card().classes('w-96 mx-auto my-16 p-8 shadow-lg rounded-lg'):
        ui.label('Welcome!').classes('text-3xl font-bold text-center mb-6')

        with ui.tabs().classes('w-full') as tabs:
            ui.tab('Login', icon='login')
            ui.tab('Sign Up', icon='person_add')
        with ui.tab_panels(tabs, value='Login').classes('w-full'):
            with ui.tab_panel('Login'):
                with ui.column().classes('w-full items-center'):
                    username_login = ui.input('Username').classes('w-full mb-4')
                    password_login = ui.input('Password', password=True).classes('w-full mb-6')
                    # Store references
                    username_login_ref['input'] = username_login
                    password_login_ref['input'] = password_login
                    ui.button('Login', on_click=lambda: handle_login(
                        username_login_ref['input'].value,
                        password_login_ref['input'].value
                    )).classes('w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
                    ui.label('Forgot password?').classes('text-sm text-blue-500 cursor-pointer mt-2')

            with ui.tab_panel('Sign Up'):
                with ui.column().classes('w-full items-center'):
                    username_signup = ui.input('Username').classes('w-full mb-4')
                    email_signup = ui.input('Email').classes('w-full mb-4')  # Keep email field
                    password_signup = ui.input('Password', password=True).classes('w-full mb-4')
                    confirm_password_signup = ui.input('Confirm Password', password=True).classes('w-full mb-6')
                    # Store references
                    username_signup_ref['input'] = username_signup
                    email_signup_ref['input'] = email_signup
                    password_signup_ref['input'] = password_signup
                    confirm_password_signup_ref['input'] = confirm_password_signup
                    ui.button('Sign Up', on_click=lambda: handle_signup(
                        username_signup_ref['input'].value,
                        email_signup_ref['input'].value,
                        password_signup_ref['input'].value,
                        confirm_password_signup_ref['input'].value
                    )).classes('w-full bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded')

def handle_login(username, password):
    if not username or not password:
        ui.notify('Username and password are required', color='red')
        return
        
    # Create MD5 hash of the input password
    password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
    
    # Check if user is registered and approved
    user_info = connection.check_user_login(username, password_hash)
    
    if user_info:
        ui.notify(f'Login successful. Welcome {username}!', color='green')
        # Redirect to the main application
        # Since we're in a separate app, we'll redirect to the main app's URL
        ui.run_javascript('window.location.href = "/dashboard";')
    else:
        ui.notify('Invalid username or password, or user not approved', color='red')

def handle_signup(username, email, password, confirm_password):
    if not username or not password:
        ui.notify('Username and password are required', color='red')
        return
        
    if password != confirm_password:
        ui.notify('Passwords do not match', color='red')
        return
        
    signup_user(username, password)

@ui.page('/dashboard')
def dashboard_page():
    with ui.header().classes('items-center justify-between'):
        ui.label('Dashboard').classes('text-2xl font-bold')
        ui.button('Logout', on_click=lambda: ui.navigate.to('/')).props('flat icon=logout')

    with ui.left_drawer().classes('bg-blue-100'):
        ui.label('Navigation').classes('text-lg font-semibold mb-4')
        ui.link('Home', '/dashboard').classes('block py-2 px-4 hover:bg-blue-200 rounded')
        ui.link('Profile', '/dashboard/profile').classes('block py-2 px-4 hover:bg-blue-200 rounded')
        ui.link('Settings', '/dashboard/settings').classes('block py-2 px-4 hover:bg-blue-200 rounded')

    # Main content area with responsive grid layout
    with ui.column().classes('p-4 w-full'):
        ui.label('Welcome to the Dashboard').classes('text-3xl font-light mb-6 text-center')
        
        # The icon map from your original app, redesigned as a responsive grid
        icon_map = {
            
            'Employee': ('/employees', 'images/employee.png'),
            'Products': ('/products', 'images/products.png'),
            'Purchase': ('/purchase', 'images/purchase.png'),
            'Reports': ('/reports', 'images/reports.png'),
            'Sales': ('/sales', 'images/sales.png'),
            'Supplier': ('/suppliers', 'images/supplier.png'),
            'Supplier Payment': ('/supplierpayment', 'images/supplierpayment.png'), 
            'Category': ('/category', 'images/category.png'),
            'Consignment': ('/consignment', 'images/consignment.png'),
            'Customers': ('/customers', 'images/customer.png'),
            'Customer Receipt': ('/customerrecipt', 'images/customerrecipt.png'),
            'Expenses': ('/expenses', 'images/expenses.png'),
            'Login': ('/login', 'images/login.png'),
            'Exit': ('/exit', 'images/exit.png'),
        }
    
        # Create a responsive grid of cards with inline images and text
        with ui.grid(columns=4).classes('w-full gap-4'):
            for label, (path, icon_path) in icon_map.items():
                with ui.card().classes('items-center cursor-pointer hover:shadow-xl transition-shadow p-4').on('click', lambda p=path: ui.navigate.to(p)):
                    with ui.row().classes('items-center'):
                        ui.image(icon_path).classes('w-8 h-8 object-contain')
                        ui.label(label).classes('ml-2 text-gray-600 font-medium text-sm')

# Category page with grid, search and filtering

if __name__ in {"__main__", "__mp_main__"}:
    # Create users table on app startup
    connection.create_users_table()
    # You can add authentication logic here before opening the dashboard
    # For now, we'll just run the app
    ui.run()
