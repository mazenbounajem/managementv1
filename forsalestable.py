import tkinter as tk
from tkinter import Toplevel, ttk
from connection import connection
from tkinter.ttk import Treeview
from pynput import mouse


  

class tabledrop(tk.Toplevel):
    
    
    
    def __init__(self):
        super().__init__()

        
        self.focus_force()
        self.geometry('800x200+500+400')
        
        self.valueofentry=None
        self.frame1=ttk.Frame(self)
        self.frame1.place(x=0,y=0)
        self.frame_main=ttk.Frame(self)
        self.frame_main.grid(row=200,column=100)
        
        self.frame_second=ttk.Frame(self)
        self.frame_second.place(x=0,y=50)
        self.newtable=ttk.Treeview
        
        
        
        def gettable(key):
            self.row=[]
            
            getproductname=connection.contogetrows
            getnames=[]
            getproductname('select id,ProductName,Price,Quantity,Vat from Product ',getnames)
            #print(getnames)

            #print(getnames[0][0])
            #print(type(getnames))
            self.namevar=[]
            
            #print(self.namevar)
            self.newtable=ttk.Treeview(self.frame_second,selectmode='browse',columns=('id','Name','price','quantity'),show='headings',style='success.Treeview',height=5)
            self.newtable.heading('id',text='Code')
            self.newtable.heading('Name',text='Name')
            self.newtable.heading('price',text='Price')
            self.newtable.heading('quantity',text='Quantity')
            for i in range(len(getnames)):
                    self.newtable.insert('',index=i,values=(getnames[i][0],getnames[i][1],getnames[i][2],getnames[i][3],getnames[i][4]))
            self.newtable.grid(row=2,column=0)
            query=entry_name.get().lower()
            for item in self.newtable.get_children():
                values=self.newtable.item(item,"values")
                if query not in values[1].lower():
                    #   newtable.selection_set(data)
                    #   newtable.focus(data)
                    #   newtable.see(data)
                    self.newtable.delete(item)
                    
                    

                else:
                    self.newtable.selection_set(item)
                    self.newtable.focus(item)
                    self.newtable.see(item)
            curItem = self.newtable.focus()
                    
            content= (self.newtable.item(curItem))
            row=content['values'] 
            #print(row)
            self.newtable.bind("<Button-1>",on_click) 
            
            self.newtable.bind_all("<Up>", handle_arrow_keys) 
            self.newtable.bind_all("<Down>", handle_arrow_keys)
            
            #print(key.char)
            self.valueofentry =row
            
        def handle_arrow_keys(event): 
          
            #self.newtable.selection_set(0)
             self.newtable.focus_set()
             self.newtable.bind("<Return>",currentrecord)
           
     
        def on_click(event):
                region_clicked=self.newtable.identify_region(event.x,event.y)
                #print(region_clicked)
                if region_clicked not in ("tree","cell"):
                    return
        
                # which item was double clicked
                column=self.newtable.identify_column(event.x)
                # to start at 1
                column_index=int(column[1:])-1
            # print(column)
                selected_iid=self.newtable.focus()
                selected_values=self.newtable.item(selected_iid)
                row=selected_values.get("values")
                #print(row)
                self.valueofentry = row 
                    
        def currentrecord(event):
              #column=self.newtable.identify_column(event.x)
              selected_iid=self.newtable.focus()
              selected_values=self.newtable.item(selected_iid)
              row=selected_values.get("values")
                #print(row)
              self.valueofentry = row 
              self.valueofentry
              self.destroy()

               
        
        

            
         
        entry_name=ttk.Entry(self.frame1,textvariable='')
        entry_name.pack(side='left')
        entry_name.focus()
        entry_name.bind('<Key>',gettable)

       
        tk1_Button=ttk.Button(self.frame1,text="Select",command=self.clicked)

        tk1_Button.pack(side='left')
        self.deiconify()
        self.transient(self.master)
        #self.grab_set()
        self.wait_window(self) 
          

    def clicked(self):
         self.valueofentry
         self.destroy()  