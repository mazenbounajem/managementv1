from purchaseui import PurchaseUI

def purchase_content():
    """Content method for purchase management that can be used in tabs"""
    purchase_ui = PurchaseUI(show_navigation=False)
    # The PurchaseUI class creates its own header, so we don't need to add one
    return purchase_ui
