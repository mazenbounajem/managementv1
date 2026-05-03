import sys
from datetime import datetime

file_path = r'c:\dbbackup\managementv1\purchaseui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until = -1

for i in range(len(lines)):
    if i < skip_until:
        continue
    
    line = lines[i]
    
    # 1. Remove Procurement Engine header row
    if 'with ui.row().classes(\'w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10 mb-2\'):' in line:
        j = i + 1
        while j < len(lines) and 'with ui.row().classes(\'w-full flex-1 gap-6 overflow-hidden\'):' not in lines[j]:
            j += 1
        skip_until = j
        continue

    # 2. Update Supplier Information row to include Date and Currency
    if 'with ui.row().classes(\'w-full glass p-4 rounded-3xl border border-white/10 gap-5 items-center\'):' in line:
        new_lines.append(line)
        new_lines.append('''                                            # Date
                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label(\'Date\').classes(\'text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                with ui.row().classes(\'items-center gap-2 bg-white/5 px-3 py-1 rounded-xl border border-white/10 h-[36px]\'):
                                                    self.date_input = ui.input(value=datetime.now().strftime(\'%Y-%m-%d\')).props(\'borderless dense\').classes(\'text-white text-xs font-bold w-full\')

                                            # Currency
                                            with ui.column().classes(\'w-40 gap-1\'):
                                                ui.label(\'Currency\').classes(\'text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                self.currency_select = ui.select(
                                                    {row[0]: f\"{row[2]} {row[1]}\" for row in self.currency_rows},
                                                    value=self.default_currency_id
                                                ).props(\'borderless dense\').classes(\'bg-white/5 px-4 py-1 rounded-xl border border-white/10 text-white text-xs font-bold w-full h-[36px]\').on(\'change\', self.on_currency_change)

                                            # Supplier
                                            with ui.column().classes(\'w-48 gap-1\'):
                                                ui.label(\'Supplier\').classes(\'text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                with ui.row().classes(\'items-center gap-3 bg-white/5 px-3 py-1.5 rounded-xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner h-[36px]\'):
                                                    self.supplier_input = ui.input(placeholder=\'Select...\').props(\'borderless dense dark\').classes(\'flex-1 text-white font-black text-xs\').on(\'click\', self.open_supplier_dialog)
''')
        # Skip the old supplier input block
        j = i + 1
        while j < len(lines) and 'with ui.column().classes(\'w-48 gap-1\'):' not in lines[j]:
            j += 1
        skip_until = j
        continue
    
    # 3. Apply compaction (p-4 -> p-2, 3xl -> 2xl, labels 9px -> 8px, buttons h-16 -> h-12)
    line = line.replace("p-4 rounded-3xl", "p-2 rounded-2xl")
    line = line.replace("gap-4", "gap-2")
    line = line.replace("gap-5", "gap-3")
    line = line.replace("gap-6", "gap-3")
    line = line.replace("px-4 py-2 rounded-2xl", "px-3 py-1 rounded-xl")
    line = line.replace("text-[9px]", "text-[8px]")
    line = line.replace("h-[44px]", "h-[36px]")
    line = line.replace("button_class='h-16'", "button_class='h-12'")
    
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Updated Purchase UI successfully")
