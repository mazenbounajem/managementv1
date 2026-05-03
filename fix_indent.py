import sys

file_path = r'c:\dbbackup\managementv1\purchaseui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the specific misaligned blocks
target_barcode = """                                                    with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                        self.barcode_input = ui.input(placeholder='Barcode...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('change', self.update_product_dropdown)"""

fixed_barcode = """                                                        with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                            ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                            self.barcode_input = ui.input(placeholder='Barcode...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('change', self.update_product_dropdown)"""

target_product = """                                                    with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                        self.product_input = ui.input(placeholder='Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('click', self.open_product_dialog)"""

fixed_product = """                                                        with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                            ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                            self.product_input = ui.input(placeholder='Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('click', self.open_product_dialog)"""

text = text.replace(target_barcode, fixed_barcode)
text = text.replace(target_product, fixed_product)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed Indentation successfully")
