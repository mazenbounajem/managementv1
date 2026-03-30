from stockoperationui import stock_operations_page as ui_func
from session_storage import session_storage

def stock_operations_page():
    """Content method for stock operations that can be used in tabs"""
    user = session_storage.get('user')
    if not user:
        return
    # Call the UI function with standalone=False to avoid nested layouts
    ui_func(standalone=False)