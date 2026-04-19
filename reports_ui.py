from nicegui import ui
from reports import Reports
from datetime import datetime, date, timedelta
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from connection import connection
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS


def reports_content(standalone=False):
    """Content method for reports that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Reports & Analytics", standalone=standalone):
            ReportsUI(standalone=False)
    else:
        ReportsUI(standalone=False)


@ui.page('/reports')
def reports_page_route():
    reports_content(standalone=True)


def _build_ag_columns(headers_list, money_fields=None, pct_fields=None):
    """Build ag-grid column definitions from a list of header names"""
    money_fields = money_fields or []
    pct_fields = pct_fields or []
    cols = []
    for h in headers_list:
        label = h.replace('_', ' ').title()
        col = {'headerName': label, 'field': h, 'sortable': True, 'filter': True}
        if h in money_fields:
            col['valueFormatter'] = '"$" + Number(params.value || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})'
            col['width'] = 130
        elif h in pct_fields:
            col['valueFormatter'] = 'Number(params.value || 0).toFixed(2) + "%"'
            col['width'] = 110
        elif h in ('rank',):
            col['width'] = 70
        elif h in ('barcode',):
            col['width'] = 110
        elif h in ('product_name',):
            col['flex'] = 2
        else:
            col['flex'] = 1
        cols.append(col)
    return cols


class ReportsUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        # Default date range: this month
        self.from_date = date.today().replace(day=1).strftime('%Y-%m-%d')
        self.to_date = date.today().strftime('%Y-%m-%d')

        # Grid and detail refs per tab
        self._grids = {}
        self._detail_containers = {}

        self.create_ui()

    # ──────────────────── UI Construction ────────────────────

    def create_ui(self):
        if self.standalone:
            layout_container = ModernPageLayout("Reports & Analytics", standalone=True)
            layout_container.__enter__()
        try:
            self._build_content()
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def _build_content(self):
        # Top date filter bar (shared across tabs)
        with ui.row().classes('w-full items-end gap-4 p-4 mb-2 rounded-2xl glass border border-gray-200'):
            ui.label('Date Range').classes('text-xs font-black uppercase tracking-widest text-gray-500 self-center')
            self.from_input = ui.input('From').props('outlined dense type=date').classes('w-40')
            self.from_input.value = self.from_date
            self.to_input = ui.input('To').props('outlined dense type=date').classes('w-40')
            self.to_input.value = self.to_date

            ui.button('Today', on_click=lambda: self._set_quick('today')).props('flat dense').classes('text-xs text-purple-600')
            ui.button('This Week', on_click=lambda: self._set_quick('week')).props('flat dense').classes('text-xs text-purple-600')
            ui.button('This Month', on_click=lambda: self._set_quick('month')).props('flat dense').classes('text-xs text-purple-600')
            ui.button('This Year', on_click=lambda: self._set_quick('year')).props('flat dense').classes('text-xs text-purple-600')
            
            with ui.row().classes('gap-2 ml-auto'):
                ModernButton('Apply', icon='filter_list', on_click=self._refresh_current, variant='primary', size='sm')
                ModernButton('PDF', icon='picture_as_pdf', on_click=self._export_pdf, variant='secondary', size='sm')
                ModernButton('Excel', icon='table_chart', on_click=self._export_excel, variant='secondary', size='sm')

        # Main Tabs
        with ui.tabs().classes('w-full').props('active-color=purple indicator-color=purple dense') as self.tabs:
            t1 = ui.tab('sales_item', label='Sales by Item', icon='bar_chart')
            t2 = ui.tab('profit_period', label='Profit by Period', icon='trending_up')
            t3 = ui.tab('most_profitable', label='Most Profitable', icon='emoji_events')
            t4 = ui.tab('fast_moving', label='Fast Moving', icon='bolt')
            t5 = ui.tab('slow_moving', label='Slow Moving', icon='hourglass_bottom')

        self.tabs.on('update:model-value', lambda e: self._on_tab_change(e.args))

        with ui.tab_panels(self.tabs, value=t1).classes('w-full flex-1'):
            with ui.tab_panel(t1).classes('p-0 pt-2'):
                self._build_sales_by_item_tab()
            with ui.tab_panel(t2).classes('p-0 pt-2'):
                self._build_profit_period_tab()
            with ui.tab_panel(t3).classes('p-0 pt-2'):
                self._build_most_profitable_tab()
            with ui.tab_panel(t4).classes('p-0 pt-2'):
                self._build_fast_slow_tab('fast_moving', 'Fast Moving Items',
                    'bolt', 'Items with highest quantity sold',
                    Reports.fetch_fast_moving_items)
            with ui.tab_panel(t5).classes('p-0 pt-2'):
                self._build_fast_slow_tab('slow_moving', 'Slow Moving Items',
                    'hourglass_bottom', 'Items with lowest quantity sold',
                    Reports.fetch_slow_moving_items)

        self._active_tab = 'sales_item'
        # Load initial data for the first tab
        ui.timer(0.15, self._load_sales_by_item, once=True)

    # ──────────────────── Quick Date Buttons ────────────────────

    def _set_quick(self, period):
        today = date.today()
        if period == 'today':
            f, t = today, today
        elif period == 'week':
            f = today - timedelta(days=today.weekday())
            t = today
        elif period == 'month':
            f = today.replace(day=1)
            t = today
        elif period == 'year':
            f = today.replace(month=1, day=1)
            t = today
        else:
            f, t = today.replace(day=1), today
        self.from_input.value = f.strftime('%Y-%m-%d')
        self.to_input.value = t.strftime('%Y-%m-%d')
        self._refresh_current()

    def _refresh_current(self):
        tab = self._active_tab
        if tab == 'sales_item':
            self._load_sales_by_item()
        elif tab == 'profit_period':
            self._load_profit_period()
        elif tab == 'most_profitable':
            self._load_most_profitable()
        elif tab == 'fast_moving':
            self._load_fast_slow('fast_moving', Reports.fetch_fast_moving_items)
        elif tab == 'slow_moving':
            self._load_fast_slow('slow_moving', Reports.fetch_slow_moving_items)

    def _on_tab_change(self, tab_name):
        self._active_tab = tab_name
        self._refresh_current()

    # ──────────────────── Tab 1: Sales by Item ────────────────────

    def _build_sales_by_item_tab(self):
        money = ['total_revenue', 'total_cost', 'total_profit']
        pct = ['profit_margin_pct']
        headers = ['product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'total_cost', 'total_profit', 'profit_margin_pct']
        cols = _build_ag_columns(headers, money_fields=money, pct_fields=pct)

        with ui.column().classes('w-full gap-3 p-2'):
            with ui.row().classes('w-full items-center justify-between mb-1'):
                ui.label('Sales by Item').classes('text-xl font-black text-gray-900')
                self._sales_item_count = ui.label('').classes('text-xs text-gray-500')

            grid = ui.aggrid({
                'columnDefs': cols,
                'rowData': [],
                'rowSelection': 'single',
                'defaultColDef': {'resizable': True, 'sortable': True},
                'pagination': True,
                'paginationPageSize': 20,
            }).classes('w-full ag-theme-quartz-custom').style('height: 380px;')
            self._grids['sales_item'] = grid

            # Detail panel
            with ModernCard(glass=True).classes('w-full p-5 mt-2'):
                ui.label('Selected Item Details').classes('text-xs font-black uppercase tracking-widest text-gray-500 mb-3')
                with ui.grid(columns=4).classes('w-full gap-4'):
                    self._si_product = self._detail_field('Product Name')
                    self._si_barcode = self._detail_field('Barcode')
                    self._si_qty = self._detail_field('Total Qty Sold')
                    self._si_revenue = self._detail_field('Revenue')
                    self._si_cost = self._detail_field('Cost')
                    self._si_profit = self._detail_field('Profit')
                    self._si_margin = self._detail_field('Margin %')

            grid.on('cellClicked', self._on_sales_item_row_click)

    def _on_sales_item_row_click(self, e):
        try:
            row = e.args.get('data', {})
            if not row:
                return
            self._si_product.set_value(str(row.get('product_name', '')))
            self._si_barcode.set_value(str(row.get('barcode', '')))
            self._si_qty.set_value(str(row.get('total_qty_sold', '')))
            self._si_revenue.set_value(f"${float(row.get('total_revenue', 0)):,.2f}")
            self._si_cost.set_value(f"${float(row.get('total_cost', 0)):,.2f}")
            self._si_profit.set_value(f"${float(row.get('total_profit', 0)):,.2f}")
            self._si_margin.set_value(f"{float(row.get('profit_margin_pct', 0)):,.2f}%")
        except Exception as ex:
            print(f"Detail update error: {ex}")

    def _load_sales_by_item(self):
        try:
            data = Reports.fetch_sales_by_item(self.from_input.value, self.to_input.value)
            grid = self._grids.get('sales_item')
            if grid:
                grid.options['rowData'] = [self._serialize(r) for r in data]
                grid.update()
            if hasattr(self, '_sales_item_count'):
                self._sales_item_count.set_text(f'{len(data)} items')
            # Load last row into detail
            if data:
                class FakeEvent:
                    args = {'data': data[0]}
                self._on_sales_item_row_click(FakeEvent())
        except Exception as ex:
            ui.notify(f'Error loading sales by item: {ex}', color='red')

    # ──────────────────── Tab 2: Profit by Period ────────────────────

    def _build_profit_period_tab(self):
        with ui.column().classes('w-full gap-3 p-2'):
            ui.label('Profit by Period').classes('text-xl font-black text-gray-900')

            # Period selector buttons
            with ui.row().classes('gap-2 mb-2'):
                self._pp_buttons = {}
                for period in ['Day', 'Week', 'Month', 'Year']:
                    btn = ui.button(period,
                        on_click=lambda p=period.lower(): self._switch_profit_period(p)
                    ).props('unelevated').classes('px-5 rounded-xl text-sm font-bold')
                    self._pp_buttons[period.lower()] = btn
                self._pp_active = 'day'
                self._style_period_buttons('day')

            # Grid container
            self._pp_grid_container = ui.column().classes('w-full')
            with self._pp_grid_container:
                self._pp_grid = ui.aggrid({
                    'columnDefs': [],
                    'rowData': [],
                    'rowSelection': 'single',
                    'defaultColDef': {'resizable': True, 'sortable': True},
                    'pagination': True,
                    'paginationPageSize': 20,
                }).classes('w-full ag-theme-quartz-custom').style('height: 350px;')

            # Detail panel
            with ModernCard(glass=True).classes('w-full p-5 mt-2'):
                ui.label('Selected Period Details').classes('text-xs font-black uppercase tracking-widest text-gray-500 mb-3')
                with ui.grid(columns=4).classes('w-full gap-4'):
                    self._pp_period_val = self._detail_field('Period')
                    self._pp_revenue = self._detail_field('Revenue')
                    self._pp_cost = self._detail_field('Cost')
                    self._pp_profit = self._detail_field('Profit')
                    self._pp_orders = self._detail_field('Orders')

            self._pp_grid.on('cellClicked', self._on_profit_period_row_click)
            ui.timer(0.2, lambda: self._load_profit_period(), once=True)

    def _style_period_buttons(self, active):
        colors = {'day': 'bg-purple-600', 'week': 'bg-purple-600',
                  'month': 'bg-purple-600', 'year': 'bg-purple-600'}
        for period, btn in self._pp_buttons.items():
            if period == active:
                btn.classes(remove='bg-white/10', add='bg-purple-600 text-white')
            else:
                btn.classes(remove='bg-purple-600 text-white', add='bg-white/10')

    def _switch_profit_period(self, period):
        self._pp_active = period
        self._style_period_buttons(period)
        self._load_profit_period()

    def _load_profit_period(self):
        period = self._pp_active
        f = self.from_input.value
        t = self.to_input.value
        try:
            if period == 'day':
                data = Reports.fetch_profit_by_day(f, t)
                headers = ['sale_day', 'total_revenue', 'total_cost', 'total_profit', 'total_orders']
                money = ['total_revenue', 'total_cost', 'total_profit']
            elif period == 'week':
                data = Reports.fetch_profit_by_week(f, t)
                headers = ['year', 'week_number', 'week_start', 'total_revenue', 'total_cost', 'total_profit', 'total_orders']
                money = ['total_revenue', 'total_cost', 'total_profit']
            elif period == 'month':
                data = Reports.fetch_profit_by_month(f, t)
                headers = ['year', 'month_number', 'month_name', 'total_revenue', 'total_cost', 'total_profit', 'total_orders']
                money = ['total_revenue', 'total_cost', 'total_profit']
            elif period == 'year':
                data = Reports.fetch_profit_by_year()
                headers = ['year', 'total_revenue', 'total_cost', 'total_profit', 'total_orders', 'profit_margin_pct']
                money = ['total_revenue', 'total_cost', 'total_profit']
            else:
                data = []
                headers = []
                money = []

            cols = _build_ag_columns(headers, money_fields=money,
                                     pct_fields=['profit_margin_pct'])
            self._pp_grid.options['columnDefs'] = cols
            self._pp_grid.options['rowData'] = [self._serialize(r) for r in data]
            self._pp_grid.update()

            # Load first row into detail
            if data:
                class FakeEvent:
                    args = {'data': data[0]}
                self._on_profit_period_row_click(FakeEvent())
        except Exception as ex:
            ui.notify(f'Error loading profit by {period}: {ex}', color='red')

    def _on_profit_period_row_click(self, e):
        try:
            row = e.args.get('data', {})
            # Determine period label
            period = self._pp_active
            if period == 'day':
                period_val = str(row.get('sale_day', ''))
            elif period == 'week':
                period_val = f"Week {row.get('week_number', '')} / {row.get('year', '')} (starts {row.get('week_start', '')})"
            elif period == 'month':
                period_val = f"{row.get('month_name', '')} {row.get('year', '')}"
            elif period == 'year':
                period_val = str(row.get('year', ''))
            else:
                period_val = ''
            self._pp_period_val.set_value(period_val)
            self._pp_revenue.set_value(f"${float(row.get('total_revenue', 0)):,.2f}")
            self._pp_cost.set_value(f"${float(row.get('total_cost', 0)):,.2f}")
            self._pp_profit.set_value(f"${float(row.get('total_profit', 0)):,.2f}")
            self._pp_orders.set_value(str(row.get('total_orders', '')))
        except Exception as ex:
            print(f"Profit period detail error: {ex}")

    # ──────────────────── Tab 3: Most Profitable ────────────────────

    def _build_most_profitable_tab(self):
        with ui.column().classes('w-full gap-3 p-2'):
            ui.label('Most Profitable Items').classes('text-xl font-black text-gray-900')

            with ui.row().classes('gap-2 mb-2'):
                self._mp_by_amount_btn = ui.button('By Amount ($)',
                    on_click=lambda: self._switch_most_profitable('amount')
                ).props('unelevated').classes('px-5 rounded-xl text-sm font-bold bg-purple-600 text-white')
                self._mp_by_pct_btn = ui.button('By Percentage (%)',
                    on_click=lambda: self._switch_most_profitable('percentage')
                ).props('unelevated').classes('px-5 rounded-xl text-sm font-bold bg-white/10')
                self._mp_mode = 'amount'

            self._mp_grid = ui.aggrid({
                'columnDefs': [],
                'rowData': [],
                'rowSelection': 'single',
                'defaultColDef': {'resizable': True, 'sortable': True},
                'pagination': True,
                'paginationPageSize': 20,
            }).classes('w-full ag-theme-quartz-custom').style('height: 350px;')

            with ModernCard(glass=True).classes('w-full p-5 mt-2'):
                ui.label('Selected Item').classes('text-xs font-black uppercase tracking-widest text-gray-500 mb-3')
                with ui.grid(columns=4).classes('w-full gap-4'):
                    self._mp_rank = self._detail_field('Rank')
                    self._mp_product = self._detail_field('Product')
                    self._mp_barcode = self._detail_field('Barcode')
                    self._mp_qty = self._detail_field('Qty Sold')
                    self._mp_revenue = self._detail_field('Revenue')
                    self._mp_cost = self._detail_field('Cost')
                    self._mp_profit = self._detail_field('Profit')
                    self._mp_margin = self._detail_field('Margin %')

            self._mp_grid.on('cellClicked', self._on_most_profitable_row_click)
            ui.timer(0.25, lambda: self._load_most_profitable(), once=True)

    def _switch_most_profitable(self, mode):
        self._mp_mode = mode
        if mode == 'amount':
            self._mp_by_amount_btn.classes(remove='bg-white/10', add='bg-purple-600 text-white')
            self._mp_by_pct_btn.classes(remove='bg-purple-600 text-white', add='bg-white/10')
        else:
            self._mp_by_pct_btn.classes(remove='bg-white/10', add='bg-purple-600 text-white')
            self._mp_by_amount_btn.classes(remove='bg-purple-600 text-white', add='bg-white/10')
        self._load_most_profitable()

    def _load_most_profitable(self):
        f = self.from_input.value
        t = self.to_input.value
        try:
            if self._mp_mode == 'amount':
                data = Reports.fetch_most_profitable_by_amount(f, t)
                headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'total_cost', 'total_profit']
                money = ['total_revenue', 'total_cost', 'total_profit']
                pct = []
            else:
                data = Reports.fetch_most_profitable_by_percentage(f, t)
                headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'total_cost', 'total_profit', 'profit_margin_pct']
                money = ['total_revenue', 'total_cost', 'total_profit']
                pct = ['profit_margin_pct']

            cols = _build_ag_columns(headers, money_fields=money, pct_fields=pct)
            self._mp_grid.options['columnDefs'] = cols
            self._mp_grid.options['rowData'] = [self._serialize(r) for r in data]
            self._mp_grid.update()

            if data:
                class FakeEvent:
                    args = {'data': data[0]}
                self._on_most_profitable_row_click(FakeEvent())
        except Exception as ex:
            ui.notify(f'Error loading most profitable: {ex}', color='red')

    def _on_most_profitable_row_click(self, e):
        try:
            row = e.args.get('data', {})
            self._mp_rank.set_value(str(row.get('rank', '')))
            self._mp_product.set_value(str(row.get('product_name', '')))
            self._mp_barcode.set_value(str(row.get('barcode', '')))
            self._mp_qty.set_value(str(row.get('total_qty_sold', '')))
            self._mp_revenue.set_value(f"${float(row.get('total_revenue', 0)):,.2f}")
            self._mp_cost.set_value(f"${float(row.get('total_cost', 0)):,.2f}")
            self._mp_profit.set_value(f"${float(row.get('total_profit', 0)):,.2f}")
            self._mp_margin.set_value(f"{float(row.get('profit_margin_pct', 0)):,.2f}%")
        except Exception as ex:
            print(f"Most profitable detail error: {ex}")

    # ──────────────────── Tab 4 & 5: Fast / Slow Moving ────────────────────

    def _build_fast_slow_tab(self, key, title, icon, subtitle, fetch_fn):
        headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'num_transactions', 'last_sale_date']
        money = ['total_revenue']
        cols = _build_ag_columns(headers, money_fields=money)

        with ui.column().classes('w-full gap-3 p-2'):
            with ui.row().classes('w-full items-center gap-3 mb-1'):
                ui.icon(icon, size='1.5rem').classes('text-purple-600')
                with ui.column():
                    ui.label(title).classes('text-xl font-black text-gray-900')
                    ui.label(subtitle).classes('text-xs text-gray-500')
                self._grids[key + '_count'] = ui.label('').classes('text-xs text-gray-500 ml-auto')

            grid = ui.aggrid({
                'columnDefs': cols,
                'rowData': [],
                'rowSelection': 'single',
                'defaultColDef': {'resizable': True, 'sortable': True},
                'pagination': True,
                'paginationPageSize': 20,
            }).classes('w-full ag-theme-quartz-custom').style('height: 350px;')
            self._grids[key] = grid

            # Detail panel
            with ModernCard(glass=True).classes('w-full p-5 mt-2'):
                ui.label('Selected Item').classes('text-xs font-black uppercase tracking-widest text-gray-500 mb-3')
                with ui.grid(columns=4).classes('w-full gap-4'):
                    refs = {
                        'rank': self._detail_field('Rank'),
                        'product_name': self._detail_field('Product'),
                        'barcode': self._detail_field('Barcode'),
                        'total_qty_sold': self._detail_field('Total Qty Sold'),
                        'total_revenue': self._detail_field('Revenue'),
                        'num_transactions': self._detail_field('# Transactions'),
                        'last_sale_date': self._detail_field('Last Sale Date'),
                    }
                self._detail_containers[key] = refs

            def on_row(e, k=key, money_f=money):
                try:
                    row = e.args.get('data', {})
                    det = self._detail_containers.get(k, {})
                    for fld, ref in det.items():
                        val = row.get(fld, '')
                        if fld in money_f:
                            ref.set_value(f"${float(val or 0):,.2f}")
                        else:
                            ref.set_value(str(val) if val is not None else '')
                except Exception as ex:
                    print(f"Detail error ({k}): {ex}")

            grid.on('cellClicked', on_row)
            # Load on tab switch (via refresh current)
            self._grids[key + '_fetch'] = fetch_fn
            self._grids[key + '_on_row'] = on_row

    def _load_fast_slow(self, key, fetch_fn):
        try:
            data = fetch_fn(self.from_input.value, self.to_input.value)
            grid = self._grids.get(key)
            if grid:
                grid.options['rowData'] = [self._serialize(r) for r in data]
                grid.update()
            count_lbl = self._grids.get(key + '_count')
            if count_lbl:
                count_lbl.set_text(f'{len(data)} items')
            if data:
                det = self._detail_containers.get(key, {})
                money = ['total_revenue']
                for fld, ref in det.items():
                    val = data[0].get(fld, '')
                    if fld in money:
                        ref.set_value(f"${float(val or 0):,.2f}")
                    else:
                        ref.set_value(str(val) if val is not None else '')
        except Exception as ex:
            ui.notify(f'Error loading {key}: {ex}', color='red')

    # ──────────────────── Helpers ────────────────────

    def _detail_field(self, label):
        """Create a read-only detail display field"""
        inp = ui.input(label).props('readonly outlined dense').classes('w-full')
        return inp

    def _export_pdf(self):
        """Export current tab data as PDF"""
        try:
            grid = self._grids.get(self._active_tab)
            if not grid or not grid.options['rowData']:
                ui.notify('No data to export', color='warning')
                return
            
            headers = [col['headerName'] for col in grid.options['columnDefs']]
            data = grid.options['rowData']
            
            pdf_gen = ReportPDFGenerator(f'{self._active_tab.replace("_", " ").title()} Report')
            pdf_data = pdf_gen.generate(headers, data)
            ui.download(pdf_data, f'report_{self._active_tab}_{datetime.now().strftime("%Y%m%d")}.pdf')
            ui.notify('PDF exported successfully', color='green')
        except Exception as e:
            ui.notify(f'PDF export failed: {e}', color='red')

    def _export_excel(self):
        """Export current tab data as CSV (Excel compatible)"""
        try:
            grid = self._grids.get(self._active_tab)
            if not grid or not grid.options['rowData']:
                ui.notify('No data to export', color='warning')
                return
            
            headers = [col['headerName'] for col in grid.options['columnDefs']]
            data = grid.options['rowData']
            
            csv_data = export_csv(data, headers)
            ui.download(csv_data, f'report_{self._active_tab}_{datetime.now().strftime("%Y%m%d")}.csv')
            ui.notify('Excel/CSV exported successfully', color='green')
        except Exception as e:
            ui.notify(f'Export failed: {e}', color='red')

    @staticmethod
    def _serialize(row):
        """Convert row dict values to JSON-safe types"""
        result = {}
        for k, v in row.items():
            if v is None:
                result[k] = ''
            elif hasattr(v, '__float__'):
                result[k] = float(v)
            elif hasattr(v, 'strftime'):
                result[k] = str(v)
            else:
                result[k] = v
        return result