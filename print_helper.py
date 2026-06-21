"""
Print Helper Module
Provides proper print functionality across the application.
For complex reports: generates PDF and opens browser print dialog on the PDF.
For simple dialogs: opens content in a clean printable window.
"""

from nicegui import ui


def print_dialog_content(content_id=None):
    """
    JavaScript to open a new window with the dialog's content for printing.
    This bypasses Quasar dialog rendering issues during print.
    Usage: ui.run_javascript(print_dialog_content('my-content-id'))
    """
    if content_id:
        selector = f'document.getElementById("{content_id}")'
    else:
        selector = 'document.querySelector(".q-dialog__inner > div") || document.querySelector(".q-dialog")'
    return f'''
        (function() {{
            var content = {selector};
            if (!content) {{ alert("No printable content found"); return; }}
            var html = '<!DOCTYPE html><html><head><title>Print</title>';
            html += '<style>';
            html += 'body {{ font-family: Arial, sans-serif; padding: 20px; color: #000; background: #fff; }}';
            html += 'table {{ border-collapse: collapse; width: 100%; }}';
            html += 'th, td {{ border: 1px solid #333; padding: 6px 8px; text-align: left; }}';
            html += 'th {{ background: #f0f0f0; font-weight: bold; }}';
            html += '.no-print, .hide-on-print, button, .q-btn {{ display: none !important; }}';
            html += '</style></head><body>';
            html += content.innerHTML;
            html += '</body></html>';
            var win = window.open("", "_blank");
            if (!win) {{ alert("Please allow popups for this site to print"); return; }}
            win.document.write(html);
            win.document.close();
            win.focus();
            setTimeout(function() {{ win.print(); }}, 500);
        }})();
    '''


def get_print_css():
    """Return comprehensive @media print CSS that handles Quasar dialogs and dark themes."""
    return '''
<style>
@media print {
  /* Force all backgrounds to white, text to black */
  * {
    background: transparent !important;
    background-color: transparent !important;
    color: black !important;
    text-shadow: none !important;
    box-shadow: none !important;
  }
  
  body {
    background: white !important;
    color: black !important;
    font-size: 11pt;
  }
  
  /* Hide all non-printable elements */
  .hide-on-print,
  .no-print,
  .q-btn,
  button,
  .btn,
  .ribbon-nav,
  .nav-buttons,
  .header,
  .tab-buttons,
  .q-dialog__backdrop,
  .action-drawer,
  .modern-action-drawer {
    display: none !important;
  }
  
  /* Fix Quasar dialog positioning for print */
  .q-dialog {
    position: static !important;
  }
  
  .q-dialog__inner {
    position: static !important;
    max-width: 100% !important;
    width: 100% !important;
    height: auto !important;
    transform: none !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
    box-shadow: none !important;
    border: none !important;
  }
  
  .q-dialog__inner > div {
    max-width: 100% !important;
    width: 100% !important;
    background: white !important;
    color: black !important;
    box-shadow: none !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 10px !important;
  }
  
  /* Make cards and containers printable */
  .q-card,
  .q-card__section,
  .card,
  [class*="card"] {
    background: white !important;
    color: black !important;
    box-shadow: none !important;
    border: 1px solid #ccc !important;
    border-radius: 0 !important;
    padding: 8px !important;
    break-inside: avoid;
  }
  
  /* Tables */
  .q-table,
  table,
  .q-table__container {
    background: white !important;
    color: black !important;
    border-collapse: collapse !important;
    width: 100% !important;
  }
  
  .q-table th,
  .q-table td,
  table th,
  table td {
    background: white !important;
    color: black !important;
    border: 1px solid #333 !important;
    padding: 4px 6px !important;
  }
  
  .q-table thead th,
  table thead th {
    background: #f0f0f0 !important;
    font-weight: bold !important;
  }
  
  /* Fix main content area */
  .main-content,
  [class*="content"],
  .q-page {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
  }
  
  /* Ensure all content divs are visible */
  .q-item,
  .q-item__section,
  .row,
  .column,
  [class*="flex-"],
  [class*="gap-"] {
    background: transparent !important;
    color: black !important;
  }
  
  /* Force all white backgrounds on common containers */
  .bg-white,
  [class*="bg-"] {
    background: white !important;
  }
  
  /* Keep text dark on light backgrounds */
  .text-white,
  [class*="text-white"] {
    color: black !important;
  }
  
  /* Show printable content */
  .printable {
    display: block !important;
    visibility: visible !important;
  }
  
  /* Page margins */
  @page {
    margin: 15mm;
    size: auto;
  }
  
  /* Avoid page breaks inside rows */
  tr,
  .q-tr {
    break-inside: avoid;
  }
}
</style>
'''


def add_print_css():
    """Inject comprehensive @media print CSS into the page head."""
    ui.add_head_html(get_print_css())


def print_pdf(pdf_bytes, filename='document.pdf', title='Report'):
    """
    Open PDF directly in a new browser tab using the native PDF viewer.
    The user can print or download from the browser's built-in controls.
    """
    from pdf_viewer_helper import show_pdf_modal
    show_pdf_modal(pdf_bytes, filename, title)
