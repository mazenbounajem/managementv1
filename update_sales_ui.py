import sys
from datetime import datetime

file_path = r'c:\dbbackup\managementv1\salesui_aggrid_compact.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until = -1

for i in range(len(lines)):
    if i < skip_until:
        continue
    
    line = lines[i]
    
    # 1. Remove the entire Header Row (Commerce Engine / Sales Invoice)
    if 'with ui.row().classes(\'w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10 mb-2\'):' in line:
        # Search for the end of this block (which includes date and currency)
        # It ends before "# --- MIDDLE SECTION: DUAL PANEL ---"
        j = i + 1
        while j < len(lines) and '# --- MIDDLE SECTION: DUAL PANEL ---' not in lines[j]:
            j += 1
        skip_until = j
        continue

    # 2. Update Customer Information Row
    if 'with ui.row().classes(\'w-full glass p-4 rounded-3xl border border-white/10 gap-5 items-center\'):' in line:
        new_lines.append(line)
        new_lines.append('''                                            # Date
                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label(\'Date\').classes(\'text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                with ui.row().classes(\'items-center gap-2 bg-white/5 px-3 py-1 rounded-2xl border border-white/10 h-[44px]\'):
                                                    self.date_input = ui.input(value=datetime.now().strftime(\'%Y-%m-%d\')).props(\'borderless dense\').classes(\'text-white text-xs font-bold w-full\')

                                            # Currency
                                            with ui.column().classes(\'w-40 gap-1\'):
                                                ui.label(\'Currency\').classes(\'text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                self.currency_select = ui.select(
                                                    {row[0]: f\"{row[2]} {row[1]}\" for row in self.currency_rows},
                                                    value=self.default_currency_id
                                                ).props(\'borderless dense\').classes(\'bg-white/5 px-4 py-1 rounded-2xl border border-white/10 text-white text-xs font-bold w-full h-[44px]\').on(\'change\', self.on_currency_change)

                                            # Customer (Name Input Smaller)
                                            with ui.column().classes(\'w-48 gap-1\'):
                                                ui.label(\'Customer\').classes(\'text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                with ui.row().classes(\'items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner h-[44px]\'):
                                                    self.customer_input = ui.input(placeholder=\'Select...\').props(\'borderless dense dark\').classes(\'flex-1 text-white font-black text-xs\').on(\'click\', self.open_customer_dialog)

                                            # Contact
                                            with ui.column().classes(\'w-32 gap-1\'):
                                                ui.label(\'Contact\').classes(\'text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                with ui.row().classes(\'items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full h-[44px]\'):
                                                    self.phone_input = ui.input(placeholder=\'Phone\').props(\'borderless dense dark\').classes(\'flex-1 text-white font-bold text-xs\')

                                            # Payment
                                            with ui.column().classes(\'flex-1 gap-1\'):
                                                ui.label(\'Payment\').classes(\'text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4\')
                                                with ui.row().classes(\'items-center gap-2 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 h-[44px]\'):
                                                    self.payment_method = ui.radio(options=[\'Cash\', \'On Account\'], value=\'Cash\').props(\'inline dark color=purple\').classes(\'text-white text-[10px] font-black uppercase tracking-tighter\')
''')
        # Skip the old block content
        j = i + 1
        while j < len(lines) and 'self.payment_method = ui.radio' not in lines[j]:
            j += 1
        skip_until = j + 1
        continue

    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Success")
