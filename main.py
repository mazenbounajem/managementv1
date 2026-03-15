from nicegui import ui

# This file acts as the main entry point for your application.
# It imports all the different pages you've created. When a module
# containing a @ui.page decorator is imported, NiceGUI automatically
# registers the route.

print("🚀 Starting ManagementV1 Application...")

try:
    # Assuming you have updated dashboard.py to use NiceGUI as suggested
    from modern_ribbon_navigation import ModernRibbonNavigation
    print("✅ Imported: Dashboard")
except ImportError:
    print("⚠️ Warning: Could not import 'dashboard_page'. The '/dashboard' route may not be available.")

try:
    from salesui_aggrid_compact_redesigned import sales_page_route
    print("✅ Imported: Sales UI")
except ImportError:
    print("⚠️ Warning: Could not import 'sales_page_route'. The '/sales' route may not be available.")

try:
    from purchaseui import purchase_page_route
    print("✅ Imported: Purchase UI")
except ImportError:
    print("⚠️ Warning: Could not import 'purchase_page_route'. The '/purchase' route may not be available.")

try:
    from productui_final import product_page
    print("✅ Imported: Product UI")
except ImportError:
    print("⚠️ Warning: Could not import 'product_page'. The '/products' route may not be available.")

try:
    from supplierui import supplier_page
    print("✅ Imported: Supplier UI")
except ImportError:
    print("⚠️ Warning: Could not import 'supplier_page'. The '/suppliers' route may not be available.")

try:
    from reports_ui import reports_page_route
    print("✅ Imported: Reports UI")
except ImportError:
    print("⚠️ Warning: Could not import 'reports_page_route'. The '/reports' route may not be available.")

# You can add imports for your other UI files here following the same pattern.
# For example:
# from roles import roles_page
# from services_ui import services_page_route
# from statisticalreports import statistical_reports_page
# from supplier_payment_ui_fixed_v2 import supplier_payment_page_route


# This defines the default page when you visit the root URL (e.g., http://localhost:8080)
# It will immediately redirect the user to the dashboard.
@ui.page('/')
def index():
    """Main landing page."""
    ui.navigate.to('/dashboard')

# This command starts the web server.
ui.run()

