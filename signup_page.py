from nicegui import ui
from connection import connection
import hashlib

class SignupPage:
    def __init__(self):
        self.username_input = None
        self.password_input = None

    def build_ui(self):
        with ui.column().style('width: 300px; margin: auto; padding-top: 50px;'):
            ui.label('Sign Up').style('font-weight: bold; font-size: 24px; margin-bottom: 20px;')
            self.username_input = ui.input(label='Username')
            self.password_input = ui.input(label='Password', password=True)
            ui.button('Sign Up', on_click=self.signup)

    def signup(self):
        username = self.username_input.value.strip()
        password = self.password_input.value.strip()

        if not username or not password:
            ui.notify('Username and password are required', color='red')
            return

        # Create MD5 hash of the password
        password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()

        sql = "INSERT INTO users (username, password) VALUES (?, ?)"
        values = (username, password_hash)

        try:
            connection.insertingtodatabase(sql, values)
            ui.notify('User registered successfully', color='green')
            self.username_input.value = ''
            self.password_input.value = ''
        except Exception as e:
            ui.notify(f'Error registering user: {str(e)}', color='red')

def signup_page():
    page = SignupPage()
    page.build_ui()
    return page
