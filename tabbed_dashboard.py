from nicegui import ui
import accounting_finance
import appointments_ui
import cashdrawer_ui
from connection import connection
import datetime

# Import content methods
from category_content_method import category_content_method
import currencies
import customer_receipt_ui_fixed_v2
import journal_voucher_ui
import ledgerui
import reports_ui
import roles
from sales_content_method import sales_content
from customer_content_method import customer_content
from product_content_method import product_content
import services_ui
import stockopeartionuimethod
import stockoperationui
from supplier_content_method import supplier_content
from purchase_content_method import purchase_content
from employee_content_method import employee_content
from database_content_method import database_content
import supplier_payment_ui_fixed_v2
from timespendui import TimeSpendUI
import sys
from ledgerui import ledger_content
from auxiliaryui import auxiliary_content
import voucher_subtype_ui
import accounting_transactions_ui

# Global registries for tab management
current_open_tab = None
tab_refresh_callbacks = {}
tab_dirty_callbacks = {}


# Import existing modules for authentication
from config import config
from logger import app_logger, handle_errors
from auth_service import AuthService
from navigation_improvements import EnhancedNavigation

# Add session storage for logged-in user
from session_storage import session_storage

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

    # Add global styles
    from modern_design_system import ModernDesignSystem as MDS
    ui.add_head_html(MDS.get_global_styles())

    # Get user permissions
    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    # Create enhanced navigation instance
    navigation = EnhancedNavigation(permissions, user)
    navigation.tabbed_mode = True
    navigation.create_navigation_header()
    navigation.create_navigation_drawer()

    # Map of page keys to their content functions and labels
    def make_iframe(path):
        """Generic loader: embed the page in a full-height iframe inside the tab."""
        def _loader():
            ui.html(
                f'<iframe src="{path}" style="width:100%;height:calc(100vh - 130px);border:none;display:block;"></iframe>'
            )
        return _loader

   # In tabbed_dashboard.py, update the content_map entries:

   # Update the content_map:
    content_map = {
    'dashboard':        {'label': 'Dashboard',        'func': create_dashboard_content,   'icon': 'dashboard'},
    'sales':            {'label': 'Sales',             'func': sales_content,               'icon': 'point_of_sale'},
    'purchase':         {'label': 'Purchase',          'func': purchase_content,            'icon': 'shopping_bag'},
    'modern-purchase':  {'label': 'Modern Purchase',   'func': make_iframe('/modern-purchase'), 'icon': 'shopping_cart'},
    'products':         {'label': 'Products',          'func': product_content,             'icon': 'inventory'},
    'customers':        {'label': 'Customers',         'func': customer_content,            'icon': 'person'},
    'suppliers':        {'label': 'Suppliers',         'func': supplier_content,            'icon': 'business'},
    'timespend':        {'label': 'Time Analysis',     'func': lambda: TimeSpendUI(show_header=False), 'icon': 'schedule'},
    'category':         {'label': 'Categories',        'func': category_content_method,     'icon': 'category'},
    'employees':        {'label': 'Employees',         'func': employee_content,            'icon': 'badge'},
    'backup':           {'label': 'Backup',            'func': database_content,            'icon': 'backup'},
    'stockoperations':  {'label': 'Stock Operations',  'func': stockoperationui.stock_operations_page, 'icon': 'inventory_2'},
    'supplierpayment':  {'label': 'Supplier Payment',  'func': supplier_payment_ui_fixed_v2.supplier_payment_page, 'icon': 'payment'},
    'expenses':         {'label': 'Expenses',          'func': lambda: __import__('expenses').expenses_content(standalone=False), 'icon': 'money_off'},
    'expensestype':     {'label': 'Expense Types',     'func': lambda: __import__('expensestype').expensestype_content(standalone=False), 'icon': 'category'},
    'currencies':       {'label': 'Currencies',        'func': lambda: currencies.currencies_content(standalone=False), 'icon': 'currency_exchange'},
    'accounting':       {'label': 'Accounting',        'func': lambda: accounting_finance.accounting_finance_content(standalone=False), 'icon': 'account_balance'},
    'cash-drawer':      {'label': 'Cash Drawer',       'func': lambda: cashdrawer_ui.cash_drawer_content(standalone=False), 'icon': 'account_balance_wallet'},
    'ledger':           {'label': 'Ledger',            'func': lambda: ledgerui.ledger_content(standalone=False), 'icon': 'account_balance'},
    'auxiliary':        {'label': 'Auxiliary',         'func': lambda: auxiliary_content(standalone=False), 'icon': 'account_balance'},
    'journal_voucher':  {'label': 'Journal Voucher',   'func': lambda: journal_voucher_ui.journal_voucher_content(standalone=False), 'icon': 'receipt_long'},
    'voucher_subtype':  {'label': 'Voucher Subtype',   'func': lambda: voucher_subtype_ui.voucher_subtype_content(standalone=False), 'icon': 'category'},
    'customerreceipt':  {'label': 'Customer Receipt',  'func': lambda: customer_receipt_ui_fixed_v2.customer_receipt_page(standalone=False), 'icon': 'receipt'},
    'reports':          {'label': 'Reports',           'func': lambda: reports_ui.reports_content(standalone=False), 'icon': 'analytics'},
'modern-reports': {'label': 'Accounting Reports', 'func': lambda: ui.open('/modern-reports', new_tab=True), 'icon': 'assessment'},
    'accounting-transactions': {'label': 'Acct. Transactions', 'func': lambda: accounting_transactions_ui.accounting_transactions_content(standalone=False), 'icon': 'receipt_long'},
    'roles':            {'label': 'Roles',             'func': lambda: roles.roles_content(standalone=False), 'icon': 'group'},
    'appointments':     {'label': 'Appointments',      'func': lambda: appointments_ui.appointments_content(standalone=False), 'icon': 'event'},
    'services':         {'label': 'Services',          'func': lambda: services_ui.services_content(standalone=False), 'icon': 'build'},
    'company':          {'label': 'Company',           'func': make_iframe('/company'),     'icon': 'business_center'},
    'profile':          {'label': 'My Account',        'func': make_iframe('/profile'),     'icon': 'manage_accounts'},
}


    # State for Split View
    state = {
        'is_split': False,
        'active_side': 'left', # 'left' or 'right'
        'right_open_tabs': {}, # name -> tab_obj
    }

    # Main Layout Container
    with ui.column().classes('w-full flex-1 gap-0 mesh-gradient') as main_container:
        # Splitter for Side-by-Side view
        splitter = ui.splitter(value=100, reverse=False).classes('w-full flex-1')
        splitter.props('separator-class=bg-[#08CB00]/20 separator-style=width:4px')
        
        with splitter.before:
            # Primary Tab Panels Container
            tab_panels_left = ui.tab_panels(navigation.tabs_ui).classes('w-full h-full bg-transparent')
            navigation.tab_panels_ui = tab_panels_left
        
        with splitter.after:
            # Secondary Area (Initially hidden by splitter value=100)
            with ui.column().classes('w-full h-full bg-black/5 border-l border-white/10') as right_area:
                with ui.row().classes('w-full items-center justify-between p-2 bg-white/5 border-b border-white/10'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('space_dashboard', size='xs').classes('text-[#08CB00] ml-2')
                        ui.label('Secondary Workspace').classes('text-xs font-black uppercase tracking-widest text-[#08CB00]')
                    
                    with ui.row().classes('items-center gap-2'):
                        # Module selector for the right side
                        right_selector = ui.select(
                            {k: v['label'] for k, v in content_map.items()},
                            label='Open Module',
                            with_input=True,
                            on_change=lambda e: open_tab_callback(e.value, side='right')
                        ).props('dense outlined size=xs').classes('w-32 bg-white/50')
                        
                        ui.button(icon='close', on_click=lambda: toggle_split_view()).props('flat round dense size=xs').classes('text-gray-400 hover:text-red-500')
                
                # Secondary Tabs and Panels
                tabs_right = ui.tabs().classes('w-full text-gray-600 border-b border-white/5')
                tabs_right.props('active-color=#08CB00 indicator-color=#08CB00 dense ripple=False')
                tab_panels_right = ui.tab_panels(tabs_right).classes('w-full flex-1 bg-transparent')

    def toggle_split_view():
        """Toggle split view mode"""
        state['is_split'] = not state['is_split']
        splitter.set_value(50 if state['is_split'] else 100)
        if not state['is_split']:
            state['active_side'] = 'left'
            navigation.tab_panels_ui = tab_panels_left
            # Link header tabs back to left panels
            navigation.tabs_ui.props(f'value={tab_panels_left.value}')
        else:
            ui.notify('Split View active. Use the secondary area for side-by-side work.', color='#08CB00')
        return state['is_split']

    # Link toggle to navigation
    navigation.split_view_callback = toggle_split_view

    def open_tab_callback(page_key, new_instance=False, side='left'):
        """Callback for navigation to open or switch to a tab"""
        global current_open_tab, tab_refresh_callbacks
        
        if page_key not in content_map:
            ui.notify(f"Module {page_key} not found", color='warning')
            return
            
        config = content_map[page_key]
        label = config['label']
        
        # Determine target containers based on side
        target_panels = tab_panels_right if side == 'right' else tab_panels_left
        target_tabs = tabs_right if side == 'right' else navigation.tabs_ui
        target_open_tabs = state['right_open_tabs'] if side == 'right' else navigation.open_tabs

        # Determine unique key for this instance
        if new_instance:
            instance_count = sum(1 for k in navigation.open_tabs if k.startswith(page_key)) + \
                             sum(1 for k in state['right_open_tabs'] if k.startswith(page_key))
            tab_key = f"{page_key}_{instance_count + 1}"
            display_label = f"{label} #{instance_count + 1}"
        else:
            tab_key = page_key
            display_label = label
        
        # Check if tab already exists in the TARGET side
        if tab_key in target_open_tabs:
            tab_obj = target_open_tabs[tab_key]
            tab_obj.set_visibility(True)
            target_panels.value = tab_obj
            
            # Refresh if registered
            refresh_key = page_key if page_key in tab_refresh_callbacks else tab_key
            if refresh_key in tab_refresh_callbacks:
                try: tab_refresh_callbacks[refresh_key]()
                except: pass
            
            # If side was right, ensure split view is shown
            if side == 'right' and not state['is_split']: toggle_split_view()
            return

        # Create new tab in the target side
        with target_tabs:
            with ui.tab(display_label, icon=config['icon']).classes('px-4 active:bg-[#08CB00]/10') as new_tab:
                if page_key != 'dashboard' or side == 'right':
                    # Close button
                    ui.button(icon='close', on_click=lambda k=tab_key, s=side: close_tab(k, s)).props('flat round dense size=xs').classes('text-gray-400 hover:text-red-500 ml-2')
            target_open_tabs[tab_key] = new_tab
            
        # Create new panel
        with target_panels:
            with ui.tab_panel(new_tab).classes('p-0'):
                try:
                    config['func']()
                except Exception as e:
                    ui.notify(f'Error loading {display_label}: {str(e)}', color='red')
        
        target_panels.value = new_tab
        if side == 'right' and not state['is_split']:
            toggle_split_view()

    def force_close_tab(page_key, side):
        """Actually close the tab and its panel"""
        target_open_tabs = state['right_open_tabs'] if side == 'right' else navigation.open_tabs
        target_panels = tab_panels_right if side == 'right' else tab_panels_left
        
        if page_key in target_open_tabs:
            tab_obj = target_open_tabs[page_key]
            if target_panels.value == tab_obj:
                # Switch to another tab if closing active
                remaining = [t for t in target_open_tabs.values() if t != tab_obj]
                if remaining: 
                    target_panels.value = remaining[0]
                elif side == 'left' and navigation.open_tabs.get('dashboard'):
                    target_panels.value = navigation.open_tabs.get('dashboard')
            
            try:
                tab_obj.set_visibility(False)
                del target_open_tabs[page_key]
            except: pass

    def close_tab(page_key, side='left'):
        """Close a tab, warning if it has unsaved changes"""
        is_dirty = False
        
        # Handle unique tab keys (e.g. sales_2) by extracting the base key
        base_key = page_key.split('_')[0] if '_' in page_key else page_key
        cb_key = page_key if page_key in tab_dirty_callbacks else base_key
        
        if cb_key in tab_dirty_callbacks:
            try:
                is_dirty = tab_dirty_callbacks[cb_key]()
            except Exception as e:
                print(f"Error checking dirty state for {cb_key}: {e}")
                
        if is_dirty:
            with ui.dialog() as dialog, ui.card().classes('p-6 rounded-xl shadow-lg'):
                ui.label('Unsaved Changes').classes('text-xl font-bold text-red-500 mb-2')
                ui.label('You have unsaved changes in this tab. Do you want to close it anyway?').classes('mb-6 text-gray-700')
                with ui.row().classes('w-full justify-end gap-3'):
                    ui.button('Cancel', on_click=dialog.close).props('outline color=gray')
                    ui.button('Close Tab', color='red', on_click=lambda: (dialog.close(), force_close_tab(page_key, side)))
            dialog.open()
        else:
            force_close_tab(page_key, side)

    # Set the callback in navigation
    navigation.open_tab_callback = open_tab_callback
    
    # Store globally for other modules to use
    current_open_tab = open_tab_callback

    # Open Dashboard by default
    open_tab_callback('dashboard')

    # Footer with system time, company name, and username
    with ui.footer().classes('flex justify-between items-center p-4 glass bg-white/5 border-t border-white/10 text-white').style('font-size: 1rem;'):
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
    """Create a premium dashboard content with glassmorphism and modern stats"""
    from modern_ui_components import ModernStats, ModernCard, ModernButton
    from modern_design_system import ModernDesignSystem as MDS

    with ui.column().classes('p-8 w-full gap-8 animate-fade-in'):
        # Header Section
        with ui.row().classes('w-full justify-between items-center bg-white/5 p-6 rounded-3xl glass border border-white/10'):
            with ui.column().classes('gap-1'):
                ui.label('Enterprise Overview').classes('text-lg font-black uppercase tracking-[0.2em] text-white')
                ui.label('Executive Performance Dashboard').classes('text-5xl font-black text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('gap-4'):
                ModernButton('System Health', icon='sensors', variant='outline', size='sm').classes('text-white border-white/20')
                ModernButton('Download Report', icon='file_download', variant='secondary', size='sm')

        # Premium Quick Stats
        with ui.grid(columns=4).classes('w-full gap-6'):
            # Sales today
            sales_today = connection.get_today_sales()
            ModernStats(
                label='Revenue Real-time', 
                value=f'${sales_today:,.2f}', 
                icon='monetization_on', 
                trend='+12.5% from yesterday', 
                trend_positive=True,
                color='#08CB00'
            )

            # Total products
            total_products = connection.get_total_products()
            ModernStats(
                label='Global Inventory', 
                value=f'{total_products:,}', 
                icon='warehouse', 
                trend='32 items low stock', 
                trend_positive=False,
                color='#08CB00'
            )

            # Total customers
            total_customers = connection.get_total_customers()
            ModernStats(
                label='Active Portfolio', 
                value=f'{total_customers:,}', 
                icon='person_add', 
                trend='+5 new this week', 
                trend_positive=True,
                color='#08CB00'
            )

            # Low stock items
            low_stock = connection.get_low_stock_count()
            ModernStats(
                label='Operational Risk', 
                value=str(low_stock), 
                icon='report_problem', 
                trend='Requires Attention', 
                trend_positive=False,
                color='#08CB00'
            )

        # Quick Actions & Secondary Insights
        with ui.row().classes('w-full gap-6'):
            # Actions Panel
            with ModernCard(glass=True).classes('flex-1 p-8').style('border-radius: 2rem;'):
                ui.label('Strategic Actions').classes('text-3xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
                
                with ui.grid(columns=2).classes('w-full gap-4'):
                    ModernButton('Execute New Sale', icon='point_of_sale', variant='primary', size='lg').classes('h-24 text-lg shadow-lg shadow-green-500/20')
                    ModernButton('Catalog Management', icon='edit_note', variant='secondary', size='lg').classes('h-24 text-lg')
                    ModernButton('Fleet Logistics', icon='local_shipping', variant='outline', size='lg').classes('h-24 text-lg')
                    ModernButton('Financial Audits', icon='account_balance', variant='outline', size='lg').classes('h-24 text-lg')
            
            # System Status
                ui.label('System Feed').classes('text-2xl font-bold mb-4 text-white').style('font-family: "Outfit", sans-serif;')
                
                activities = [
                    ('Sales', 'Invoice #1024 synced', '2m ago'),
                    ('Inventory', 'Stock alert: Coffee', '15m ago'),
                    ('User', 'Admin logged in', '1h ago')
                ]
                
                with ui.column().classes('w-full gap-4'):
                    for cat, desc, time in activities:
                        with ui.row().classes('w-full justify-between items-center p-3 rounded-xl bg-white/10 hover:bg-white/20 transition-all'):
                            with ui.column().classes('gap-0'):
                                ui.label(cat).classes('text-xs font-black uppercase text-[#08CB00]')
                                ui.label(desc).classes('text-sm font-bold text-white')
                            ui.label(time).classes('text-xs text-white/60')


# Export the session storage for use in other modules
__all__ = ['session_storage', 'check_page_access', 'require_login', 'get_current_user', 'current_open_tab', 'tab_refresh_callbacks', 'tab_dirty_callbacks']
