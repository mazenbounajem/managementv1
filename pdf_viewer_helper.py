"""
Unified PDF Viewer Helper for NiceGUI
Provides a reusable modal dialog for viewing, downloading, and printing PDFs
"""

from nicegui import ui
import base64


def show_pdf_modal(pdf_bytes, filename='document.pdf', title='Document Preview'):
    """
    Open PDF directly in a new browser tab using the native PDF viewer.
    The user can print or download from the browser's built-in controls.

    Args:
        pdf_bytes: Raw PDF bytes from ReportLab or similar
        filename: Filename for download (default: 'document.pdf')
        title: Dialog title (default: 'Document Preview')
    """
    try:
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        ui.run_javascript(f'''
            (function() {{
                var w = window.open("", "_blank");
                if (!w) {{ alert("Please allow popups to view the PDF"); return; }}
                w.document.write(
                    '<embed src="data:application/pdf;base64,{pdf_b64}" ' +
                    'type="application/pdf" width="100%" height="100%" ' +
                    'style="position:fixed;top:0;left:0;width:100%;height:100%;border:none;">' +
                    '</embed>'
                );
                w.document.close();
                w.document.title = "{title}";
            }})();
        ''')
    except Exception as e:
        ui.notify(f'Error displaying PDF: {str(e)}', color='negative', icon='error')
        print(f'PDF viewer error: {str(e)}')


def generate_and_show_pdf(invoice_number, invoice_data, subtotal, discount_percent, 
                         discount_amount, final_total, company_name, currency_symbol='$', 
                         title='Invoice Preview'):
    """
    Generate a PDF using ReportLab and immediately show it in the modal viewer.

    Args:
        invoice_number: Invoice/reference number
        invoice_data: List of dict items with 'Barcode', 'Product', 'Quantity', 'Price', 'Discount', 'Subtotal'
        subtotal: Subtotal amount
        discount_percent: Discount percentage
        discount_amount: Discount amount
        final_total: Final total after discounts
        company_name: Company name for header
        currency_symbol: Currency symbol (default: '$')
        title: Modal title (default: 'Invoice Preview')
    """
    try:
        import base64
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO

        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            leftMargin=20, 
            rightMargin=20,
            topMargin=30, 
            bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(f"{company_name} - Invoice", styles['Heading1']))
        elements.append(Spacer(1, 12))

        # Invoice details
        elements.append(Paragraph(
            f"Invoice #: {invoice_number}<br/>Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 12))

        # Items table
        table_data = [['Barcode', 'Product', 'Quantity', 'Price', 'Discount', 'Subtotal']]
        for item in invoice_data:
            table_data.append([
                item.get('Barcode', ''),
                item.get('Product', ''),
                item.get('Quantity', ''),
                item.get('Price', ''),
                item.get('Discount', ''),
                item.get('Subtotal', '')
            ])

        page_width, page_height = letter
        available_width = page_width - 40
        col_widths = [available_width * 0.15, available_width * 0.25, available_width * 0.15, 
                      available_width * 0.15, available_width * 0.15, available_width * 0.15]

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # Totals section
        totals_data = []
        if discount_percent > 0 or discount_amount > 0:
            totals_data.append(['Subtotal:', f"{currency_symbol}{subtotal:.2f}"])
            if discount_percent > 0:
                totals_data.append([f'Discount ({discount_percent}%):', f"-{currency_symbol}{subtotal * discount_percent / 100:.2f}"])
            if discount_amount > 0:
                totals_data.append(['Discount Amount:', f"-{currency_symbol}{discount_amount:.2f}"])

        totals_data.append(['Grand Total:', f"{currency_symbol}{final_total:.2f}"])

        totals_table = Table(totals_data, colWidths=[available_width * 0.7, available_width * 0.3])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (-1, -1), (-1, -1), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(totals_table)

        # Build PDF
        doc.build(elements)

        # Get bytes and show in modal
        pdf_bytes = buffer.getvalue()
        buffer.close()

        show_pdf_modal(pdf_bytes, f'Invoice_{invoice_number}.pdf', title)

    except Exception as e:
        ui.notify(f'Error generating PDF: {str(e)}', color='negative')
        print(f'PDF generation error: {str(e)}')
