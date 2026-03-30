import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
from decimal import Decimal
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from connection import connection

class POSSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Point of Sale System")
        self.root.geometry("1400x800")
        self.root.configure(bg='#2b3e50')
        
        # Initialize variables
        self.cart_items = []
        self.total_amount = Decimal('0.00')
        self.vat_rate = Decimal('0.11')  # 11% VAT
        
        self.setup_ui()
        self.load_customers()
        self.load_products()
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main container
        main_frame = tb.Frame(self.root, bootstyle="dark")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for transaction details
        self.create_transaction_frame(main_frame)
        
        # Middle frame for product entry
        self.create_product_entry_frame(main_frame)
        
        # Bottom frame for cart and totals
        self.create_cart_frame(main_frame)
        
        # Button frame
        self.create_button_frame(main_frame)
        
    def create_transaction_frame(self, parent):
        """Create transaction details frame"""
        trans_frame = tb.LabelFrame(parent, text="Transaction Details", bootstyle="info")
        trans_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Date
        tb.Label(trans_frame, text="Date:", bootstyle="info").grid(row=0, column=0, padx=5, pady=5)
        self.date_entry = tb.Entry(trans_frame, bootstyle="info", width=12)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')
        
        # Customer
        tb.Label(trans_frame, text="Customer:", bootstyle="info").grid(row=0, column=2, padx=5, pady=5)
        self.customer_var = tk.StringVar()
        self.customer_combo = tb.Combobox(trans_frame, textvariable=self.customer_var, 
                                         bootstyle="info", width=30)
        self.customer_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # Currency
        tb.Label(trans_frame, text="Currency:", bootstyle="info").grid(row=0, column=4, padx=5, pady=5)
        self.currency_var = tk.StringVar(value="USD")
        self.currency_combo = tb.Combobox(trans_frame, textvariable=self.currency_var, 
                                         values=["USD", "LBP"], bootstyle="info", width=10)
        self.currency_combo.grid(row=0, column=5, padx=5, pady=5)
        
        # Invoice Number
        tb.Label(trans_frame, text="Invoice #:", bootstyle="info").grid(row=0, column=6, padx=5, pady=5)
        self.invoice_entry = tb.Entry(trans_frame, bootstyle="info", width=15)
        self.invoice_entry.insert(0, self.generate_invoice_number())
        self.invoice_entry.grid(row=0, column=7, padx=5, pady=5)
        self.invoice_entry.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')
        
    def create_product_entry_frame(self, parent):
        """Create product entry frame"""
        entry_frame = tb.LabelFrame(parent, text="Add Product", bootstyle="info")
        entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Barcode
        tb.Label(entry_frame, text="Barcode:", bootstyle="info").grid(row=0, column=0, padx=5, pady=5)
        self.barcode_entry = tb.Entry(entry_frame, bootstyle="info", width=15)
        self.barcode_entry.grid(row=0, column=1, padx=5, pady=5)
        self.barcode_entry.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')
        self.barcode_entry.bind('<Return>', self.lookup_product)
        
        # Product Name
        tb.Label(entry_frame, text="Product:", bootstyle="info").grid(row=0, column=2, padx=5, pady=5)
        self.product_var = tk.StringVar()
        self.product_combo = tb.Combobox(entry_frame, textvariable=self.product_var, 
                                       bootstyle="info", width=30)
        self.product_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # Quantity
        tb.Label(entry_frame, text="Qty:", bootstyle="info").grid(row=0, column=4, padx=5, pady=5)
        self.qty_entry = tb.Entry(entry_frame, bootstyle="info", width=8)
        self.qty_entry.insert(0, "1")
        self.qty_entry.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')
        self.qty_entry.grid(row=0, column=5, padx=5, pady=5)
        
        # Unit Price
        tb.Label(entry_frame, text="Price:", bootstyle="info").grid(row=0, column=6, padx=5, pady=5)
        self.price_entry = tb.Entry(entry_frame, bootstyle="info", width=10)
        self.price_entry.grid(row=0, column=7, padx=5, pady=5)
        self.price_entry.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')
        
        # VAT
        self.vat_var = tk.BooleanVar()
        self.vat_check = tb.Checkbutton(entry_frame, text="VAT", variable=self.vat_var, 
                                       bootstyle="info")
        self.vat_check.grid(row=0, column=8, padx=5, pady=5)
        
        # Add Button
        self.add_btn = tb.Button(entry_frame, text="Add to Cart", command=self.add_to_cart, 
                               bootstyle="success")
        self.add_btn.grid(row=0, column=9, padx=10, pady=5)
        
    def create_cart_frame(self, parent):
        """Create cart display frame"""
        cart_frame = tb.Frame(parent)
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cart Treeview
        columns = ('barcode', 'product', 'vat', 'quantity', 'price', 'total')
        self.cart_tree = tb.Treeview(cart_frame, columns=columns, show='headings', 
                                   height=15, bootstyle="info")
        
        # Define headings
        self.cart_tree.heading('barcode', text='Barcode')
        self.cart_tree.heading('product', text='Product Name')
        self.cart_tree.heading('vat', text='VAT')
        self.cart_tree.heading('quantity', text='Qty')
        self.cart_tree.heading('price', text='Unit Price')
        self.cart_tree.heading('total', text='Total')
        
        # Configure column widths
        self.cart_tree.column('barcode', width=100)
        self.cart_tree.column('product', width=300)
        self.cart_tree.column('vat', width=80)
        self.cart_tree.column('quantity', width=80)
        self.cart_tree.column('price', width=100)
        self.cart_tree.column('total', width=120)
        
        # Add scrollbar
        scrollbar = tb.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)
        
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to remove item
        self.cart_tree.bind('<Double-1>', self.remove_item)
        
        # Totals frame
        totals_frame = tb.Frame(cart_frame)
        totals_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Subtotal
        tb.Label(totals_frame, text="Subtotal:", font=('Arial', 12), 
                bootstyle="info").grid(row=0, column=0, padx=5, pady=5)
        self.subtotal_label = tb.Label(totals_frame, text="0.00", font=('Arial', 12), 
                                     bootstyle="info")
        self.subtotal_label.grid(row=0, column=1, padx=5, pady=5)
        
        # VAT
        tb.Label(totals_frame, text="VAT (11%):", font=('Arial', 12), 
                bootstyle="info").grid(row=0, column=2, padx=5, pady=5)
        self.vat_label = tb.Label(totals_frame, text="0.00", font=('Arial', 12), 
                                bootstyle="info")
        self.vat_label.grid(row=0, column=3, padx=5, pady=5)
        
        # Total
        tb.Label(totals_frame, text="Total:", font=('Arial', 14, 'bold'), 
                bootstyle="info").grid(row=0, column=4, padx=5, pady=5)
        self.total_label = tb.Label(totals_frame, text="0.00", font=('Arial', 14, 'bold'), 
                                  bootstyle="info")
        self.total_label.grid(row=0, column=5, padx=5, pady=5)
        
    def create_button_frame(self, parent):
        """Create action buttons frame"""
        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tb.Button(btn_frame, text="Clear Cart", command=self.clear_cart, 
                 bootstyle="warning").pack(side=tk.LEFT, padx=5)
        
        tb.Button(btn_frame, text="Save & Print", command=self.save_sale, 
                 bootstyle="success").pack(side=tk.RIGHT, padx=5)
        
        tb.Button(btn_frame, text="Hold Sale", command=self.hold_sale, 
                 bootstyle="secondary").pack(side=tk.RIGHT, padx=5)
        
    def load_customers(self):
        """Load customers from database"""
        try:
            cursor = connection.contogetrows
            customers = []
            cursor('SELECT id, customerName FROM customer ORDER BY customerName', customers)
            customer_list = [f"{row[1]}" for row in customers[0]]
            customer_list.insert(0, "Cash Client")
            self.customer_combo['values'] = customer_list
            self.customer_combo.current(0)
        except Exception as e:
            print(f"Error loading customers: {e}")
            self.customer_combo['values'] = ["Cash Client"]
            
    def load_products(self):
        """Load products from database"""
        try:
            cursor = connection.contogetrows
            products = []
            cursor('SELECT id, productName, barcode, price FROM products ORDER BY productName', products)
            self.products_data = products[0]
            product_list = [f"{row[1]}" for row in products[0]]
            self.product_combo['values'] = product_list
        except Exception as e:
            print(f"Error loading products: {e}")
            
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        try:
            cursor = connection.contogetrows
            result = []
            cursor("SELECT COUNT(*) FROM sales", result)
            count = result[0][0][0] if result and result[0] else 0
            return f"INV-{datetime.now().strftime('%Y%m%d')}-{count + 1:04d}"
        except:
            return f"INV-{datetime.now().strftime('%Y%m%d')}-0001"
            
    def lookup_product(self, event=None):
        """Lookup product by barcode"""
        barcode = self.barcode_entry.get()
        if barcode:
            for product in self.products_data:
                if str(product[2]) == barcode:
                    self.product_var.set(product[1])
                    self.price_entry.delete(0, tk.END)
                    self.price_entry.insert(0, str(product[3]))
                    self.qty_entry.focus()
                    break
                    
    def add_to_cart(self):
        """Add product to cart"""
        try:
            product_name = self.product_var.get()
            barcode = self.barcode_entry.get()
            qty = int(self.qty_entry.get())
            price = Decimal(self.price_entry.get())
            has_vat = self.vat_var.get()
            
            if not product_name or qty <= 0 or price <= 0:
                messagebox.showerror("Error", "Please enter valid product details")
                return
                
            # Calculate totals
            item_total = qty * price
            if has_vat:
                vat_amount = item_total * self.vat_rate
                item_total += vat_amount
                
            # Add to cart
            self.cart_items.append({
                'barcode': barcode,
                'product': product_name,
                'vat': 'Yes' if has_vat else 'No',
                'quantity': qty,
                'price': price,
                'total': item_total
            })
            
            # Update cart display
            self.update_cart_display()
            self.clear_product_entry()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
            
    def update_cart_display(self):
        """Update cart treeview and totals"""
        # Clear existing items
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
            
        # Add items to tree
        subtotal = Decimal('0.00')
        vat_total = Decimal('0.00')
        
        for item in self.cart_items:
            self.cart_tree.insert('', 'end', values=(
                item['barcode'],
                item['product'],
                item['vat'],
                item['quantity'],
                f"{item['price']:.2f}",
                f"{item['total']:.2f}"
            ))
            subtotal += item['quantity'] * item['price']
            if item['vat'] == 'Yes':
                vat_total += item['quantity'] * item['price'] * self.vat_rate
                
        # Update totals
        total = subtotal + vat_total
        self.subtotal_label.config(text=f"{subtotal:.2f}")
        self.vat_label.config(text=f"{vat_total:.2f}")
        self.total_label.config(text=f"{total:.2f}")
        
    def clear_product_entry(self):
        """Clear product entry fields"""
        self.barcode_entry.delete(0, tk.END)
        self.product_var.set('')
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, '1')
        self.price_entry.delete(0, tk.END)
        self.vat_var.set(False)
        
    def remove_item(self, event):
        """Remove item from cart"""
        selected = self.cart_tree.selection()
        if selected:
            index = self.cart_tree.index(selected[0])
            del self.cart_items[index]
            self.update_cart_display()
            
    def clear_cart(self):
        """Clear all items from cart"""
        self.cart_items.clear()
        self.update_cart_display()
        
    def save_sale(self):
        """Save sale to database"""
        if not self.cart_items:
            messagebox.showerror("Error", "No items in cart")
            return
            
        try:
            customer = self.customer_var.get()
            currency = self.currency_var.get()
            total = Decimal(self.total_label.cget('text'))
            
            # Insert sale record
            cursor = connection.insertingtodatabase
            sale_sql = """
                INSERT INTO sales (date, customer, total_amount, currency, invoice_number)
                VALUES (?, ?, ?, ?, ?)
            """
            sale_values = (
                self.date_entry.get(),
                customer,
                float(total),
                currency,
                self.invoice_entry.get()
            )
            cursor(sale_sql, sale_values)
            
            # Get sale ID
            cursor2 = connection.contogetrows
            sale_id = cursor2("SELECT MAX(id) FROM sales")[0][0]
            
            # Insert sale items
            for item in self.cart_items:
                item_sql = """
                    INSERT INTO sale_items (sale_id, barcode, product_name, quantity, price, vat, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                item_values = (
                    sale_id,
                    item['barcode'],
                    item['product'],
                    item['quantity'],
                    float(item['price']),
                    1 if item['vat'] == 'Yes' else 0,
                    float(item['total'])
                )
                cursor(item_sql, item_values)
                
            messagebox.showinfo("Success", "Sale completed successfully!")
            self.clear_cart()
            self.invoice_entry.delete(0, tk.END)
            self.invoice_entry.insert(0, self.generate_invoice_number())
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving sale: {str(e)}")
            
    def hold_sale(self):
        """Hold sale for later"""
        messagebox.showinfo("Hold", "Sale held for later processing")
        
    def run(self):
        """Run the POS system"""
        self.root.mainloop()

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = POSSystem(root)
    app.run()
