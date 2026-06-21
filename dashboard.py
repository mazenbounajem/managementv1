# select different interpreter python 13 global
import tkinter as tk
from tkinter import PhotoImage, Frame, RIDGE, Toplevel, TOP
import ttkbootstrap as tb
from ttkbootstrap import ttk
from customer import CustomerClass

class Dashboard:
     def __init__(self,root, title='',themename='superhero', iconphoto='.images/conphoto.png', size=None, position=None, minsize=None, maxsize=None, resizable=None, hdpi=True, scaling=None, transient=None, overrideredirect=False, alpha=1.0):
        self.root=root
        self.style = tb.Style(themename)
        self.root.title('Dashboard')
        self.root.iconbitmap('./images/conphoto.png')
        self.root.geometry("1800x1000+0+0")
        
        self.frame1()
        #==============================design====================
     def frame1(self,maxsize=None):

            new_frame = Frame(self.root, bd=1, relief=RIDGE)
            new_frame.grid(row=0, column=0, sticky="ew")
            self.root.grid_rowconfigure(0, weight=0)
            self.root.grid_columnconfigure(0, weight=1)

            # Configure grid for new_frame
            new_frame.grid_columnconfigure(tuple(range(14)), weight=1)

            self.icon_exit = PhotoImage(file="images/exit.png")
            btn_logout = ttk.Button(new_frame, text='Logout', image=self.icon_exit, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_logout.grid(row=0, column=13, sticky="e", padx=5, pady=5)

            self.icon_sal = PhotoImage(file="images/sales.png")
            btn_billing = ttk.Button(new_frame, text="Bill", image=self.icon_sal, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'), command=self.open_invoice)
            btn_billing.grid(row=0, column=0, sticky="ew", padx=2, pady=5)

            self.icon_side = PhotoImage(file="images/employee.png")
            btn_Employee = ttk.Button(new_frame, text="Employee", image=self.icon_side, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_Employee.grid(row=0, column=1, sticky="ew", padx=2, pady=5)

            self.icon_supp = PhotoImage(file="images/supplier.png")
            btn_supplier = ttk.Button(new_frame, text="Supplier", image=self.icon_supp, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_supplier.grid(row=0, column=2, sticky="ew", padx=2, pady=5)

            self.icon_cat = PhotoImage(file="images/category.png")
            btn_category = ttk.Button(new_frame, text="Category", image=self.icon_cat, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'), command=self.open_category)
            btn_category.grid(row=0, column=3, sticky="ew", padx=2, pady=5)

            self.icon_products = PhotoImage(file="images/products.png")
            btn_products = ttk.Button(new_frame, text="Products", image=self.icon_products, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'), command=self.open_products)
            btn_products.grid(row=0, column=4, sticky="ew", padx=2, pady=5)

            btn_sales = ttk.Button(new_frame, text="Sales", image=self.icon_sal, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_sales.grid(row=0, column=5, sticky="ew", padx=2, pady=5)

            self.icon_purchase = PhotoImage(file="images/purchase.png")
            btn_purchase1 = ttk.Button(new_frame, text="Purchase", image=self.icon_purchase, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_purchase1.grid(row=0, column=6, sticky="ew", padx=2, pady=5)

            self.icon_customer = PhotoImage(file="images/customer.png")
            btn_customer = ttk.Button(new_frame, text="Customer", command=self.customer, image=self.icon_customer, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_customer.grid(row=0, column=7, sticky="ew", padx=2, pady=5)

            self.icon_reports = PhotoImage(file="images/reports.png")
            btn_report = ttk.Button(new_frame, text="Report", image=self.icon_reports, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_report.grid(row=0, column=8, sticky="ew", padx=2, pady=5)

            self.icon_customerpayment = PhotoImage(file="images/customerrecipt.png")
            btn_customerpayment = ttk.Button(new_frame, text="CustomerReceipt", image=self.icon_customerpayment, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_customerpayment.grid(row=0, column=9, sticky="ew", padx=2, pady=5)

            self.icon_consignment = PhotoImage(file="images/consignment.png")
            btn_consignment = ttk.Button(new_frame, text="Consignment", image=self.icon_consignment, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_consignment.grid(row=0, column=10, sticky="ew", padx=2, pady=5)

            self.icon_expenses = PhotoImage(file="images/expenses.png")
            btn_expenses = ttk.Button(new_frame, text="Expenses", image=self.icon_expenses, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_expenses.grid(row=0, column=11, sticky="ew", padx=2, pady=5)

            self.icon_supplierpayment = PhotoImage(file="images/supplierpayment.png")
            btn_payment = ttk.Button(new_frame, text="Supplier Payment", image=self.icon_supplierpayment, compound=TOP, bootstyle=('SUCCESS', 'OUTLINE'))
            btn_payment.grid(row=0, column=12, sticky="ew", padx=2, pady=5)

     def customer(self):
        
        self.new_win =Toplevel(self.root)
        self.new_obj=CustomerClass(self.new_win)

     def open_category(self):
        self.new_win = Toplevel(self.root)
        from category import CategoryClass
        self.new_obj = CategoryClass(self.new_win, self.style.colors)

     def open_supplier(self):
        self.new_win = Toplevel(self.root)
        from supplier import SupplierClass
        self.new_obj = SupplierClass(self.new_win)

     def open_products(self):
        self.new_win = Toplevel(self.root)
        from products import ProductsCass
        self.new_obj = ProductsCass(self.new_win)

     def open_invoice(self):
        self.new_win = Toplevel(self.root)
        for widget in self.new_win.winfo_children():
            widget.destroy()
        from invoice import InvoiceClass
        self.new_obj = InvoiceClass(self.new_win)

if __name__ == "__main__":
    root = tk.Tk()
    app = Dashboard(root)
    root.mainloop()

