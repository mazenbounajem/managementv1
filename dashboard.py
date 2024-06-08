# select different interpreter python 13 global
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.style import *
from tkinter import *
from customer import CustomerClass
from tkinter import PhotoImage
class Dashboard:
     def __init__(self,root, title='',themename='superhero', iconphoto='.images/conphoto.png', size=None, position=None, minsize=None, maxsize=None, resizable=None, hdpi=True, scaling=None, transient=None, overrideredirect=False, alpha=1.0):
        self.root=root
        self.root.title('Dashboard')
        self.root.iconbitmap('./images/conphoto.png')
        self.root.geometry("1800x1000+0+0")
        
        self.frame1()
        #==============================design====================
     def frame1(self,maxsize=None):

            new_frame = Frame(self.root, bd=1,relief=RIDGE)
            new_frame.place(x=0,y=0,width=maxsize,height=100)

            self.icon_exit=PhotoImage(file="images/exit.png")
            btn_logout = ttk.Button(new_frame, text='logout',image=self.icon_exit,compound=TOP,bootstyle=('SUCCESS, OUTLINE'))
            btn_logout.pack(side=RIGHT)
            
            self.icon_sal=PhotoImage(file="images/sales.png")
            btn_billing=ttk.Button(new_frame,text="Bill",image=self.icon_sal,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            
            self.icon_side=PhotoImage(file="images/employee.png")
            btn_Employee=ttk.Button(new_frame,text="Employee",image=self.icon_side,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            
            self.icon_supp=PhotoImage(file="images/supplier.png")
            btn_supplier=ttk.Button(new_frame,text="Supplier",image=self.icon_supp,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            self.icon_cat=PhotoImage(file="images/category.png")
            btn_category=ttk.Button(new_frame,text="Category",image=self.icon_cat,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            self.icon_products=PhotoImage(file="images/products.png")
            btn_products=ttk.Button(new_frame,text="Products",image=self.icon_products,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            
            
            #self.icon_sal=PhotoImage(file="images/sales.png")
            btn_sales=ttk.Button(new_frame,text="Sales",image=self.icon_sal,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            self.icon_purchase=PhotoImage(file="images/purchase.png")
            btn_purchase1=ttk.Button(new_frame,text="Purchase",image=self.icon_purchase,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)

            self.icon_customer=PhotoImage(file="images/customer.png")
            btn_customer=ttk.Button(new_frame,text="Customer",command=self.customer,image=self.icon_customer,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)

            self.icon_reports=PhotoImage(file="images/reports.png")
            btn_report=ttk.Button(new_frame,text="Report",image=self.icon_reports,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)
            
            self.icon_customerpayment=PhotoImage(file="images/customerrecipt.png")
            btn_customerpayment=ttk.Button(new_frame,text="CustomerRecipt",image=self.icon_customerpayment,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)

            self.icon_consignment=PhotoImage(file="images/consignment.png")
            btn_consignment=ttk.Button(new_frame,text="consignment",image=self.icon_consignment,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)

            self.icon_expenses=PhotoImage(file="images/expenses.png")
            btn_expenses=ttk.Button(new_frame,text="expenses",image=self.icon_expenses,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)

            self.icon_supplierpayment=PhotoImage(file="images/supplierpayment.png")
            btn_payment=ttk.Button(new_frame,text="Supplier Payment",image=self.icon_supplierpayment,compound=TOP,bootstyle=('SUCCESS, OUTLINE')).pack(side=LEFT,fill=Y)



     def customer(self):
        
        self.new_win =Toplevel(self.root)
        self.new_obj=CustomerClass(self.new_win)
          
        

        


        
        

        
        
        

       



if __name__=="__main__":    
    root=tb.Window(themename="superhero")
    obj=Dashboard(root)
    root.mainloop()
