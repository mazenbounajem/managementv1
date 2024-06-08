
from tkinter import *
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from tkinter import PhotoImage

from ttkbootstrap.tooltip import ToolTip

class ControlsClass():
    def controls(first_frame,root,add,save,duplicate,undo,delete,print,refresh,search):    
        #root=tb.Window(themename='superhero')
        canvas=tb.Canvas(width=100, height=100)
        first_frame=tb.Frame(root,padding='1',bootstyle="primary")
        first_frame.place(x=10,y=10)
        icon_new=PhotoImage(file="images/iconsglobal/add.png")
        canvas.create_image(100,100, image=icon_new, state="normal")
        canvas.addimg = icon_new
        
        btn_new = ttk.Button(first_frame,command=add,image=icon_new,bootstyle=('outline'))
        btn_new.grid(row=0,column=1)
        ToolTip(btn_new,text='New',bootstyle="(SUCCESS, INVERSE)")

        saveicon=PhotoImage(file="images/iconsglobal/save.png")
        canvas.create_image(100,100, image=saveicon, state="normal")
        canvas.saveimg = saveicon
        
        btn_save= ttk.Button(first_frame,command=save,image=saveicon,bootstyle=('outline'))
        btn_save.grid(row=1,column=1)
        ToolTip(btn_save,text='Save',bootstyle="(SUCCESS, INVERSE)")


        icon_duplicate=PhotoImage(file="images/iconsglobal/duplicate.png")
        canvas.create_image(100,100, image=icon_duplicate, state="normal")
        canvas.duplicateimg = icon_duplicate
        btn_duplicate = ttk.Button(first_frame,command=duplicate,image=icon_duplicate,bootstyle=('outline'))

        btn_duplicate.grid(row=2,column=1,ipadx=1,ipady=2)
        ToolTip(btn_duplicate,text='DuplicateRecord',bootstyle="(WARNING, INVERSE)")

        icon_undo=PhotoImage(file="images/iconsglobal/undo.png")
        canvas.create_image(50,50, image=icon_undo, state="normal")
        canvas.undoimg = icon_undo
        btn_undo = ttk.Button(first_frame,command=undo,image=icon_undo,bootstyle=('outline'))
        btn_undo.grid(row=3,column=1)
        ToolTip(btn_undo,text='Undo',bootstyle="(WARNING, INVERSE)")
        icon_delete=PhotoImage(file="images/iconsglobal/delete.png")
        canvas.create_image(50,50, image=icon_delete, state="normal")
        canvas.deleteimg = icon_delete
        btn_delete = ttk.Button(first_frame,command=delete,image=icon_delete,bootstyle=('outline'))
        btn_delete.grid(row=4,column=1)
        ToolTip(btn_delete,text='Delete',bootstyle="(DANGER, INVERSE)")

        icon_print=PhotoImage(file="images/iconsglobal/print.png")
        canvas.create_image(50,50, image=icon_print, state="normal")
        canvas.printimg = icon_print
        btn_print = ttk.Button(first_frame,command=print,image=icon_print,bootstyle=('outline'))
        btn_print.grid(row=5,column=1)
        ToolTip(btn_print,text='Print',bootstyle="(SUCCESS, INVERSE)")
        icon_refresh=PhotoImage(file="images/iconsglobal/refresh.png")
        canvas.create_image(50,50, image=icon_refresh, state="normal")
        canvas.refreshimg = icon_refresh
        btn_refresh = ttk.Button(first_frame,command=refresh,image=icon_refresh,bootstyle=('outline'))
        btn_refresh.grid(row=6,column=1)
        ToolTip(btn_refresh,text='Refresh',bootstyle="(SUCCESS, INVERSE)")
        icon_search=PhotoImage(file="images/iconsglobal/search.png")
        canvas.create_image(50,50, image=icon_search, state="normal")
        canvas.searchimg = icon_search
        btn_search= ttk.Button(first_frame,command=search,image=icon_search,bootstyle=('outline'))
        btn_search.grid(row=7,column=1)
        ToolTip(btn_search,text='Search',bootstyle="(SUCCESS, INVERSE)")
        
        