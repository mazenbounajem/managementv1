import sys

file_path = r'c:\dbbackup\managementv1\purchaseui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until = -1

for i in range(len(lines)):
    if i < skip_until:
        continue
    
    line = lines[i]
    
    # Identify the break between panels
    if "self.payment_method = ui.radio(options=['Cash', 'On Account']" in line:
        new_lines.append(line)
        # Check if the next few lines contain the closing of the row and opening of the next
        j = i + 1
        found_merge_point = False
        while j < i + 10 and j < len(lines):
            if "with ui.row().classes('w-full glass p-2 rounded-2xl border border-white/10 gap-3 items-end" in lines[j]:
                found_merge_point = True
                break
            j += 1
        
        if found_merge_point:
            # We are inserting a separator or just keeping it together
            new_lines.append("\n")
            new_lines.append("                                            # --- Inline Product Entry (Merged Level) ---\n")
            new_lines.append("                                            with ui.row().classes('items-end gap-2 px-2 py-1 bg-white/5 rounded-xl border border-white/10 ml-auto'):\n")
            skip_until = j + 1
            continue
            
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Merged rows successfully")
