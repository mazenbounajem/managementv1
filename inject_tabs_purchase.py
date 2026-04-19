import re

def main():
    with open('purchaseui.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        if "def create_ui(self):" in line:
            start_idx = i
        if start_idx != -1 and "def purchase_page_route():" in line:
            end_idx = i
            break

    print('start_idx', start_idx, 'end_idx', end_idx)

    if start_idx != -1 and end_idx != -1:
        old_content = lines[start_idx:end_idx]
        new_content = []
        started_indenting = False
        
        for i in range(len(old_content)):
            line = old_content[i]
            if started_indenting:
                if line.strip():
                    new_content.append('        ' + line)
                else:
                    new_content.append(line)
            else:
                if "with ui.element('div').classes('w-full mesh-gradient" in line:
                    new_content.append('''        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden flex flex-col'):
            with ui.tabs().classes('w-full bg-black/20 text-white border-b border-white/10 h-12') as tabs:
                op_tab = ui.tab('Purchase Operations', icon='shopping_bag').classes('font-bold tracking-widest')
                ret_tab = ui.tab('Purchase Returns', icon='assignment_return').classes('font-bold tracking-widest')
            with ui.tab_panels(tabs, value=op_tab).classes('w-full flex-1 bg-transparent p-0 m-0 overflow-hidden'):
                with ui.tab_panel(op_tab).classes('w-full h-full p-0 m-0 overflow-hidden'):
''')
                    started_indenting = True
                    new_content.append('        ' + line)
                else:
                    new_content.append(line)
                    
        # Add the return tab at the end of the block
        new_content.append('''                with ui.tab_panel(ret_tab).classes('w-full h-full p-0 m-0 overflow-hidden'):
                    try:
                        from purchase_returns_ui import PurchaseReturnsUI
                        PurchaseReturnsUI(standalone=False)
                    except Exception as e:
                        from nicegui import ui
                        ui.label(f'Error loading Purchase Returns UI: {e}').classes('text-red-500 font-bold p-8')
''')
        
        lines[start_idx:end_idx] = new_content
        with open('purchaseui.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print('SUCCESS')

if __name__ == '__main__':
    main()
