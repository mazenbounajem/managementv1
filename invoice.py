from tkinter import *
import ttkbootstrap as tb
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from ttkbootstrap.constants import * 
from tkinter import messagebox
 

from controls import ControlsClass
from createtable import CreateTableClass
from connection import connection
from treecustomized import tabledrop

from tkintertableapi import Tablesales
class InvoiceClass():
    def __init__(self,root):
        self.root = root
        self.root.title("Sales Invoice")
        
        

        self.discountentry=IntVar()
        self.discountamount=IntVar()
        self.salesamount=IntVar()
        self.vatamount=IntVar()
        self.totalamount=IntVar()
        totalsales=None

        self.frame1=tb.Frame()
        controlsget=ControlsClass
        controlsget.controls(self.frame1,self.root,self.add,self.save,self.duplicate,self.undo,self.delete,self.print,self.refresh,self.search)
        

        self.frame2=tb.Frame()
        self.frame2.pack(padx=150,fill='x')
        self.createtablenew=CreateTableClass


        self.frame3=tb.Frame()
        self.frame3.pack(padx=150,fill='x')
        
        self.enterdate=tb.Label(self.frame3,text="Date")
        self.enterdate.pack(side='left')
        self.entryd=tb.DateEntry(self.frame3,bootstyle='info')
        self.entryd.pack(side='left')
        getcustomername=connection.contogetrows
        getnames=[]
        getcustomername('select customerName,phone from customer',getnames)
        #print(getnames)

        #print(getnames[0][0])
        #print(type(getnames))
        self.namevar=[]
        #self.namevar = self.display_list(getnames)
        # print(self.namevar)
        

        lbl_name=tb.Label(self.frame3,bootstyle="info",text="Name:")
        lbl_name.pack(side='left',padx=20)

        self.var_option_value=StringVar()
        self.varcustomerid=StringVar()
        
        self.var_customername=StringVar() 
        self.var_phone=StringVar()       
                
        def createobject(event):
            
            mycustomizedtable = tabledrop() 
            
            
            fillnameandphone = mycustomizedtable.valueofentry
            self.varcustomerid.set(fillnameandphone[0])
            self.var_customername.set(fillnameandphone[1])
            self.var_phone.set(fillnameandphone[2])
        
        self.entry_name=tb.Entry(self.frame3,textvariable=self.var_customername,bootstyle="Success")
        self.entry_name.pack(side='left',padx=20)
        self.entry_name.bind('<Button -1>',createobject)
        
        #self.entry_name.bind('<Return>',self.get_pname_fromdata)


        

        lbl_phone=tb.Label(self.frame3,bootstyle="info",text="Phone:")
        lbl_phone.pack(side='left',padx=20)
        
        self.entry_phone=tb.Entry(self.frame3,textvariable=self.var_phone,bootstyle="info",state=DISABLED,font=('times new roman','12'),foreground='white')
        self.entry_phone.pack(side='left',padx=20)

        
        
        
        self.lbl_currency=tb.Label(self.frame3,bootstyle="info",text="Currency")
        self.lbl_currency.pack(side='left',padx=20)

        self.currency_cmb=tb.Combobox(self.frame3,bootstyle='Danger',values=(['Usd','LBP']))
        self.currency_cmb.current(0)
        self.currency_cmb.pack(side='left')


        frame4=tb.Frame(self.root)
        frame4.pack(padx=150,fill='x',pady=30)

        frame5=tb.Frame(frame4)
        frame5.pack(side='bottom',fill='x',padx=40,pady=0)

        self.frame6=tb.Frame()
        self.frame6.pack(anchor='e',padx=150)
        self.labledisc=tb.Label(self.frame6,text='Disc%',bootstyle='info')
        self.labledisc.pack(side='left')
        self.entrydisc=tb.Entry(self.frame6,textvariable=self.discountentry,bootstyle='info',width=5)
        self.entrydisc.pack(side='left')
        self.entrydiscamount=tb.Entry(self.frame6,textvariable=self.discountamount,bootstyle='info')
        self.entrydiscamount.pack(side='left',padx=10)
        
        self.frame7=tb.Frame()
        self.frame7.pack(anchor='e',padx=160,pady=2)
        self.lablesalesamt=tb.Label(self.frame7,text='SalesAmt:',bootstyle='info')
        self.lablesalesamt.pack(side='left',padx=40)
        self.entrysalesamt=tb.Entry(self.frame7,textvariable=self.salesamount,bootstyle='info')
        self.entrysalesamt.pack(side='left')


        self.frame8=tb.Frame()
        self.frame8.pack(anchor='e',padx=160,pady=2)
        self.lablevat=tb.Label(self.frame8,text='VatAmt:',bootstyle='info')
        self.lablevat.pack(side='left',padx=40)
        self.entryvatamt=tb.Entry(self.frame8,textvariable=self.vatamount,bootstyle='info')
        self.entryvatamt.pack(side='left')


        self.frame9=tb.Frame()
        self.frame9.pack(anchor='e',padx=160,pady=2)
        self.labletotal=tb.Label(self.frame9,text='Total:',bootstyle='info')
        self.labletotal.pack(side='left',padx=40)
        self.entrytotal=tb.Entry(self.frame9,textvariable=self.totalamount,bootstyle='info')
        self.entrytotal.pack(side='left')

        

        

        

        #####################################pip install tkintertable   to try it#######################3
        
        data ={'main':{'code':None,'Discription':None,'Quantity':None,'Vat':None,'UnitPrice':None,'Discount':None,'Subtotal':None}

        }
        self.table=Tablesales(frame4,frame5,data=data)


        
        self.root.bind('<Return>',self.getthetotal)
       # self.table.bind_class("Lable","<Return>")
        
        
        
       
        
        





        self.tablesales()
    ########main table#####################
    def set_cell_value(self,event):
        if event:
            
            print(event)
            
        
            
            
             
    def tablesales(self):  
        datafromdatabase=[]
        columns=[]
        sqltoselectheaders= 'select * from Sales'
        sqltoselectcolumns='select id,UserId,CustomerId,CurrencyId,Date,Subtotal,DiscountPercent,DiscountValue,TotalVat,TotalVatInLocalCurrency,Total from Invoice order by id desc'
        

        self.createtablenew.create_table(datafromdatabase,columns,sqltoselectheaders,sqltoselectcolumns)
        self.datafromdatabase=datafromdatabase
        self.columns=columns
        
        
        #print(type(self.table))
        self.tableview =Tableview( master=self.frame2, coldata=self.columns, rowdata=self.datafromdatabase[0], paginated=True, pagesize=12, height=8, searchable=True, autofit=False,
                bootstyle=PRIMARY,
                stripecolor=(None, None),                  
        )
        
        self.tableview.pack(fill='x',expand=100)    
###### functions ########################
        
    def add(self):
        print("add")

        self.var_customername.set('Cash Client')
       
        #self.table.table.bind_class("<Return>",'Tablesales',self.table.table.drawCellEntry(0,0))
        self.table.table.drawCellEntry(0,0)

        
    def save(self):
        print('save')
        wholetablecells=self.table.table.getallvalues()
       # print(wholetablecells)
       # print(type(wholetablecells))

        wholetablecells.pop(len(wholetablecells)-1)
        print(wholetablecells)

        #print(self.var_customername.get())
        customername=self.var_customername.get()
        customerphone=self.var_phone.get()
        currency=self.currency_cmb.get()
        total=self.salesamount.get()

        print(customername,customerphone,currency,total)

        insertingsales=connection.insertingtodatabase
        try:
            messagebox.askquestion('Question','here you are what you want to do')

        except:
            messagebox.askyesnocancel('your answer','I was not satisfied with your answer')    
        
        
       
        
    def duplicate(self):
        print('add')
    def undo(self):
        print('undo')
        if True: 
           ask= messagebox.askyesno('Undo',"Are you sure you want to undo")
           print(ask)
           if ask==True:
               print('yes')
               self.table.table.cleardata()
               self.var_customername.set('')
               self.salesamount.set(0)
               self.table.table.redraw()
               
               self.table.table.drawSelectedRect(0,0)
               
               
               
               
               
           else:
               print('No')    

            
    
    def delete(self):
        print('add')
    def print(self):
        print('add')
    def refresh(self):
        pass
        
        
    def search(self):
        print('add')

    def getthetotal(self,e): 
         if self.table.table.row>0:
            
            sales=self.table.table.getsalesvalues()
            self.salesamount.set(sales)   
                                    







if __name__=="__main__":
    root = tb.Window(themename="superhero")
    width= root.winfo_screenwidth() 
    height= root.winfo_screenheight()
    
    root.geometry("%dx%d" % (width, height))
    obj = InvoiceClass(root)
    root.mainloop()