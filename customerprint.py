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
import emoji



class CustomerPrint:
    def __init__(self,root):
        self.root=root
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws) 
        y = (hs)
        print (w,h,ws,hs)
        self.root.geometry("1600x700+200+150")
        self.root.resizable(False, False)
        
        self.root.title('Customer Print')
        self.rows1=[()]
        self.frame1=tb.Frame(self.root)
        self.frame1.place(x=100,y=0)
        self.cmb1=object
        self.cmb2=object
        self.cmb3=object

        self.lbltitle=tb.Label(self.frame1,bootstyle='danger',text="Please Select a title for your report:",font=("times new roman",'10','bold'),background='white')
        self.lbltitle.grid(row=1,column=0,padx=10,pady=50)

        self.cmbreport=tb.Combobox(self.frame1,bootstyle='success',values=['customer info','customer statment','customer bought products'],state='readonly')
        self.cmbreport.grid(row=1,column=1,padx=40,pady=50)
        self.cmbreport.current(0)
       
        self.frame2=tb.Frame(self.root)
        self.frame2.place(x=0, y=200)


        columns1=[
            
                {'text':'field'},
                {'text':'condtion'},
                {'text':'value'}
        ]
            
          
       
        self.table =Tableview(
                master=self.frame2,
                coldata=columns1,
                rowdata=self.rows1,
                paginated=False,
                pagesize=1,
                height=5,
                searchable=False,
                autofit=False,
                bootstyle=PRIMARY,
                stripecolor=(None),
                autoalign=LEFT

                     
            )
       # self.build()
        self.table.grid(row=1,column=0,padx=50,pady=0,columnspan=1)


        self.frame3=tb.Frame(self.frame2)
        self.frame3.grid(row=2,column=0)
       
        self.buttonminus=tb.Button(self.frame3,bootstyle="secondary-outline",command=self.delete,text= f'{emoji.emojize(":minus:")}')
        self.buttonminus.grid(row=2,column=0,columnspan=1,padx=0)
        self.buttonback=tb.Button(self.frame3,bootstyle="secondary-outline",text= f'{emoji.emojize(":BACK_arrow:")}')
        self.buttonback.grid(row=2,column=1,columnspan=1,padx=0)
        self.buttonsoon=tb.Button(self.frame3,bootstyle="secondary-outline",text= f'{emoji.emojize(":SOON_arrow:")}')
        self.buttonsoon.grid(row=2,column=2,columnspan=1,padx=0)
        self.buttonadd=tb.Button(self.frame3,bootstyle="secondary-outline",command=self.add,text= f'{emoji.emojize(":plus:")}')
        self.buttonadd.grid(row=2,column=3,columnspan=1,padx=0)
        
        self.table.bind_all('<<TreeviewSelect>>',self.set_cell_value)
        
        self.frame4=tb.Frame(self.root)
        self.frame4.place(x=40, y=400)
        self.enterdate=tb.Label(self.frame4,text="From Date")
        self.enterdate.grid(row=0,column=0)
        self.entryd=tb.DateEntry(self.frame4,bootstyle='danger')
        self.entryd.grid(row=0,column=1)

        self.tilldate=tb.Label(self.frame4,text="Till Date")
        self.tilldate.grid(row=1,column=0,padx=20)
        self.tilld=tb.DateEntry(self.frame4,bootstyle='danger')
        self.tilld.grid(row=1,column=1,padx=10,pady=10)

        self.entryd.configure()
    
    def variablegrid(self, **kwargs):
            
            self.cmb2=tb.Combobox(self.frame2,bootstyle="danger",values=['customer info','customer statment','customer bought products'],state='readonly')
            
            
            self.cmb2=tb.Combobox(self.frame2,bootstyle="danger",values=['customer info','customer statment','customer bought products'],state='readonly')
            
            
            self.cmb3=tb.Combobox(self.frame2,bootstyle="danger",values=['customer info','customer statment','customer bought products'],state='readonly')
          
            
            
        
#     def build(self):
#    # """Create the row object in the `Treeview` and capture
#     #the resulting item id (iid).
#     #"""
#         self._iid=self.table.insert_rows('end', [[self.cmb1, self.cmb2,self.cmb3]])
#         self.cmb1=tb.Combobox(self.frame2,bootstyle="danger",text="",values=['customer info','customer statment','customer bought products'],state='readonly')
#         if self._iid is None:
#             self._iid = self.view.insert("", END, values=self.values)
#             self._table.iidmap[self.iid] = self

    def add(self):
        #add row to the Tableview
        #self.table.insert_rows(self, 'end', ['mazen','largerthan','chadi'])
        name = ['variable']
        ipcode = ['variable']
        testtt=['variable']
        for i in range(min(len(name), len(ipcode),len(testtt))):
            self.table.insert_row(i,([name[i], ipcode[i],testtt[i]]))

        self.table.load_table_data(clear_filters=False)
    def delete(self):
        #delete row from the Tableview
            row=''
            selected_rows = self.table.get_rows(selected=True)
            print(selected_rows)
            for row in selected_rows:
                row=row.iid
            self.table.delete_rows(None,row,True)
    def set_cell_value(self,event):
            
            selected_rows = self.table.get_rows(selected=True)
            print(selected_rows)
            
            for row in selected_rows:
                row=row.iid
                self.table.configure(row,self.variablegrid())
            print(row)

    
         
              
            
       
if __name__=="__main__":    
    root=tb.Window(themename="superhero")
    obj=CustomerPrint(root)
    root.mainloop()