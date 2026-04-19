def main():
    with open('purchaseui.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(lines):
        if "with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):" in line:
            if "with ui.tab_panel" in lines[i-1]:
                start_idx = i
                break
                
    if start_idx == -1: return
    
    end_idx = -1
    for i, line in enumerate(lines[start_idx:]):
        if "                with ui.tab_panel(ret_tab)" in line:
            end_idx = start_idx + i
            break
            
    if end_idx == -1: return
    
    # Indent everything between start_idx and end_idx by 8 spaces
    for i in range(start_idx, end_idx):
        if lines[i].strip():
            lines[i] = "        " + lines[i]
            
    with open('purchaseui.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
if __name__ == '__main__':
    main()
