from nicegui import ui
from connection import connection
import hashlib

class LoginPage:
    def __init__(self):
        self.username_input = None
        self.password_input = None

    def build_ui(self):
        with ui.column().style('width: 300px; margin: auto; padding-top: 50px;'):
            ui.label('Login').style('font-weight: bold; font-size: 24px; margin-bottom: 20px;')
            self.username_input = ui.input(label='Username')
            self.password_input = ui.input(label='Password', password=True)
            ui.button('Login', on_click=self.login)

    def login(self):
        username = self.username_input.value.strip()
        password = self.password_input.value.strip()

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

def login_page():
    page = LoginPage()
    page.build_ui()
    return page
