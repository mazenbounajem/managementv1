def main():
    with open('salesui_aggrid_compact.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    ignoring = False
    start_ret_tab = False
    for line in lines:
        if "with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden flex flex-col'):" in line:
            ignoring = True
            continue
        if ignoring:
            if "with ui.tabs()" in line or "op_tab =" in line or "ret_tab =" in line or "with ui.tab_panels(" in line or "with ui.tab_panel(op_tab)" in line:
                continue
            if "with ui.element('div')" in line:
                new_lines.append("        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):\n")
                ignoring = False
                continue
        if "with ui.tab_panel(ret_tab)" in line:
            start_ret_tab = True
            continue
        if start_ret_tab:
            if "except Exception as e:" in line or "ui.label" in line or "SalesReturnsUI" in line or "from sales_returns_ui" in line or "try:" in line or "from nicegui import ui" in line:
                continue
            start_ret_tab = False
            new_lines.append(line)
            continue
            
        new_lines.append(line)

    with open('salesui_aggrid_compact.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('SUCCESS')

if __name__ == '__main__':
    main()
