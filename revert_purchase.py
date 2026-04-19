def main():
    with open('purchaseui.py', 'r', encoding='utf-8') as f:
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
            if "except Exception as e:" in line or "ui.label" in line or "PurchaseReturnsUI" in line or "from purchase_returns_ui" in line or "try:" in line or "from nicegui import ui" in line:
                continue
            start_ret_tab = False
            new_lines.append(line)
            continue
            
        new_lines.append(line)

    # Let's also restore the original un-indented structure for purchaseui.py!
    # Because my fix_purchase_indent.py indented everything between start_idx and end_idx by 8 spaces.
    # To fix this, I need to unindent everything by 8 spaces where the indentation is > 8.
    # Actually, let's just use regex to un-indent the block.
    # We will look for "        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):"
    
    start_idx = -1
    for i, line in enumerate(new_lines):
        if "with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):" in line:
            start_idx = i
            break
            
    if start_idx != -1:
        end_idx = -1
        for i, line in enumerate(new_lines[start_idx:]):
            if "def purchase_page_route():" in line:
                end_idx = start_idx + i
                break
        
        if end_idx != -1:
            for i in range(start_idx+1, end_idx):
                if new_lines[i].startswith("        "):
                    new_lines[i] = new_lines[i][8:]

    with open('purchaseui.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('SUCCESS')

if __name__ == '__main__':
    main()
