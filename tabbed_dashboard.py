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
from settings_backup_ui import settings_backup_content
import supplier_payment_ui_fixed_v2
from timespendui import TimeSpendUI
import sales_returns_ui
import purchase_returns_ui
import sys
from ledgerui import ledger_content
from auxiliaryui import auxiliary_content
import voucher_subtype_ui
import accounting_transactions_ui
from business_track import business_track_content
import company_ui
import trial_hierarchy_ui

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

    'products':         {'label': 'Products',          'func': product_content,             'icon': 'inventory'},
    'customers':        {'label': 'Customers',         'func': customer_content,            'icon': 'person'},
    'suppliers':        {'label': 'Suppliers',         'func': supplier_content,            'icon': 'business'},
    'timespend':        {'label': 'Time Analysis',     'func': lambda: TimeSpendUI(show_header=False), 'icon': 'schedule'},
    'category':         {'label': 'Categories',        'func': category_content_method,     'icon': 'category'},
    'employees':        {'label': 'Employees',         'func': employee_content,            'icon': 'badge'},
    'backup':           {'label': 'Database Backup',   'func': lambda: settings_backup_content(standalone=False), 'icon': 'backup'},
    'stockoperations':  {'label': 'Stock Operations',  'func': stockoperationui.stock_operations_page, 'icon': 'inventory_2'},
    'supplierpayment':  {'label': 'Supplier Payment',  'func': lambda: supplier_payment_ui_fixed_v2.SupplierPaymentUI(show_navigation=False), 'icon': 'payment'},
    'expenses':         {'label': 'Expenses',          'func': lambda: __import__('expenses').expenses_content(standalone=False), 'icon': 'money_off'},
    'expensestype':     {'label': 'Expense Types',     'func': lambda: __import__('expensestype').expensestype_content(standalone=False), 'icon': 'category'},
    'currencies':       {'label': 'Currencies',        'func': lambda: currencies.currencies_content(standalone=False), 'icon': 'currency_exchange'},
    'accounting':       {'label': 'Accounting',        'func': lambda: accounting_finance.accounting_finance_content(standalone=False), 'icon': 'account_balance'},
    'cash-drawer':      {'label': 'Cash Drawer',       'func': lambda: cashdrawer_ui.cash_drawer_content(standalone=False), 'icon': 'account_balance_wallet'},
    'ledger':           {'label': 'Ledger',            'func': lambda: ledgerui.ledger_content(standalone=False), 'icon': 'account_balance'},
    'auxiliary':        {'label': 'Auxiliary',         'func': lambda: auxiliary_content(standalone=False), 'icon': 'account_balance'},
    'journal_voucher':  {'label': 'Journal Voucher',   'func': lambda: journal_voucher_ui.journal_voucher_content(standalone=False), 'icon': 'receipt_long'},
    'voucher_subtype':  {'label': 'Voucher Subtype',   'func': lambda: voucher_subtype_ui.voucher_subtype_content(standalone=False), 'icon': 'category'},
    'customerreceipt':  {'label': 'Customer Receipt',  'func': lambda: customer_receipt_ui_fixed_v2.CustomerReceiptUI(show_navigation=False), 'icon': 'receipt'},
    'reports':          {'label': 'Reports',           'func': lambda: reports_ui.reports_content(standalone=False), 'icon': 'analytics'},
'modern-reports': {'label': 'Accounting Reports', 'func': lambda: ui.run_javascript('window.open("/modern-reports", "_blank");'), 'icon': 'assessment'},
    'accounting-transactions': {'label': 'Acct. Transactions', 'func': lambda: accounting_transactions_ui.accounting_transactions_content(standalone=False), 'icon': 'receipt_long'},
    'business-track':   {'label': 'Business Track',    'func': lambda: business_track_content(standalone=False), 'icon': 'insights'},
    'roles':            {'label': 'Roles',             'func': lambda: roles.roles_content(standalone=False), 'icon': 'group'},
    'appointments':     {'label': 'Appointments',      'func': lambda: appointments_ui.appointments_content(standalone=False), 'icon': 'event'},
    'sales-returns':    {'label': 'Sales Returns',     'func': lambda: sales_returns_ui.SalesReturnsUI(show_navigation=False), 'icon': 'assignment_return'},
    'purchase-returns': {'label': 'Purchase Returns',  'func': lambda: purchase_returns_ui.PurchaseReturnsUI(show_navigation=False), 'icon': 'assignment_return'},
    'services':         {'label': 'Services',          'func': lambda: services_ui.services_content(standalone=False), 'icon': 'build'},
    'company':          {'label': 'Company',           'func': lambda: company_ui.CompanyUI(show_navigation=False, show_footer=False), 'icon': 'business_center'},
    'trial-hierarchy':  {'label': 'Trial Hierarchy',   'func': lambda: trial_hierarchy_ui.trial_hierarchy_content(standalone=False), 'icon': 'account_tree'},
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
        company_name = company_info.get('company_name') if company_info else ''
        ui.label(company_name)

        # Username
        username = user.get('username') if user else 'Guest'
        ui.label(f'User: {username}')

def create_dashboard_content():
    """Create a professional, data-rich dashboard with live KPIs and module launcher"""
    from modern_ui_components import ModernStats, ModernCard, ModernButton
    from modern_design_system import ModernDesignSystem as MDS
    import datetime
    import time as _time

    # ── TTL Cache for dashboard queries (Phase 5) ───────────────────────
    _CACHE_TTL = 60  # seconds

    if not hasattr(create_dashboard_content, '_cache'):
        create_dashboard_content._cache = {}

    def _cached(key, fn):
        cache = create_dashboard_content._cache
        now = _time.time()
        if key in cache and (now - cache[key][1]) < _CACHE_TTL:
            return cache[key][0]
        try:
            val = fn()
        except Exception:
            val = cache[key][0] if key in cache else None
        cache[key] = (val, now)
        return val

    # ── Live Data Fetching (cached) ─────────────────────────────────────
    sales_today     = _cached('sales_today',     connection.get_today_sales) or 0.0
    week_sales      = _cached('week_sales',      connection.get_week_sales) or 0.0
    month_sales     = _cached('month_sales',     connection.get_month_sales) or 0.0
    total_products  = _cached('total_products',  connection.get_total_products) or 0
    total_customers = _cached('total_customers', connection.get_total_customers) or 0
    low_stock       = _cached('low_stock',       connection.get_low_stock_count) or 0
    company_info    = _cached('company_info',    connection.get_company_info) or {}
    company_name    = company_info.get('company_name', '') if company_info else ''

    # Try to get supplier count
    try:
        from database_manager import db_manager
        sup_count = _cached('sup_count', lambda: db_manager.execute_scalar('SELECT COUNT(*) FROM suppliers')) or 0
        exp_today = _cached('exp_today', lambda: db_manager.execute_scalar(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE CAST(expense_date AS DATE)=CAST(GETDATE() AS DATE)"
        )) or 0.0
    except Exception:
        sup_count = 0
        exp_today = 0.0

    # ── STYLES INJECTION ────────────────────────────────────────────────
    ui.add_head_html("""
    <style>
      @keyframes pulse-ring {
        0%   { transform: scale(1);   opacity: 0.7; }
        70%  { transform: scale(1.15); opacity: 0; }
        100% { transform: scale(1.15); opacity: 0; }
      }
      .kpi-card { transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease; }
      .kpi-card:hover { transform: translateY(-6px) scale(1.02); box-shadow: 0 22px 50px rgba(0,0,0,.25); }
      .module-tile { transition: transform .2s cubic-bezier(.34,1.56,.64,1), box-shadow .2s ease; cursor: pointer; }
      .module-tile:hover { transform: translateY(-4px) scale(1.03); box-shadow: 0 16px 40px rgba(8,203,0,.15); }
      .progress-bar-fill { transition: width .8s cubic-bezier(.22,1,.36,1); }
      @keyframes count-up { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
      .kpi-value { animation: count-up .6s ease forwards; }
      .section-title { font-family: 'Outfit', sans-serif; font-weight: 900; letter-spacing: -.02em; }
    </style>
    """)

    # ── Helper: KPI Card ────────────────────────────────────────────────
    def kpi_card(label, value, icon, color, sub=None, sub_positive=True):
        with ui.card().classes('kpi-card p-6 flex-1 glass border border-white/10 overflow-hidden relative').style(
            f'border-left: 4px solid {color}; border-radius: 1.5rem; min-width: 180px;'
        ):
            # Decorative blob
            ui.element('div').style(
                f'position:absolute; width:80px; height:80px; border-radius:50%; '
                f'background:{color}18; right:-10px; top:-10px; pointer-events:none;'
            )
            with ui.column().classes('gap-1 relative z-10'):
                with ui.row().classes('items-center justify-between w-full'):
                    ui.label(label).classes('text-xs font-bold uppercase tracking-widest text-white/60')
                    with ui.element('div').classes('p-2 rounded-xl').style(f'background:{color}22'):
                        ui.icon(icon).style(f'font-size:20px; color:{color};')
                ui.label(value).classes('kpi-value text-3xl font-black text-white mt-1').style(
                    'font-family:"Outfit",sans-serif;'
                )
                if sub:
                    icon_name = 'trending_up' if sub_positive else 'trending_down'
                    clr = '#34d399' if sub_positive else '#f87171'
                    with ui.row().classes('items-center gap-1 mt-1'):
                        ui.icon(icon_name).style(f'font-size:13px; color:{clr};')
                        ui.label(sub).classes('text-xs font-semibold').style(f'color:{clr};')

    # ── Helper: Module Tile ─────────────────────────────────────────────
    def module_tile(label, icon, color, callback):
        with ui.card().classes('module-tile glass border border-white/10 p-4 items-center justify-center text-center').style(
            'border-radius:1.25rem; min-height:90px;'
        ).on('click', callback):
            with ui.column().classes('items-center gap-2'):
                with ui.element('div').classes('p-3 rounded-xl').style(f'background:{color}22'):
                    ui.icon(icon).style(f'font-size:26px; color:{color};')
                ui.label(label).classes('text-xs font-bold text-white/80').style('letter-spacing:.02em;')

    # ════════════════════════════════════════════════════════════════════
    #  DASHBOARD LAYOUT
    # ════════════════════════════════════════════════════════════════════
    with ui.column().classes('w-full gap-7 animate-fade-in').style('padding: 2rem;'):

        # ── HEADER ─────────────────────────────────────────────────────
        with ui.row().classes('w-full items-center justify-between glass border border-white/10 p-5 rounded-3xl'):
            with ui.column().classes('gap-0'):
                ui.label('COMMAND CENTER').classes('text-xs font-black uppercase tracking-[.25em] text-[#08CB00]')
                ui.label(company_name).classes('section-title text-4xl text-white')
                ui.label(
                    datetime.datetime.now().strftime('📅  %A, %B %d %Y  •  %H:%M')
                ).classes('text-sm text-white/50 mt-1')
            with ui.row().classes('gap-3'):
                with ui.element('div').classes('flex items-center gap-2 px-4 py-2 rounded-xl glass border border-white/10'):
                    with ui.element('div').style(
                        'width:8px;height:8px;border-radius:50%;background:#08CB00;'
                        'box-shadow:0 0 0 0 rgba(8,203,0,.7);animation:pulse-ring 2s infinite;'
                    ): pass
                    ui.label('System Online').classes('text-xs font-bold text-white/70')

        # ── KPI ROW ─────────────────────────────────────────────────────
        with ui.row().classes('w-full gap-5 flex-wrap'):
            kpi_card('Today\'s Revenue',  f'${sales_today:,.2f}',   'payments',      '#08CB00',  f'Week: ${week_sales:,.0f}',  True)
            kpi_card('Monthly Sales',    f'${month_sales:,.2f}',   'bar_chart',     '#3b82f6',  'Current period',             True)
            kpi_card('Total Customers',  f'{total_customers:,}',   'people',        '#a78bfa',  'Active accounts',            True)
            kpi_card('Suppliers',        f'{sup_count:,}',         'business',      '#f59e0b',  'Registered vendors',         True)
            kpi_card('Products',         f'{total_products:,}',    'inventory_2',   '#06b6d4',  'In catalog',                 True)
            kpi_card('Low Stock Alerts', f'{low_stock}',           'report_problem','#ef4444',  'Needs attention',            False)

        # ── MAIN BODY : Financials, Inventory, Orders, Live Activity ─────────────────────
        with ui.grid(columns=2).classes('w-full gap-6 mt-4'):
            
            # — 1. Financial Snapshot
            with ui.card().classes('glass border border-white/10 p-5').style('border-radius:1.5rem; flex: 1;'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('donut_large').style('color:#08CB00; font-size:20px;')
                    ui.label('Financial Snapshot').classes('section-title text-base text-white')

                def meter_row(label, value, max_val, color):
                    pct = min(100, (value / max_val * 100)) if max_val else 0
                    with ui.column().classes('w-full gap-1 mb-3'):
                        with ui.row().classes('justify-between w-full'):
                            ui.label(label).classes('text-xs text-white/60 font-semibold')
                            ui.label('$' + f'{value:,.0f}').classes('text-xs font-black text-white')
                        with ui.element('div').style(
                            'width:100%;height:6px;border-radius:99px;background:rgba(255,255,255,.1);overflow:hidden;'
                        ):
                            ui.element('div').classes('progress-bar-fill').style(
                                f'width:{pct:.1f}%;height:100%;background:{color};border-radius:99px;'
                            )

                ref = max(month_sales, week_sales, sales_today, exp_today, 1)
                meter_row('Today\'s Sales',  sales_today,  ref, '#08CB00')
                meter_row('Week\'s Sales',   week_sales,   ref, '#3b82f6')
                meter_row('Month\'s Sales',  month_sales,  ref, '#a78bfa')
                meter_row('Today\'s Expenses', float(exp_today), ref, '#ef4444')

                ui.separator().classes('my-3 opacity-20')
                with ui.row().classes('justify-between w-full'):
                    with ui.column().classes('items-center gap-0'):
                        ui.label('Net Est.').classes('text-xs text-white/40 uppercase font-bold')
                        net = sales_today - float(exp_today)
                        clr = '#34d399' if net >= 0 else '#f87171'
                        ui.label('$' + f'{net:,.2f}').classes('text-lg font-black').style(f'color:{clr};')
                    with ui.column().classes('items-center gap-0'):
                        ui.label('Month').classes('text-xs text-white/40 uppercase font-bold')
                        ui.label('$' + f'{month_sales:,.0f}').classes('text-lg font-black text-white')

            # — 2. Inventory Health
            with ui.card().classes('glass border border-white/10 p-5').style('border-radius:1.5rem; flex: 1;'):
                with ui.row().classes('items-center gap-2 mb-3'):
                    ui.icon('inventory').style('color:#06b6d4; font-size:20px;')
                    ui.label('Inventory Health').classes('section-title text-base text-white')

                healthy = max(0, total_products - low_stock)
                pct_healthy = (healthy / total_products * 100) if total_products else 100

                with ui.row().classes('justify-between mb-2'):
                    ui.label('Healthy Stock').classes('text-xs text-white/60')
                    ui.label(f'{pct_healthy:.0f}%').classes('text-xs font-black text-[#08CB00]')
                with ui.element('div').style(
                    'width:100%;height:8px;border-radius:99px;background:rgba(255,255,255,.1);overflow:hidden;'
                ):
                    ui.element('div').classes('progress-bar-fill').style(
                        f'width:{pct_healthy:.1f}%;height:100%;'
                        'background:linear-gradient(90deg,#08CB00,#34d399);border-radius:99px;'
                    )

                with ui.row().classes('justify-between mt-6 w-full'):
                    with ui.column().classes('items-center flex-1'):
                        ui.label(f'{total_products}').classes('text-3xl font-black text-white')
                        ui.label('Total SKUs').classes('text-xs text-white/40 uppercase font-bold')
                    with ui.column().classes('items-center flex-1'):
                        ui.label(f'{healthy}').classes('text-3xl font-black text-[#34d399]')
                        ui.label('In Stock').classes('text-xs text-white/40 uppercase font-bold')
                    with ui.column().classes('items-center flex-1'):
                        ui.label(f'{low_stock}').classes('text-3xl font-black text-[#f87171]')
                        ui.label('Low Stock').classes('text-xs text-white/40 uppercase font-bold')

            # — 3. Customer Orders
            with ui.card().classes('glass border border-white/10 p-5').style('border-radius:1.5rem; flex: 1;'):
                with ui.row().classes('items-center justify-between mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('receipt_long').style('color:#3b82f6; font-size:20px;')
                        ui.label('Customer Orders').classes('section-title text-base text-white')
                
                recent_orders = []
                try:
                    from database_manager import db_manager
                    def fetch_sales():
                        try:
                            res = db_manager.execute_query("SELECT invoice_number, total_amount, sale_date FROM sales ORDER BY created_at DESC")
                            return res[:5] if res else []
                        except:
                            try:
                                res2 = db_manager.execute_query("SELECT invoice_number, total_amount, sale_date FROM sales ORDER BY sale_date DESC")
                                return res2[:5] if res2 else []
                            except:
                                return []
                    recent_orders = _cached('recent_orders', fetch_sales) or []
                except:
                    pass

                with ui.column().classes('w-full gap-2'):
                    if not recent_orders:
                        ui.label('No recent orders.').classes('text-xs text-white/40')
                    else:
                        for row in recent_orders:
                            try: inv = row.invoice_number
                            except: inv = row[0] if isinstance(row, (tuple, list)) else row.get('invoice_number', 'N/A')
                            
                            try: amt = float(row.total_amount)
                            except: amt = float(row[1]) if isinstance(row, (tuple, list)) else float(row.get('total_amount', 0))
                            
                            try: sdate = str(row.sale_date)
                            except: sdate = str(row[2]) if isinstance(row, (tuple, list)) else str(row.get('sale_date', ''))
                            
                            with ui.row().classes('w-full items-center justify-between p-3 rounded-xl hover:bg-white/10 transition-all cursor-default border border-white/5'):
                                with ui.row().classes('items-center gap-3'):
                                    with ui.element('div').classes('p-2 rounded-lg flex-shrink-0 bg-[#3b82f6]18').style('background: rgba(59, 130, 246, 0.1);'):
                                        ui.icon('shopping_bag').style('font-size:16px; color:#3b82f6;')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'INV {inv}').classes('text-xs font-black text-white/90 uppercase tracking-wider')
                                        ui.label(sdate[:10]).classes('text-[10px] text-white/50')
                                ui.label('$' + f'{amt:,.2f}').classes('text-sm font-black text-[#34d399]')

            # — 4. Live Activity
            with ui.card().classes('glass border border-white/10 p-5').style('border-radius:1.5rem; flex: 1;'):
                with ui.row().classes('items-center justify-between mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('bolt').style('color:#fbbf24; font-size:20px;')
                        ui.label('Live Activity').classes('section-title text-base text-white')
                    with ui.element('div').style(
                        'width:7px;height:7px;border-radius:50%;background:#08CB00;'
                        'box-shadow:0 0 0 0 rgba(8,203,0,.7);animation:pulse-ring 2s infinite;'
                    ): pass

                activities = [
                    ('point_of_sale', 'Sales', 'New invoice created',    '#08CB00', 'Just now'),
                    ('inventory_2',   'Stock',  'Low stock: 3 products',  '#f59e0b', '5m ago'),
                    ('payments',      'Finance','Supplier payment logged', '#a78bfa', '12m ago'),
                    ('people',        'CRM',    'New customer registered', '#3b82f6', '25m ago'),
                    ('receipt_long',  'Purchase','Purchase order received','#06b6d4', '1h ago'),
                ]

                with ui.column().classes('w-full gap-2'):
                    for ic, cat, desc, clr, ts in activities:
                        with ui.row().classes('w-full items-center gap-3 p-3 rounded-xl hover:bg-white/10 transition-all cursor-default'):
                            with ui.element('div').classes('p-2 rounded-lg flex-shrink-0 flex items-center justify-center').style(f'background:{clr}18;'):
                                ui.icon(ic).style(f'font-size:16px; color:{clr};')
                            with ui.column().classes('flex-1 gap-0'):
                                ui.label(cat).classes('text-xs font-black uppercase').style(f'color:{clr}; letter-spacing:.05em;')
                                ui.label(desc).classes('text-[11px] text-white/70 font-medium')
                            ui.label(ts).classes('text-[10px] text-white/30 flex-shrink-0')

# Export the session storage for use in other modules
__all__ = ['session_storage', 'check_page_access', 'require_login', 'get_current_user', 'current_open_tab', 'tab_refresh_callbacks', 'tab_dirty_callbacks']
