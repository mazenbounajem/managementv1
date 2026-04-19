def revert(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(lines):
        if "with ui.tabs().classes" in line:
            start_idx = i
            break
            
    if start_idx == -1: return False
    
    # We find where we added the 'with ui.element('div')'
    # Actually, we can just find 'with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):'
    
    # We want to remove from 'with ui.tabs()' up up to 'with ui.tab_panels(...)'
    # The original starts with: "        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):"
    
    # Since there are lots of messes, let's just use regex to re-dedent lines between the tab wrapper,
    # or simpler: Just delete the tab injection lines!
    
    new_lines = []
    ignoring = False
    for i in range(len(lines)):
        line = lines[i]
        
        # Start ignoring when we see flex flex-col injected
        if "with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden flex flex-col'):" in line:
            ignoring = True
            continue
            
        if ignoring:
            if "with ui.tab_panels" in line: continue
            if "with ui.tab_panel(op_tab)" in line: continue
            if "op_tab = ui.tab" in line: continue
            if "ret_tab = ui.tab" in line: continue
            if "with ui.tabs()" in line: continue
            
            if "with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):" in line:
                ignoring = False
                new_lines.append("        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):\n")
                continue
                
        # Handle the return tab at the bottom
        if "with ui.tab_panel(ret_tab)" in line:
            break # Stop taking lines
            
        if not ignoring:
            # Check if this line is indented due to Python auto indentation of previous messes
            # Revert + 8 spaces
            # Since the user or script indented the block after "with ui.element" we need to un-indent
            pass
            
    return new_lines

# Since auto-unindent is hard if we don't know exact levels, let's write a targeted script.
