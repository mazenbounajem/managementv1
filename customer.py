
from tkinter import messagebox
from tkinter.ttk import Treeview
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.style import *
from tkinter import *
from ttkbootstrap.style import *
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
from connection import connection
from customerprint import CustomerPrint


class CustomerClass():
    def __init__(self,root, title='',themename='superhero', iconphoto='.images/conphoto.png', size=None, position=None, minsize=None, maxsize=None, resizable=None, hdpi=True, scaling=None, transient=None, overrideredirect=False, alpha=1.0):
        self.root=root
        self.root.title('Customer')
        self.root.iconbitmap('./images/conphoto.png')
        self.root.geometry("1800x800+0+150")
    #     colors=root.style.colors
        #first frame contain the control buttons
        ############################ Global Variables ################
        self.var_name=StringVar()
        self.var_address=StringVar()
        self.var_phone=StringVar()
        self.var_email=StringVar()
        self.var_referenceby=StringVar()
        self.var_mof=StringVar()
        self.var_vat=StringVar()
        self.var_project=StringVar()
        # to add data to sql server
        self.data=[]
        self.datafromdatabase=[]
        # for binding treeview to table
        self.tree = ttk.Treeview()
        self.varid=''
        
        
################################## Gui Frames, contain 3 frame 1 for controls, 2 for table, and frame 3 for data entry ########################

        first_frame=Frame(self.root)
        first_frame.grid(row=0,column=0)
        self.icon_new=PhotoImage(file="images/iconsglobal/add.png")
        
        btn_new = ttk.Button(first_frame,command=self.add,image=self.icon_new,bootstyle=('outline'))
        btn_new.grid(row=0,column=0)

        self.save=PhotoImage(file="images/iconsglobal/save.png")
        
        btn_save= ttk.Button(first_frame,command=self.onClickSave,image=self.save,bootstyle=('outline'))
        btn_save.grid(row=1,column=0)



        self.icon_duplicate=PhotoImage(file="images/iconsglobal/duplicate.png")
        btn_duplicate = ttk.Button(first_frame,image=self.icon_duplicate,bootstyle=('outline'))
        btn_duplicate.grid(row=2,column=0)
        self.icon_undo=PhotoImage(file="images/iconsglobal/undo.png")
        btn_undo = ttk.Button(first_frame,command=self.undo,image=self.icon_undo,bootstyle=('outline'))
        btn_undo.grid(row=3,column=0)
        self.icon_delete=PhotoImage(file="images/iconsglobal/delete.png")
        btn_delete = ttk.Button(first_frame,command=self.delete,image=self.icon_delete,bootstyle=('outline'))
        btn_delete.grid(row=4,column=0)
        self.icon_print=PhotoImage(file="images/iconsglobal/print.png")
        btn_print = ttk.Button(first_frame,command=self.print,image=self.icon_print,bootstyle=('outline'))
        btn_print.grid(row=5,column=0)
        self.icon_refresh=PhotoImage(file="images/iconsglobal/refresh.png")
        btn_refresh = ttk.Button(first_frame,command=self.refresh,image=self.icon_refresh,bootstyle=('outline'))
        btn_refresh.grid(row=6,column=0)
        self.icon_search=PhotoImage(file="images/iconsglobal/search.png")
        btn_search= ttk.Button(first_frame,image=self.icon_search,bootstyle=('outline'))
        btn_search.grid(row=7,column=0)

        # second frame contain the data table
        
        self.second_frame =tb.Frame(self.root)
        self.second_frame.place(x=100,y=0,width=1800,height=400)
         
        self.create_table()
        
        self.table.bind_all('<<TreeviewSelect>>',self.getData)
        
        
# example for the row data
    def create_table(self):
            getdatacustomer= connection.contogetrows
            getdatacustomerall=[]
            getdatacustomer('select * from customer',getdatacustomerall)
           # print(getdatacustomerall)
            self.datafromdatabase.append(getdatacustomerall)
            #row_data = [
            #    ('mazen','1','ghaboun','76352915','mazenbounajem@gmail.com','2024-05-17','2024-05-17','2024-05-17','100000','1')
             #   ]
            

            getcolumnnames=connection.contogetheaders
            getheaderscustomers=[]
            getheaders=getcolumnnames('select * from customer',getheaderscustomers)
          
            columns=getheaderscustomers
            self.table =Tableview(
                master=self.second_frame,
                coldata=columns,
                rowdata=self.datafromdatabase[0],
                paginated=True,
                pagesize=12,
                height=12,
                searchable=True,
                autofit=True,
                bootstyle=PRIMARY,
                stripecolor=(None),
                autoalign=LEFT
                
                
            )
            
            
            
            self.table.grid(row=0,column=0,padx='0',pady='10')
        #table.insert_row('',END,values=)
            row=self.table.tablerows
            #print(row[1].values)
            
            
            third_frame=tb.Frame(self.root)
            third_frame.place(x=100,y=450,width=1400,height=800)
            lbl_name=tb.Label(third_frame,bootstyle="info",text="Name:")
            lbl_name.grid(row=0,column=0,padx=10,pady=5)
            
            self.entry_name=tb.Entry(third_frame,textvariable=self.var_name,bootstyle="info")
            self.entry_name.grid(row=0,column=1,padx=10,pady=5)

            lbl_address=tb.Label(third_frame,bootstyle="info",text="Address:")
            lbl_address.grid(row=0,column=2,padx=10,pady=5)
            
            self.entry_address=tb.Entry(third_frame,textvariable=self.var_address,bootstyle="info")
            self.entry_address.grid(row=0,column=3,padx=10,pady=5)

            lbl_phone=tb.Label(third_frame,bootstyle="info",text="Phone:")
            lbl_phone.grid(row=0,column=4,padx=10,pady=5)
            
            self.entry_phone=tb.Entry(third_frame,textvariable=self.var_phone,bootstyle="info")
            self.entry_phone.grid(row=0,column=5,padx=10,pady=5)

            lbl_email=tb.Label(third_frame,bootstyle="info",text="Email:")
            lbl_email.grid(row=1,column=0,padx=10,pady=5)
            
            self.entry_email=tb.Entry(third_frame,textvariable=self.var_email,bootstyle="info")
            self.entry_email.grid(row=1,column=1,padx=10,pady=5)

            lbl_mof=tb.Label(third_frame,bootstyle="info",text="MOF:")
            lbl_mof.grid(row=1,column=2,padx=10,pady=5)
            
            self.entry_mof=tb.Entry(third_frame,textvariable=self.var_mof,bootstyle="info")
            self.entry_mof.grid(row=1,column=3,padx=10,pady=5)

            lbl_vat=tb.Label(third_frame,bootstyle="info",text="Vat:")
            lbl_vat.grid(row=2,column=0,padx=10,pady=5)
            
            self.entry_vat=tb.Entry(third_frame,textvariable=self.var_vat,bootstyle="info")
            self.entry_vat.grid(row=2,column=1,padx=10,pady=5)

            lbl_project=tb.Label(third_frame,bootstyle="info",text="Project:")
            lbl_project.grid(row=2,column=2,padx=10,pady=5)
            
            self.entry_project=tb.Entry(third_frame,textvariable=self.var_project,bootstyle="info")
            self.entry_project.grid(row=2,column=3,padx=10,pady=5)

            lbl_referncedby=tb.Label(third_frame,bootstyle="info",text="Refernced By:")
            lbl_referncedby.grid(row=3,column=0,padx=10,pady=5)
            
            self.entry_reference=tb.Entry(third_frame,textvariable=self.var_referenceby,bootstyle="info")
            self.entry_reference.grid(row=3,column=1,padx=10,pady=5)




        ##################################functions#######################
    
    def getData(self,ev):
          if ev:  
            selected_rows = self.table.get_rows(selected=True)
    # print(selected_rows)
            for row in selected_rows:
                #print (row.values)
                self.varid=row.values[0]
                self.var_name.set(row.values[1])
                self.var_address.set(row.values[2])
                self.var_phone.set(row.values[3])
                self.var_email.set(row.values[4])
                self.var_mof.set(row.values[6])
                self.var_vat.set(row.values[7])
                self.var_project.set(row.values[8])
                self.var_referenceby.set(row.values[5])
          else:
               pass 
    def onClickSave(self):
            customer_name=self.var_name.get()
            customer_address=self.var_address.get()
            customer_phone=self.var_phone.get()
            customer_email=self.var_email.get()
            customer_mof=self.var_mof.get()
            customer_vat=self.var_vat.get()
            customer_project=self.var_project.get()
            customer_referenceby=self.var_referenceby.get()
            if self.var_name.get()=="":
                messagebox.showerror("Error",f"please enter customer Name",parent=self.root)
            else:
                 print(customer_name,customer_mof,customer_address,customer_email,customer_vat,customer_project,customer_referenceby)
                 self.data.append((customer_name,customer_address,customer_phone,customer_email,customer_referenceby,customer_mof,customer_vat,customer_project,'','','','',''))
                 print(self.data)
                 #self.table.destroy()
                 #self.table=self.create_table()
                 sql="""insert into customer (customerName,Address,phone,Email,refernceBy,mof,vat,project,firstsalesdate,lastpaymentdate,lastsalesdate,balanceLL,balanceusd) 
                 Values(?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL)"""
                 values=(customer_name,customer_mof,customer_address,customer_phone,customer_email,customer_vat,customer_project,customer_referenceby)
                 insertingdatacustomer=connection.insertingtodatabase
                 insertingdatacustomer(sql,values)
                 self.table.delete_rows()
                 self.datafromdatabase.clear()
                 self.create_table()              
    def add(self):
         self.var_name.set("")
         self.var_address.set("")
         self.var_phone.set("")
         self.var_email.set("")
         self.var_mof.set("")
         self.var_vat.set("")
         self.var_project.set("")
         self.var_referenceby.set("")
    def delete(self):
         if self.var_name.get()!="":
              self.var_name.get()
              sql=""" DELETE From Customer where customerName=?"""
              customername=self.var_name.get()
              
              try:
                    deletingcustomerrow=connection.deleterow
                    deletingcustomerrow(sql,customername)
              except:
                   messagebox.showerror("Error","please enter customer name",parent=self.root)
              else:     
                    self.table.delete_rows()
                    self.datafromdatabase.clear()
                    self.create_table()  
    def refresh(self):
         self.datafromdatabase.clear()
         self.create_table()
    def undo(self):
         if self.varid!='':
              print(self.varid)
              str(self.varid)
              self.getData(Event)
    
    def print(self):
        self.new_win =Toplevel(self.root)
        self.new_obj=CustomerPrint(self.new_win)
         

            

        
       
        

     




if __name__=="__main__":    
    root=tb.Window(themename="superhero")
    obj=CustomerClass(root)
    root.mainloop()