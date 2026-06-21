import os, glob, re

def main():
    target_dir = r"e:\managementv1"
    py_files = glob.glob(os.path.join(target_dir, "*.py"))

    for filepath in py_files:
        if 'fix_' in filepath: continue
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        changed = False

        # Pattern 1: salesui style
        if "ui.button('✕ Close', on_click=pdf_dialog.close)" in content and "pdf_bytes" in content:
            replacement = (
                "ui.button('⬇ Download PDF', on_click=lambda: ui.download(pdf_bytes, 'Report_Invoice.pdf')).classes('bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded mr-2')\n"
                "                        ui.button('✕ Close', on_click=pdf_dialog.close)"
            )
            content = content.replace("ui.button('✕ Close', on_click=pdf_dialog.close)", replacement)
            changed = True

        # Pattern 2: Reports style (accounting_helpers, reports_framework, etc)
        # Look for: ui.button('X Close', on_click=d.close)
        # However we need the bytes. In reports style, we usually have `b64` passed in.
        # So we can decode the `b64` string back to bytes.
        
        if "ui.button('X Close', on_click=d.close)" in content and "_show_pdf(b64" in content:
            replacement = (
                "import base64; ui.button('⬇ Download / Print PDF', on_click=lambda: ui.download(base64.b64decode(b64.encode('utf-8')), 'Report.pdf')).classes('bg-blue-600 hover:bg-blue-700 text-white px-4 py-1 rounded text-sm mr-2')\n"
                "                ui.button('X Close', on_click=d.close)"
            )
            content = content.replace("ui.button('X Close', on_click=d.close)", replacement)
            changed = True

        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched {os.path.basename(filepath)}")

if __name__ == '__main__':
    main()
