import cairo
from io import BytesIO
import os
from datetime import datetime

class CairoInvoiceGenerator:
    def __init__(self):
        self.width, self.height = 595, 842  # A4 size in points
        self.margin = 50
        self.line_height = 20
        self.current_y = 100
        
    def create_invoice_pdf(self, invoice_data):
        """Generate PDF invoice using Cairo"""
        # Create PDF surface
        buffer = BytesIO()
        surface = cairo.PDFSurface(buffer, self.width, self.height)
        ctx = cairo.Context(surface)
        
        # Set background
        ctx.set_source_rgb(1, 1, 1)  # White background
        ctx.paint()
        
        # Draw invoice
        self.draw_header(ctx, invoice_data)
        self.draw_invoice_details(ctx, invoice_data)
        self.draw_items_table(ctx, invoice_data['items'])
        self.draw_totals(ctx, invoice_data)
        self.draw_footer(ctx)
        
        # Finish
        surface.finish()
        buffer.seek(0)
        
        return buffer
    
    def draw_header(self, ctx, invoice_data):
        """Draw company header"""
        ctx.set_source_rgb(0.2, 0.2, 0.8)  # Blue color
        ctx.set_font_size(24)
        ctx.move_to(self.margin, 50)
        ctx.show_text("INVOICE")
        
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_font_size(12)
        ctx.move_to(self.margin, 80)
        ctx.show_text("Your Company Name")
        ctx.move_to(self.margin, 100)
        ctx.show_text("123 Business Street")
        ctx.move_to(self.margin, 120)
        ctx.show_text("City, State 12345")
        ctx.move_to(self.margin, 140)
        ctx.show_text("Phone: (555) 123-4567")
        
    def draw_invoice_details(self, ctx, invoice_data):
        """Draw invoice details section"""
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_font_size(12)
        
        # Invoice details
        x = self.width - 200
        y = 100
        
        ctx.move_to(x, y)
        ctx.show_text(f"Invoice #: {invoice_data['invoice_number']}")
        ctx.move_to(x, y + 20)
        ctx.show_text(f"Date: {invoice_data['date']}")
        ctx.move_to(x, y + 40)
        ctx.show_text(f"Customer: {invoice_data['customer_name']}")
        
        # Customer details
        ctx.move_to(self.margin, 200)
        ctx.show_text("Bill To:")
        ctx.move_to(self.margin, 220)
        ctx.show_text(invoice_data['customer_name'])
        if invoice_data.get('customer_phone'):
            ctx.move_to(self.margin, 240)
            ctx.show_text(f"Phone: {invoice_data['customer_phone']}")
            
    def draw_items_table(self, ctx, items):
        """Draw items table"""
        # Table headers
        y = 280
        ctx.set_source_rgb(0.8, 0.8, 0.8)  # Light gray
        ctx.rectangle(self.margin, y - 15, self.width - 2 * self.margin, 25)
        ctx.fill()
        
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_font_size(10)
        ctx.move_to(self.margin + 5, y)
        ctx.show_text("Item")
        ctx.move_to(self.margin + 200, y)
        ctx.show_text("Qty")
        ctx.move_to(self.margin + 250, y)
        ctx.show_text("Price")
        ctx.move_to(self.margin + 320, y)
        ctx.show_text("Discount")
        ctx.move_to(self.margin + 400, y)
        ctx.show_text("Subtotal")
        
        # Items
        y += 30
        ctx.set_source_rgb(0, 0, 0)
        for item in items:
            ctx.move_to(self.margin + 5, y)
            ctx.show_text(str(item['product']))
            ctx.move_to(self.margin + 200, y)
            ctx.show_text(str(item['quantity']))
            ctx.move_to(self.margin + 250, y)
            ctx.show_text(f"${item['price']:.2f}")
            ctx.move_to(self.margin + 320, y)
            ctx.show_text(f"{item['discount']}%")
            ctx.move_to(self.margin + 400, y)
            ctx.show_text(f"${item['subtotal']:.2f}")
            y += 25
            
    def draw_totals(self, ctx, invoice_data):
        """Draw totals section"""
        y = 400 + len(invoice_data['items']) * 25
        
        # Line
        ctx.set_source_rgb(0.5, 0.5, 0.5)
        ctx.set_line_width(1)
        ctx.move_to(self.margin, y)
        ctx.line_to(self.width - self.margin, y)
        ctx.stroke()
        
        y += 20
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_font_size(12)
        
        # Subtotal
        ctx.move_to(self.width - 200, y)
        ctx.show_text("Subtotal:")
        ctx.move_to(self.width - 100, y)
        ctx.show_text(f"${invoice_data['subtotal']:.2f}")
        
        # Total
        y += 25
        ctx.set_font_size(14)
        ctx.move_to(self.width - 200, y)
        ctx.show_text("Total:")
        ctx.move_to(self.width - 100, y)
        ctx.show_text(f"${invoice_data['total_amount']:.2f}")
        
    def draw_footer(self, ctx):
        """Draw footer"""
        y = self.height - 100
        ctx.set_source_rgb(0.5, 0.5, 0.5)
        ctx.set_font_size(10)
        ctx.move_to(self.margin, y)
        ctx.show_text("Thank you for your business!")
        ctx.move_to(self.margin, y + 15)
        ctx.show_text("Payment terms: Net 30 days")
        ctx.move_to(self.margin, y + 30)
        ctx.show_text("For questions, contact us at info@yourcompany.com")

# Integration function for salesui_aggrid_compact.py
def generate_sales_invoice_pdf(rows, customer_name, invoice_number, total_amount):
    """Generate PDF from sales data"""
    invoice_data = {
        'invoice_number': invoice_number,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'customer_name': customer_name,
        'customer_phone': '',
        'total_amount': total_amount,
        'subtotal': total_amount,
        'items': rows
    }
    
    generator = CairoInvoiceGenerator()
    pdf_buffer = generator.create_invoice_pdf(invoice_data)
    
    return pdf_buffer
