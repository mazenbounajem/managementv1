from salesui_aggrid_compact import SalesUI

def sales_content():
    """Content method for sales management that can be used in tabs"""
    sales_ui = SalesUI()
    # The SalesUI class creates its own header, so we don't need to add one
    return sales_ui
