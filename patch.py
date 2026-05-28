import re

with open('e:/managementv1/stock_reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_ui = """    state = {'from_date': from_date_final, 'to_date': to_date_final, 'report_type': 1}

    with ui.dialog() as dlg:
        dlg.props('maximized persistent')
        with ui.card().classes('w-full h-full m-0 rounded-none p-0').style('background:#0d1520; border-radius:0;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-3').style('background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('print', size='1.5rem').classes('text-sky-400')
                    ui.label('Stock Print Special').classes('text-white font-black text-xl').style('font-family:"Outfit",sans-serif;')
                ui.button('X  Close', on_click=dlg.close).classes('bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold')

            with ui.row().classes('w-full gap-0 overflow-hidden').style('height:calc(100vh - 56px);'):
                
                # Left panel: buttons
                with ui.column().classes('h-full p-6 gap-6 overflow-y-auto').style('width:360px; min-width:360px; background:rgba(255,255,255,0.03); border-right:1px solid rgba(255,255,255,0.08);'):
                    ui.label('SELECT REPORT').classes('text-[10px] font-black text-sky-400 uppercase tracking-widest mb-2')
                    
                    rep1_btn = ui.button('1) Adjustment (Cost, Price, Qty)', on_click=lambda: select_report(1)).props('unelevated').classes('w-full py-4 font-bold rounded-xl text-sm shadow-md transition-all').style('justify-content:flex-start;')
                    rep2_btn = ui.button('2) Cost Summation (By Ref & Date)', on_click=lambda: select_report(2)).props('unelevated').classes('w-full py-4 font-bold rounded-xl text-sm shadow-md transition-all mt-2').style('justify-content:flex-start;')

                    def select_report(num):
                        state['report_type'] = num
                        if num == 1:
                            rep1_btn.props('color=primary')
                            rep2_btn.props('color=grey-8')
                        else:
                            rep1_btn.props('color=grey-8')
                            rep2_btn.props('color=secondary')
                        
                    # initialize
                    select_report(1)

                    ui.separator().classes('bg-white/10 mt-4')
                    ui.label('Configure the dates on the right, then click View Report.').classes('text-gray-300 text-xs mt-2')

                # Right panel: from-to + view report button
                with ui.column().classes('flex-1 h-full p-6 gap-6 overflow-auto'):
                    with ui.row().classes('items-end gap-6 glass p-5 rounded-2xl border border-white/10 w-full flex-wrap'):
                        with ui.column().classes('gap-1'):
                            ui.label('FROM').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                            ui.input(value=state['from_date']).props('type=date outlined dense dark color=cyan stack-label').classes('text-white font-bold w-48').on_value_change(lambda e: state.update({'from_date': e.value}))
                        with ui.column().classes('gap-1'):
                            ui.label('TO').classes('text-[9px] font-black text-sky-400 uppercase tracking-widest')
                            ui.input(value=state['to_date']).props('type=date outlined dense dark color=cyan stack-label').classes('text-white font-bold w-48').on_value_change(lambda e: state.update({'to_date': e.value}))
                        
                        def cmd_view_report():
                            f, t = state['from_date'], state['to_date']
                            if not f or not t: return ui.notify('Select dates', color='warning')
                            if f > t: return ui.notify('From before To', color='warning')
                            
                            if state['report_type'] == 1:
                                report_adjustment_cost_price(f, t)
                            else:
                                b64 = report_ops_with_items_grouped_b64(f, t)
                                if b64:
                                    _show(b64, 'Cost Summation Grouped')
                            dlg.close()

                        ui.button('VIEW REPORT', icon='visibility', on_click=cmd_view_report).props('unelevated color=purple').classes('px-10 py-3 rounded-xl font-black text-sm uppercase tracking-widest self-end mb-1 shadow-lg')
    dlg.open()"""

new_text = re.sub(r'    state = \{\'from_date\': from_date_final, \'to_date\': to_date_final\}.*    dlg\.open\(\)', new_ui, text, flags=re.DOTALL)

with open('e:/managementv1/stock_reports.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Success')
