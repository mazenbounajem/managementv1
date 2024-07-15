from tkinter import StringVar
import ttkbootstrap as tb
from controls import ControlsClass
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import * 
from createtable import CreateTableClass
from connection import connection
from ttkbootstrap.dialogs import Dialog
from tkinter import PanedWindow
from ttkbootstrap.dialogs import Messagebox

class ProductsCass():
    def __init__(self, root):
        self.root = root
        self.root.title("Products")
        #frame 1 is taken by parameter to class controls
        self.frame1=tb.Frame(self.root)
        controlsget=ControlsClass
        controlsget.controls(self.frame1,self.root,self.add,self.save,self.duplicate,self.undo,self.delete,self.print,self.refresh,self.search)
        
        self.createtablenew=CreateTableClass
        self.getdatacombosup()
        self.getdatacombocat()
        self.frame2=tb.Frame()

        self.costper=StringVar()
        self.costam=StringVar()
        self.price=StringVar()
        self.priceht=StringVar()
        self.vatvalue=StringVar()
        self.varid=''
   # instatiate the class     
        self.frame2.pack(padx=150,fill='x')



        self.var_name=StringVar()
        # create the view design
        self.third_frame=tb.Frame(self.root)
        self.third_frame.place(x=100,y=450,width=1400,height=800)
        lbl_name=tb.Label(self.third_frame,bootstyle="info",text="Product Name:")
        lbl_name.grid(row=0,column=0,padx=10,pady=5)
        
        self.entry_name=tb.Entry(self.third_frame,textvariable=self.var_name,bootstyle="info")
        self.entry_name.grid(row=0,column=1,padx=10,pady=5)

        lbl_supplier=tb.Label(self.third_frame,bootstyle="info",text="Supplier:")
        lbl_supplier.grid(row=0,column=2,padx=10,pady=5)
        
        self.entry_Combosup=tb.Combobox(self.third_frame,bootstyle="info",values=self.slicedatasup)
        self.entry_Combosup.grid(row=0,column=3,padx=10,pady=5)
        self.entry_Combosup.bind('<KeyRelease>',self.searchcmbsupplier)

        lbl_category=tb.Label(self.third_frame,bootstyle="info",text="Category:")
        lbl_category.grid(row=0,column=4,padx=10,pady=5)
        
        self.entry_combocat=tb.Combobox(self.third_frame,bootstyle="info",values=self.slicedatacat)
        self.entry_combocat.grid(row=0,column=5,padx=10,pady=5)

       
        lbl_quantity=tb.Label(self.third_frame,bootstyle="info",text="Quantity:")
        lbl_quantity.grid(row=2,column=0,padx=10,pady=10)
       
        
        self.entry_quantity=tb.Spinbox(self.third_frame,bootstyle="info")
        self.entry_quantity.grid(row=2,column=1,padx=10,pady=10)

        


        lbl_cost=tb.Label(self.third_frame,bootstyle="info",text="Costpercentage:")
        lbl_cost.grid(row=2,column=2,padx=10,pady=10)
        
        self.entry_cost=tb.Spinbox(self.third_frame,bootstyle="info",textvariable=self.costper,state=DISABLED)
        self.entry_cost.grid(row=2,column=3,padx=10,pady=10)
        self.entry_cost.bind('<Return>',self.costpercentage)

        lbl_costamt=tb.Label(self.third_frame,bootstyle="info",text="Cost Amount:")
        lbl_costamt.grid(row=2,column=4,padx=10,pady=10)
        
        self.entry_costamt=tb.Spinbox(self.third_frame,bootstyle="info",textvariable=self.costam,state=DISABLED)
        self.entry_costamt.grid(row=2,column=5,padx=10,pady=10)
        self.entry_costamt.bind('<Return>',self.costamt)

        lbl_vatcombo=tb.Label(self.third_frame,bootstyle="info",text="Vat:")
        lbl_vatcombo.grid(row=4,column=0,padx=10,pady=10)

        
        
        self.entry_vatcomb=tb.Combobox(self.third_frame,bootstyle="info",values=[0,11],textvariable=self.vatvalue)
        self.entry_vatcomb.grid(row=4,column=1,padx=10,pady=10)

        lbl_price=tb.Label(self.third_frame,bootstyle="info",text="Price:")
        lbl_price.grid(row=4,column=2,padx=10,pady=10)


        self.entry_price=tb.Spinbox(self.third_frame,bootstyle="info",textvariable=self.price)
        self.entry_price.grid(row=4,column=3,padx=10,pady=10)
        self.entry_price.bind('<Return>',self.pricebinding)

        lbl_priceht=tb.Label(self.third_frame,bootstyle="info",text="PriceHT:")
        lbl_priceht.grid(row=4,column=4,padx=10,pady=10)

        self.entry_priceHT=tb.Spinbox(self.third_frame,bootstyle="info",textvariable=self.priceht)
        self.entry_priceHT.grid(row=4,column=5,padx=10,pady=10)

        

        





    
    
    ############################ define a treeview widget to get data for the products#################################
        self.tabletouse()
        #############################binding an event to tableview in the frame treeview widget
        self.tableview.bind_all('<<TreeviewSelect>>',self.getData)
    
    def tabletouse(self):
                datafromdatabase=[]
                columns=[]
                sqltoselectheaders='Select * from Product'
                sqltoselectcolumns= """SELECT Product.id,Product.ProductName, Supplier.Name, category.category_name, Product.Price, Product.Quantity, Product.Cost, Product.CostAmt, Product.Status,Product.Vat,Product.Priceht,Product.ProductImage
                 FROM     Product INNER JOIN
                  Supplier ON Product.Supplier = Supplier.id INNER JOIN
                  category ON Product.Category = category.id
                        ORDER BY Product.id DESC
                """
                

                self.createtablenew.create_table(datafromdatabase,columns,sqltoselectcolumns,sqltoselectheaders)
                self.datafromdatabase=datafromdatabase
                self.columns=columns
                
               
              
                self.tableview =Tableview( master=self.frame2, coldata=self.columns,rowdata= self.datafromdatabase[0], paginated=True, pagesize=12, height=12, searchable=True,  autofit=False,
                        bootstyle=PRIMARY,
                        stripecolor=(None, None),                  
                )
                
                #print(self.columns)
                
                self.tableview.columnconfigure(index=0,minsize=1,weight=1)
                
                self.tableview.pack(fill='x',expand=1)
    
    def getdatacombosup(self):
           self.slicedatasup=[]
           datafromsup=[]
           headersfromsup=[]
           querforrows='select Name from Supplier'
           queryforheaders='Select Name from Supplier'

           self.createtablenew.create_table(datafromsup,headersfromsup,querforrows,queryforheaders)
           self.datafromsup=datafromsup
           self.columns=headersfromsup
           print(type(self.datafromsup))

           for item in self.datafromsup:
                for i in range(len(item)):
                       self.slicedatasup.append(str(item[i][0]))
    def getdatacombocat(self):
           self.slicedatacat=[]
           datafromcat=[]
           headersfromscat=[]
           querforrows='select category_name from category'
           queryforheaders='Select category_name from category'

           self.createtablenew.create_table(datafromcat,headersfromscat,querforrows,queryforheaders)
           self.datafromcat=datafromcat
           self.columnscat=headersfromscat
           print(type(self.datafromcat))

           for item in self.datafromcat:
                for i in range(len(item)):
                       self.slicedatacat.append(str(item[i][0]))                   
    def searchcmbsupplier(self,event):
        self.datasup=[]
        value=event.widget.get()
        
        if value=='':
           self.entry_Combosup['values']=self.slicedatasup
        else:
           
           for item in self.slicedatasup:
              if value.lower() in item.lower():
                 self.datasup.append(item)
           self.entry_Combosup['values']=self.datasup
    def pricebinding(self,event):
          if self.price.get()==0:
                Messagebox.show_error(title='error',str="Please enter a value to price",parent=self.root)
          else:
             price=self.price.get()
             print(price)
             self.entry_cost.config(state=NORMAL)  
             self.entry_costamt.config(state=NORMAL) 
             vatget=self.entry_vatcomb.get()
             print(vatget)
             if int(vatget) !=0:
                   print(self.price.get())
                   vat=int(price)*0.11
                   priceht=float(price)-vat
                   self.entry_priceHT.set(priceht)
             else  :
                   self.entry_priceHT.set(self.price.get())           
    def costpercentage(self,event):
       if self.price.get()==0 :
          Messagebox.showerror("Error","please enter Uprice or profit",parent=self.root)
       elif self.price.get()!=0:
                  
                   costpercentage=float(self.entry_cost.get())
                   costamt=float(self.price.get())*(1-(costpercentage/100))
                   print (costamt)
                   self.entry_costamt.set(str(costamt))
    def costamt(self,event):
       if self.price.get()==0:
                  Messagebox.showerror("Error","Please Enter Price",parent=self.root)
       elif self.price.get()!=0:
          costamt=int(self.entry_costamt.get())
          var_costpercentage=round((1-float(costamt/float(self.price.get())))*100)
          self.entry_cost.set(str(var_costpercentage))  

    def getData(self,event):
          if event:
              print(event) 
              selected_rows = self.tableview.get_rows(selected=True)
              for row in selected_rows:
                #print (row.values)
                        self.varid=row.values[0]
                        self.var_name.set(row.values[1])
                        self.entry_Combosup.set(row.values[2])
                        self.entry_combocat.set(row.values[3])
                        self.entry_quantity.set(row.values[5])
                        self.entry_cost.set(row.values[6])
                        self.entry_costamt.set(row.values[7])
                        self.vatvalue.set(row.values[9])
                        self.entry_price.set(row.values[4])
                        self.priceht.set(row.values[10])                                        
        
#     def getvaluecombo(self,Key):
#         #    print(Key.char)
#         #    query=self.entry_Combosup.get().lower()
#         #    print(query)

#         #    for i in range(len(self.slicedatasup)):
#         #           #print(self.slicedatasup[i].lower())
#         #           if query in self.slicedatasup[i].lower():
#         #                  print(self.slicedatasup[i].lower())
        
#         self.row=[]
           
#         getcustomername=connection.contogetrows
#         getnames=[]
#         getcustomername('select Name,phone from Supplier',getnames)
#         self.supname=StringVar()
        
#         canvas=tb.Canvas()
#         self.entrycombo=tb.Entry(textvariable=self.supname,bootstyle="info")
#         self.entrycombo.focus_set()
#         self.getsup=tb.Button(text='Search')

#         print(Key.char)
#         canvas.pack(side='top',padx=500,anchor='w')
        
#         canvas.create_window(200,140, window=self.entrycombo)
        
#         canvas.create_window(300, 140, window=self.getsup)

#         self.newtable=tb.Treeview(columns=('id','name'),show='headings',style='success.Treeview',height=5)
#         self.newtable.heading('id',text='Id')
#         self.newtable.heading('name',text='Name')
#         canvas.create_window(200,240,window=self.newtable)
#         for i in range(len(getnames)):
#                     self.newtable.insert('',index=i,values=(getnames[i][0],getnames[i][1]))
#         self.newtable.grid(row=2,column=0)
#         query=self.entrycombo.get().lower()
#         for item in self.newtable.get_children():
#                 values=self.newtable.item(item,"values")
#                 if query not in values[0].lower():
#                     #   newtable.selection_set(data)
#                     #   newtable.focus(data)
#                     #   newtable.see(data)
#                     self.newtable.delete(item)
                    
                    

#                 else:
#                     self.newtable.selection_set(item)
#                     self.newtable.focus(item)
#                     self.newtable.see(item)
#         curItem = self.newtable.focus()
                    
#         content= (self.newtable.item(curItem))
#         row=content['values'] 
#             #print(row)
#         self.newtable.bind("<Button-1>",on_click) 
#             #print(key.char)
#         self.valueofentry =row
#         def on_click(event):
#                 region_clicked=self.newtable.identify_region(event.x,event.y)
#                 #print(region_clicked)
#                 if region_clicked not in ("tree","cell"):
#                     return
        
#                 # which item was double clicked
#                 column=self.newtable.identify_column(event.x)
#                 # to start at 1
#                 column_index=int(column[1:])-1
#             # print(column)
#                 selected_iid=self.newtable.focus()
#                 selected_values=self.newtable.item(selected_iid)
#                 row=selected_values.get("values")
#                 #print(row)
#                 self.valueofentry = row 
                
               
               
                

              
        
           
    
    
    
    
       
    
    
    
    
    
    
    
    
    
    
    
    
    
    #functions to controls.py defined in class controlsclass with function controls taken as parameters    
    def add(self):
            print("you click add")
            self.varid=''
            self.var_name.set("")
            self.entry_Combosup.set("")
            self.entry_combocat.set("")
            self.entry_quantity.set("")
            self.entry_cost.set("")
            self.entry_costamt.set("")
            self.entry_vatcomb.set("")
            self.entry_price.set("")
            self.entry_priceHT.set("")
    def save(self):
            print("you click save")
            name=self.var_name.get()
            combosup=self.entry_Combosup.get()
            combocat=self.entry_combocat.get()
            quantity=self.entry_quantity.get()
            cost= self.entry_cost.get()
            costamount=self.entry_costamt.get()
            vatcomb=self.vatvalue.get()
            price=self.price.get()
            priceht=self.priceht.get()
            print(name,combosup,combocat,quantity,cost,costamount,vatcomb,price,priceht)
            connectiontogetid=connection

            idsupp=connectiontogetid.getid("select id from supplier where Name=?",combosup)
        #print(idsupp)
            idcat=connectiontogetid.getid("select id from category where category_name=?",combocat)
            
            if self.varid!='':
                 try:
                          sql=""" Update product set ProductName=?, Supplier=?,Category=?,Price=?,Quantity=?,Cost=?,CostAmt=?,Status=?,Vat=?,Priceht=? where id=?"""
                          inputs=(name,idsupp,idcat,price,quantity,cost,costamount,'Active',vatcomb,priceht,self.varid)
                          messagebox1=Messagebox.yesno(title='Question',message='Are you sure you want to update Data')
                          print(messagebox1)
                          if  messagebox1=="No":
                                 print('no')
                                 return
                          else:          
                                connectiontogetid.insertingtodatabase(sql,inputs) 
                                messagebox=Messagebox.show_info('update','Data updated successfuly',self.root) 
                                        
                 except Exception as ex:
                                messagebox=Messagebox.show_error('Error',f'Could not connect to database:{str(ex)}',self.root)     
                 finally:
                                pass
                
            else: 
                   # print(idcat)
                try:
                        sql=""" insert into Product(ProductName,Supplier,Category,Price,Quantity,Cost,CostAmt,Status,Vat,Priceht)
                                Values(?,?,?,?,?,?,?,?,?,?)"""
                        values=(name,idsupp,idcat,price,quantity,cost,costamount,'Active',vatcomb,priceht)
                        connectiontogetid.insertingtodatabase(sql,values)
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
    def duplicate(self):
            print("you click duplicat")
    def undo(self):
            print("you click undo") 
            if self.varid!='':
                print(self.varid)
                str(self.varid)
                self.getData(E)        
    def delete(self):
            print("you click delete")
            if  self.varid!="":
                
                sql=""" DELETE From Product where id=?"""
                id=self.varid
              
                try:
                        deletingcategoryrow=connection.deleterow
                        deletingcategoryrow(sql,id)
                except:
                        messagebox=Messagebox.show_error("Error","please an item",parent=self.root)
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
                print("you click refresh")
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
    root.geometry("%dx%d" % (width, height))
    obj = ProductsCass(root)
    root.mainloop()
        
        