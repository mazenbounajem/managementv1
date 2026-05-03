import sys
with open(r'c:\dbbackup\managementv1\tabbed_dashboard.py', 'r', encoding='utf-8') as f:
    text = f.read()

start_marker = '# ── MAIN BODY : Module Launcher + Financials'
end_marker = '# Export the session storage for use in other modules'

start_idx = text.find(start_marker)
if start_idx != -1:
    start_idx = text.rfind('\n', 0, start_idx) + 1

end_idx = text.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print('Failed to find markers')
    sys.exit(1)

new_content = """        # ── MAIN BODY : Financials, Inventory, Orders, Live Activity ─────────────────────
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
                meter_row('Today\\'s Sales',  sales_today,  ref, '#08CB00')
                meter_row('Week\\'s Sales',   week_sales,   ref, '#3b82f6')
                meter_row('Month\\'s Sales',  month_sales,  ref, '#a78bfa')
                meter_row('Today\\'s Expenses', float(exp_today), ref, '#ef4444')

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

"""

new_text = text[:start_idx] + new_content + text[end_idx:]

with open(r'c:\dbbackup\managementv1\tabbed_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Success!')
