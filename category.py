import ttkbootstrap as tb
from controls import ControlsClass
from createtable import CreateTableClass
from tkinter import *
import tkinter as tk
from tkinter import ttk
from connection import connection
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *


class CategoryClass():
    def __init__(self, root,colors):
        super().__init__()
        
        self.colors=colors
        self.root = root
        self.root.title("Category")
        self.datafromdatabase=[]
        self.columns=[]
        self.table=Tableview
        self.table1=tb.Treeview()
        self.varid=''
        self.var_Categorycode=StringVar()
        self.var_CategoryName=StringVar()
        self.var_discription=StringVar()
        self.var_companyidentetiy=StringVar()

        #frame 1 is taken by parameter to class controls
        self.frame1=tb.Frame()
        controlsget=ControlsClass
        controlsget.controls(self.frame1,self.root,self.add,self.save,self.duplicate,self.undo,self.delete,self.print,self.refresh,self.search)
    
    
    ############################ define a treeview widget to get data for the Category#################################
        
        
        self.frame2=tb.Frame()
        self.frame2.pack(padx=150,fill='x')
        self.createtablenew=CreateTableClass
        

  
        

        

        ###########################variable in the class
        third_frame=tb.Frame(self.root)
        third_frame.place(x=150,y=450,width=1400,height=800)
        lbl_name=tb.Label(third_frame,bootstyle="info",text="Code:")
        lbl_name.grid(row=0,column=0,padx=10,pady=5)
        
        self.entry_CategoryCode=tb.Entry(third_frame,textvariable=self.var_Categorycode,bootstyle="info")
        self.entry_CategoryCode.grid(row=0,column=1,padx=10,pady=5)

        lbl_companyname=tb.Label(third_frame,bootstyle="info",text="Category Name:")
        lbl_companyname.grid(row=0,column=2,padx=10,pady=5)
        
        self.categoryname=tb.Entry(third_frame,textvariable=self.var_CategoryName,bootstyle="info")
        self.categoryname.grid(row=0,column=3,padx=10,pady=5)

        
        lbl_companyid=tb.Label(third_frame,bootstyle="info",text="Company Identity:")
        lbl_companyid.grid(row=2,column=0,padx=0,pady=5)
        self.companyidentity=tb.Combobox(third_frame,values=['fabrics','finished products','glass','socialmedia'],textvariable=self.var_companyidentetiy)
        self.companyidentity.grid(row=2,column=1,padx=10,pady=5)

        lbl_discription=tb.Label(third_frame,bootstyle="info",text="Discription:")
        lbl_discription.grid(row=2,column=2,padx=10,pady=5)
        self.framefortext=tb.Frame()
        self.framefortext.place(x=630,y=500,width=400,height=100)
        self.entry_Discription=tb.Text(self.framefortext,border=1,height=10,width=100)
        self.entry_Discription.pack(ipadx=400,ipady=500,fill="both")
        
        self.tabletouse()
        self.tableview.bind_all('<<TreeviewSelect>>',self.getData)
    #functions to controls.py defined in class controlsclass with function controls taken as parameters    
    def tabletouse(self):
                datafromdatabase=[]
                columns=[]


                self.createtablenew.create_table(datafromdatabase,columns)
                self.datafromdatabase=datafromdatabase
                self.columns=columns
                
                
                #print(type(self.table))
                self.tableview =Tableview( master=self.frame2, coldata=self.columns, rowdata=self.datafromdatabase[0], paginated=True, pagesize=12, height=12, searchable=True,            autofit=False,
                        bootstyle=PRIMARY,
                        stripecolor=(None, None),                  
                )
                
                self.tableview.pack(fill='x',expand=100)    
    def add(self):
                 self.varid=''
                 self.var_Categorycode.set('')
                 self.var_CategoryName.set('')
                 self.var_companyidentetiy.set('')
                 self.entry_Discription.delete('0.0','end')
    def save(self):
            print("you click save")
            
            categoryname=self.categoryname.get()
            ccode=self.entry_CategoryCode.get()
            companyidentity=self.companyidentity.get()
            cdiscription=self.entry_Discription.get('1.0',END)
            print(categoryname,ccode,cdiscription,companyidentity)
            entercategory=connection.insertingtodatabase
            if self.varid!='' :
                   int(self.varid)
                   try:
                        sql2="""update category SET category_code=?,category_name=?,discription=?,company_id=? where id=? """                
                        
                        inputs=(ccode,categoryname,cdiscription,companyidentity,self.varid)
                        entercategory(sql2,inputs)
                   except Exception as ex:
                          messagebox=Messagebox.show_error('Error',f'Could not connect to database:{str(ex)}',self.root)     
                   finally:
                          messagebox=Messagebox.yesnocancel('Are you sure you want to update Data','Question',self.root)
                          if not messagebox:
                                 return 
                          else:
                                 messagebox=Messagebox.show_info('update','Data updated successfuly',self.root)

            else:  
                        print(self.varid,'it is equal to null') 
                        try:
                                
                                sql="""insert into category(category_code,category_name,discription,company_id,status)
                                Values(?,?,?,?,1)"""
                                Values=(ccode,categoryname,cdiscription,companyidentity)
                                entercategory(sql,Values)
                        except Exception as ex:
                                messagebox=Messagebox.show_error('Error',f'could not connect to database:{str(ex)}',self.root)
                        finally:
                                messagebox=Messagebox.show_info('Success','Data entered successfully',self.root) 
                        

            self.tableview.pack_forget()
            self.tableview.delete_rows()
            self.tableview.delete_columns()
            self.datafromdatabase.clear()
            self.columns.clear()
            
            self.tabletouse()
            #print (type(self.datafromdatabase))
            

    def getData(self,event):
          if event:
              print(event) 
              selected_rows = self.tableview.get_rows(selected=True)
              for row in selected_rows:
                #print (row.values)
                 self.varid=row.values[0]
                 self.var_Categorycode.set(row.values[1])
                 self.var_CategoryName.set(row.values[2])
                 self.var_companyidentetiy.set(row.values[4])
                 self.entry_Discription.delete('0.0','end')
                 self.entry_Discription.insert('1.0',row.values[3])

                   


    def duplicate(self):
            print("you click duplicat")
    def undo(self):
            print("you click undo") 
            if self.varid!='':
              print(self.varid)
              str(self.varid)
              self.getData(Event)               
    def delete(self):
            print("you click delete")
            if  self.var_CategoryName.get()!="":
                self.var_CategoryName.get()
                sql=""" DELETE From category where category_name=?"""
                categoryname=self.var_CategoryName.get()
              
                try:
                        deletingcategoryrow=connection.deleterow
                        deletingcategoryrow(sql,categoryname)
                except:
                        messagebox=Messagebox.show_error("Error","please enter category name",parent=self.root)
                else:     
                        self.tableview.pack_forget()
                        self.tableview.delete_rows()
                        self.tableview.delete_columns()
                        self.datafromdatabase.clear()
                        self.columns.clear()
                        self.tabletouse() 
    def print(self):
            print("you click print") 
    def refresh(self):
        self.tableview.pack_forget()
        self.tableview.delete_rows()
        self.tableview.delete_columns()
        self.datafromdatabase.clear()
        self.columns.clear()
        self.tabletouse() 
    def search(self):
            print("you click search")


if __name__=="__main__":
    root = tb.Window(themename="superhero")
    width= root.winfo_screenwidth() 
    height= root.winfo_screenheight()
    colors = root.style.colors
    root.geometry("%dx%d" % (width, height))
    obj = CategoryClass(root,colors)
    root.mainloop()