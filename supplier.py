import ttkbootstrap as tb
from controls import ControlsClass
from createtable import CreateTableClass
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from tkinter import *
from ttkbootstrap.dialogs import Messagebox
from connection import connection


class SupplierClass():
    def __init__(self, root):
        super().__init__()
        self.root=root
        self.root.title("Supplier")
        self.var_name=StringVar()
        self.var_address=StringVar()
        self.var_phone=StringVar()
        self.var_email=StringVar()
        self.var_mof=StringVar()
        self.var_vat=StringVar()
        self.var_website=StringVar()
        self.var_mobile=StringVar()
        self.varid=''




    #create a frame for controls imported from class Controls
        self.frame1=tb.Frame()
    #create an instantiation for the class    
        controlsget=ControlsClass

    # call the method or the function 
        controlsget.controls(self.frame1,self.root,self.add,self.save,self.duplicate,self.undo,self.delete,self.print,self.refresh,self.search)



        self.frame2=tb.Frame()
   # instatiate the class     
        self.frame2.pack(padx=150,fill='x')
        self.createtablenew=CreateTableClass


   # create the view design
        third_frame=tb.Frame(self.root)
        third_frame.place(x=100,y=450,width=1400,height=800)
        lbl_name=tb.Label(third_frame,bootstyle="info",text="Name:")
        lbl_name.grid(row=0,column=0,padx=10,pady=5)
        
self.entry_name=tb.Entry(third_frame,textvariable=self.var_name,bootstyle="info")
        self.entry_name.grid(row=0,column=1,padx=10,pady=5)
self.entry_name.configure(fg='#c05884', relief='flat')

        lbl_address=tb.Label(third_frame,bootstyle="info",text="Address:")
        lbl_address.grid(row=0,column=2,padx=10,pady=5)
        
self.entry_address=tb.Entry(third_frame,textvariable=self.var_address,bootstyle="info")
        self.entry_address.grid(row=0,column=3,padx=10,pady=5)
self.entry_address.configure(fg='#c05884', relief='flat')

        lbl_phone=tb.Label(third_frame,bootstyle="info",text="Phone:")
        lbl_phone.grid(row=0,column=4,padx=10,pady=5)
        
self.entry_phone=tb.Entry(third_frame,textvariable=self.var_phone,bootstyle="info")
        self.entry_phone.grid(row=0,column=5,padx=10,pady=5)
        self.entry_phone.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')

        lbl_email=tb.Label(third_frame,bootstyle="info",text="Email:")
        lbl_email.grid(row=1,column=0,padx=10,pady=5)
        
self.entry_email=tb.Entry(third_frame,textvariable=self.var_email,bootstyle="info")
        self.entry_email.grid(row=1,column=1,padx=10,pady=5)
        self.entry_email.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')

        lbl_mof=tb.Label(third_frame,bootstyle="info",text="MOF:")
        lbl_mof.grid(row=1,column=2,padx=10,pady=5)
        
self.entry_mof=tb.Entry(third_frame,textvariable=self.var_mof,bootstyle="info")
        self.entry_mof.grid(row=1,column=3,padx=10,pady=5)
        self.entry_mof.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')

        lbl_vat=tb.Label(third_frame,bootstyle="info",text="Vat:")
        lbl_vat.grid(row=1,column=4,padx=10,pady=5)
        
self.entry_vat=tb.Entry(third_frame,textvariable=self.var_vat,bootstyle="info")
        self.entry_vat.grid(row=1,column=5,padx=10,pady=5)
        self.entry_vat.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')

        lbl_project=tb.Label(third_frame,bootstyle="info",text="Website:")
        lbl_project.grid(row=1,column=6,padx=10,pady=5)
        
self.entry_project=tb.Entry(third_frame,textvariable=self.var_website,bootstyle="info")
        self.entry_project.grid(row=1,column=7,padx=10,pady=5)
        self.entry_project.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')

        lbl_referncedby=tb.Label(third_frame,bootstyle="info",text="Mobile:")
        lbl_referncedby.grid(row=0,column=6,padx=10,pady=5)
        
self.entry_reference=tb.Entry(third_frame,textvariable=self.var_mobile,bootstyle="info")
        self.entry_reference.grid(row=0,column=7,padx=10,pady=5)
        self.entry_reference.configure(bg='#c05884', fg='white', insertcolor='white', relief='flat')     

        self.tabletouse()
        self.tableview.bind_all('<<TreeviewSelect>>',self.getData)
    #functions to controls.py defined in class controlsclass with function controls taken as parameters    
    def tabletouse(self):
                datafromdatabase=[]
                columns=[]
                sqltoselectheaders= 'select * from Supplier'
                sqltoselectcolumns='select * from Supplier order by id desc'
                

                self.createtablenew.create_table(datafromdatabase,columns,sqltoselectheaders,sqltoselectcolumns)
                self.datafromdatabase=datafromdatabase
                self.columns=columns
                
                
                #print(type(self.table))
                self.tableview =Tableview( master=self.frame2, coldata=self.columns, rowdata=self.datafromdatabase[0], paginated=True, pagesize=12, height=12, searchable=True,  autofit=False,
                        bootstyle=PRIMARY,
                        stripecolor=(None, None),                  
                )
                print(self.columns)
                
                self.tableview.pack(fill='both',expand=1) 

    def getData(self,event):
          if event:
              print(event) 
              selected_rows = self.tableview.get_rows(selected=True)
              for row in selected_rows:
                #print (row.values)
                 self.varid=row.values[0]
                 self.var_name.set(row.values[1])
                 self.var_address.set(row.values[3])
                 self.var_phone.set(row.values[4])
                 self.var_mobile.set(row.values[5])
                 self.var_website.set(row.values[6])
                 self.var_vat.set(row.values[7])
                 self.var_mof.set(row.values[8])


                 

        







### create functions to add save duplicate undo delete print refresh search

    def add(self):
        print (self.varid)
        #self.varid.set(" ")
        self.varid=''
        self.var_name.set(" ")
        self.var_address.set(" ")
        self.var_phone.set(" ")
        self.var_mobile.set(" ")
        self.var_website.set(" ")
        self.var_vat.set(" ")
        self.var_mof.set(" ")
    def save(self):
        print('you click save')   
        sname=self.var_name.get()
        saddress=self.var_address.get()
        smobile=self.var_mobile.get()
        smof=self.var_mof.get()
        emailaddress=self.var_email.get()
        sphone=self.var_phone.get()
        swebsite=self.var_website.get()
        svat=self.var_vat.get()
       # print(sname,saddress,smobile,emailaddress,smof,sphone,swebsite,svat) 
        inserttosupplier=connection
        
        if self.varid !='':
                  int(self.varid)
                  try:
                        sql2="""update supplier SET Name=?,CurrencyId=?,PrimaryAddress=?,Email=?,Phone=?,Mobile=?,Email=?,website=?,VatNumber=?,Mof=? where id=? """                
                        
                        inputs=(sname,1,saddress,sphone,smobile,emailaddress,swebsite,svat,smof, self.varid)
                        
                        messagebox1=Messagebox.yesno(title='Question',message='Are you sure you want to update Data')
                        print(messagebox1)
                        if  messagebox1=="No":
                                 print('no')
                                 return
                        else:          
                                inserttosupplier.insertingtodatabase(sql2,inputs) 
                                messagebox=Messagebox.show_info('update','Data updated successfuly',self.root) 
                                 
                  except Exception as ex:
                          messagebox=Messagebox.show_error('Error',f'Could not connect to database:{str(ex)}',self.root)     
                  finally:
                          return
        else: 
                 try:
                     sql="""insert into supplier (Name,CurrencyId,PrimaryAddress,Phone,Mobile,Email,website,VatNumber,Mof,Balance_LL,Balance_USD)
                     Values(?,?,?,?,?,?,?,?,?,0.00,0.00)"""
                     values=(sname,1,saddress,sphone,smobile,emailaddress,swebsite,svat,smof)
                     inserttosupplier.insertingtodatabase(sql,values)
                 except Exception as ex :
                      messagebox=Messagebox.show_error('Error',f'Could not connect to database:{str(ex)}',self.root)  
                 finally:
                      messagebox=Messagebox.show_info(title='Inserting',message='Supplier where successfully added')  
                 
                 
        
        self.tableview.pack_forget()
        self.tableview.delete_rows()
        self.tableview.delete_columns()
        self.datafromdatabase.clear()
        self.columns.clear()
            
        self.tabletouse()        
    def duplicate(self):
        print('you click duplicate')        
    def undo(self):
            if self.varid!='':
              print(self.varid)
              str(self.varid)
              self.getData(Event)     
    def delete(self):
        print('you click delete')

        if  self.varid!="":
                int(self.varid)
                sql=""" DELETE From Supplier where id=?"""
                deletingbyid=self.varid
              
                try:
                        deletingsupplierrow=connection.deleterow
                        deletingsupplierrow(sql,deletingbyid)
                except:
                        messagebox=Messagebox.show_error("Error","please select supplier name",parent=self.root)
                else:     
                        self.tableview.pack_forget()
                        self.tableview.delete_rows()
                        self.tableview.delete_columns()
                        self.datafromdatabase.clear()
                        self.columns.clear()
                        self.tabletouse()  

    def print(self):
        print('you click print')   
    def refresh(self):
        self.tableview.pack_forget()
        self.tableview.delete_rows()
        self.tableview.delete_columns()
        self.datafromdatabase.clear()
        self.columns.clear()
        self.tabletouse() 
    def search(self):
        print('you click search')          







if __name__=="__main__":
    root = tb.Window(themename="superhero")
    width= root.winfo_screenwidth() 
    height= root.winfo_screenheight()
    colors = root.style.colors
    root.geometry("%dx%d" % (width, height))
    obj = SupplierClass(root)
    root.mainloop()