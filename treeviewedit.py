import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
#from tabletouse import exampletree

class TreeviewEdit(tb.Treeview):
   
    
    def __init__(self,master,**kwargs):
        super().__init__( master,**kwargs)

        s=ttk.Style()
        s.configure('tb.Treeview',rowheight=100)
        

        self.bind("<Button-1>",self.on_click)
    def on_click(self,event):
        print("Double-clicked")
        # identify the region that double clicke
        region_clicked=self.identify_region(event.x,event.y)
        print(region_clicked)


        if region_clicked not in ("tree","cell"):
            return
        
        # which item was double clicked
        column=self.identify_column(event.x)
        # to start at 1
        column_index=int(column[1:])-1
        print(column)
        selected_iid=self.focus()
        selected_values=self.item(selected_iid)
        print(selected_values)
        
        if column=="#0":
            selected_text=selected_values.get("text")
        else:
            selected_text=selected_values.get("values")[column_index]
        #print(selected_text)
        column_box = self.bbox(selected_iid,column)
        #print(column_box)

        

        entry_edit=tb.Entry()
        # record the column index and item iid
        entry_edit.editing_column_index=column_index
        entry_edit.editing_item_iid=selected_iid
        entry_edit.insert(0,selected_text)
        entry_edit.select_range(0,tk.END)
        entry_edit.focus()
        entry_edit.bind("<FocusOut>",self.on_focus_out)
        entry_edit.bind("<Return>",self.on_enter_pressed)
        

        entry_edit.place(x=column_box[0],
                         y=column_box[1],
                         width=column_box[2],
                         height=column_box[3])
    def on_focus_out(self,event):
        event.widget.destroy()

    def on_enter_pressed(self,event):
        new_text = event.widget.get()
        # Such as I002
        selected_iid=event.widget.editing_item_iid
        #such as -1 tree column ,0 first self_defind column,etc.
        column_index = event.widget.editing_column_index
        if column_index == -1:
            self.item(selected_iid,text=new_text)
        else:
            current_values = self.item(selected_iid).get("values") 
            current_values[column_index] = new_text
            self.item(selected_iid,values=current_values)
            print(current_values)
        event.widget.destroy() 