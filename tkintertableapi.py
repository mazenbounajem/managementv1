#from tkintertable import TableCanvas, TableModel
from tkinter import *
import random
from collections import OrderedDict
from inheritencetktable import TableCanvasEdit
import ttkbootstrap as tb





class Tablesales(Frame):
    """Basic test frame for the table"""

    def __init__(self, parent,frame5,data={}):
        
        self.parent = parent
        self.barcode=''
        
        f = Frame(self.parent)
        f.pack(fill=BOTH,expand=1)
        self.table = TableCanvasEdit(f,frame5, data=data,cellwidth=225, cellbackgr='#e3f698',rowheight=40,)
        

        self.table.show()
        self.table.focus("")
        
            
    