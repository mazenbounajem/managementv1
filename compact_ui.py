import sys

file_path = r'c:\dbbackup\managementv1\salesui_aggrid_compact.py'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Main container padding and gap
text = text.replace("with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):", 
                    "with ui.column().classes('flex-1 h-full p-2 gap-2 relative overflow-hidden'):")

# 2. Main content row gap
text = text.replace("with ui.row().classes('w-full flex-1 gap-6 overflow-hidden'):", 
                    "with ui.row().classes('w-full flex-1 gap-3 overflow-hidden'):")

# 3. Customer row padding and height
text = text.replace("with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 gap-5 items-center'):", 
                    "with ui.row().classes('w-full glass p-2 rounded-2xl border border-white/10 gap-3 items-center'):")

# 4. Product entry row padding and height
text = text.replace("with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 gap-3 items-end mt-2'):", 
                    "with ui.row().classes('w-full glass p-2 rounded-2xl border border-white/10 gap-2 items-end mt-1'):")

# 5. Summary/Totals row
text = text.replace("with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 items-center justify-between'):", 
                    "with ui.row().classes('w-full glass p-2 rounded-2xl border border-white/10 items-center justify-between'):")

# 6. Global style refinements
text = text.replace("text-[9px]", "text-[8px]")
text = text.replace("px-4 py-2 rounded-2xl", "px-3 py-1 rounded-xl")
text = text.replace("h-[44px]", "h-[36px]")

# 7. Action bar scaling (making it slightly smaller)
text = text.replace("button_class='h-16'", "button_class='h-12'")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Compacted successfully")
