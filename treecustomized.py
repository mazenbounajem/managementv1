import tkinter as tk
from tkinter import Toplevel, ttk
from connection import connection
from tkinter.ttk import Treeview
from pynput import mouse


  

class tabledrop(tk.Toplevel):
    
    
    
    def __init__(self):
        super().__init__()

        
        
        self.geometry('400x200+500+400')
        
        self.valueofentry=None
        self.frame_main=ttk.Frame(self)
        self.frame_main.grid(row=200,column=100)
        
        self.frame_second=ttk.Frame(self)
        self.frame_second.grid(row=300,column=100)
        
        
        
        def gettable(key):
            self.row=[]
            
            getcustomername=connection.contogetrows
            getnames=[]
            getcustomername('select id,customerName,phone from customer',getnames)
            #print(getnames)

            #print(getnames[0][0])
            #print(type(getnames))
            self.namevar=[]
            
            #print(self.namevar)
            self.newtable=ttk.Treeview(self.frame_second,columns=( 'id','Name','Phone'),show='headings',style='success.Treeview',height=5)
            self.newtable.heading('Name',text='Name')
            self.newtable.heading('Phone',text='Phone')
            for i in range(len(getnames)):
                    self.newtable.insert('',index=i,values=(getnames[i][0],getnames[i][1],getnames[i][2]))
            self.newtable.grid(row=2,column=0)
            query=entry_name.get().lower()
            for item in self.newtable.get_children():
                values=self.newtable.item(item,"values")
                if query not in values[0].lower():
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
            #print(key.char)
            self.valueofentry =row
            
            
            
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
                    
                    
               
        
        

            
              
        entry_name=ttk.Entry(self.frame_main,textvariable='')
        entry_name.grid(row=1,column=0)
        entry_name.bind('<Key>',gettable)

       
        tk1_Button=ttk.Button(self.frame_main,text="Select",command=self.clicked)

        tk1_Button.grid(row=1,column=1)
        self.transient(self.master)
        self.grab_set()
        self.wait_window(self) 
          

    def clicked(self):
         self.valueofentry
         self.destroy()  
      
    
         
         
                 
        




           
           

                
# if __name__=="__main__":
   
#     root= tk.Tk()
#     # def createobject(event):
#     #     obj=tabledrop(root,entryname)          
#     # entryname=ttk.Entry(root)
#     # entryname.grid(row=0,column=0)
#     # entryname.bind('<Button -1>',createobject)
#     #entryname.grid(row=1,column=1)
    
#     root.mainloop()
    





    
   