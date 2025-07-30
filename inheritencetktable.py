from tkintertable import TableCanvas, TableModel
from tkintertable.TableFormula import Formula
from tkinter import *
from tkinter import ttk
from forsalestable import tabledrop
from connection import connection


import emoji
class TableCanvasEdit(TableCanvas):
    
    def __init__(self, master,frame5,data,**kwargs):
            super().__init__( master,frame5,data,**kwargs)
            self.editable = True
            self.createMenuBar
            self.multiplerowlist=[] 
            self.multiplecollist=[]
            self.height=50
            self.salesamt=IntVar()
            
            self.buttonminus=Button(frame5,command=self.deleteRow,text= f'{emoji.emojize(":minus:")}')
            self.buttonminus.grid(row=0,column=1)
            self.buttonback=Button(frame5,command=self.gotoprev,text= f'{emoji.emojize(":BACK_arrow:")}')
            self.buttonback.grid(row=0,column=2)
            self.buttonsoon=Button(frame5,command=self.gotonext,text= f'{emoji.emojize(":SOON_arrow:")}')
            self.buttonsoon.grid(row=0,column=3)
            self.buttonadd=Button(frame5,command=self.addarow,text= f'{emoji.emojize(":plus:")}')
            self.buttonadd.grid(row=0,column=4)
            self.entryqtynorecords=Label(frame5,font=('times new roman','15'),bg='green',fg='black')
            self.entryqtynorecords.grid(row=0,column=5,padx=300)
            self.entrysummation=Label(frame5,font=('times new roman','15'),bg='green',fg='black')
            self.entrysummation.grid(row=0,column=6,padx=600)
            self.values=[]
            self.rowandquantity()
            self.sumquantity()
            self.row=0
            self.row1=1
            
    def do_bindings(self): 
             
                    self.bind("<Button-1>",self.handle_left_click) 
                    self.bind("<Double-Button-1>",self.handle_double_click) 
                    self.bind("<Control-Button-1>", self.handle_left_ctrl_click) 
                
                    self.bind("<Shift-Button-1>", self.handle_left_shift_click) 
                    self.bind("<ButtonRelease-1>", self.handle_left_release) 
                    if self.ostyp=='mac': 
                        #For mac we bind Shift, left-click to right click 
                        self.bind("<Button-2>", self.handle_right_click) 
                        self.bind('<Shift-Button-1>',self.handle_right_click) 
                    else: 
                        self.bind("<Button-3>", self.handle_right_click) 
                
                    self.bind('<B1-Motion>', self.handle_mouse_drag) 
                    self.bind('<Motion>', self.handle_motion) 
                
                    self.bind_all("<Control-x>", self.deleteRow) 
                    self.bind_all("<Control-n>", self.addRow) 
                    self.bind_all("<Delete>", self.clearData) 
                    self.bind_all("<Control-v>", self.paste) 
                
                    #if not hasattr(self,'parentapp'): 
                    #    self.parentapp = self.parentframe 
                
                    self.parentframe.master.bind_all("<Right>", self.handle_arrow_keys) 
                    self.parentframe.master.bind_all("<Left>", self.handle_arrow_keys) 
                    self.parentframe.master.bind_all("<Up>", self.handle_arrow_keys) 
                    self.parentframe.master.bind_all("<Down>", self.handle_arrow_keys) 
                    self.parentframe.master.bind_all("<KP_8>", self.handle_arrow_keys) 
                    self.parentframe.master.bind_all("<Return>", self.handle_arrow_keys) 
                    self.parentframe.master.bind_all("<Tab>", self.handle_arrow_keys) 
                    #if 'windows' in self.platform: 
                    self.bind("<MouseWheel>", self.mouse_wheel) 
                    self.bind('<Button-4>', self.mouse_wheel) 
                    self.bind('<Button-5>', self.mouse_wheel) 
                    self.focus_set() 
                    return 
    def handle_arrow_keys(self, event): 
          """Handle arrow keys press""" 
          #print event.keysym 
   
          row = self.get_row_clicked(event) 
          col = self.get_col_clicked(event) 
          x,y = self.getCanvasPos(self.currentrow, 0) 
          if x == None: 
              return 
   
          if event.keysym == 'Up': 
              if self.currentrow == 0: 
                  return 
              else: 
                  #self.yview('moveto', y) 
                  #self.tablerowheader.yview('moveto', y) 
                  self.currentrow  = self.currentrow -1 
          elif event.keysym == 'Down': 
              if self.currentrow >= self.rows-1: 
                  return 
              else: 
                  #self.yview('moveto', y) 
                  #self.tablerowheader.yview('moveto', y) 
                  self.currentrow  = self.currentrow +1 
          elif event.keysym == 'Right' or event.keysym == 'Return': 
              if self.currentcol >= self.cols-1: 
                  if self.currentrow < self.rows-1: 
                      self.currentcol = 0 
                      self.currentrow  = self.currentrow +1 
                  else: 
                      return 
              else: 
                  self.currentcol  = self.currentcol +1 
          elif event.keysym == 'Left':
              if self.currentcol==0:
                   return 
              self.currentcol  = self.currentcol -1 
          self.drawSelectedRect(self.currentrow, self.currentcol) 
          coltype = self.model.getColumnType(self.currentcol) 
          if coltype == 'text' or coltype == 'number': 
              self.delete('entry') 
              self.drawCellEntry(self.currentrow, self.currentcol) 
          return            
    def drawCellEntry(self, row, col, text=None): 
          """When the user single/double clicks on a text/number cell, bring up entry window""" 
   
          if self.editable == False: 
              return 
          #absrow = self.get_AbsoluteRow(row) 
          h=self.rowheight 
          model=self.getModel() 
          cellvalue = self.model.getCellRecord(row, col) 
          if Formula.isFormula(cellvalue): 
              return 
          else: 
              text = self.model.getValueAt(row, col) 
          x1,y1,x2,y2 = self.getCellCoords(row,col) 
          w=x2-x1 
          #Draw an entry window 
          txtvar = StringVar() 
          txtvar.set(text) 
          codevar=StringVar()
          codevar.set(text)
          quantityvar=StringVar()
          #quantityvar.set(1)
          discvar=StringVar()
          def callback(e): 
              value = txtvar.get() 
              if value == '=': 
                  #do a dialog that gets the formula into a text area 
                  #then they can click on the cells they want 
                  #when done the user presses ok and its entered into the cell 
                  self.cellentry.destroy() 
                  #its all done here.. 
                  self.formula_Dialog(row, col) 
                  return 
   
              coltype = self.model.getColumnType(col) 
              if coltype == 'number': 
                  sta = self.checkDataEntry(e) 
                  if sta == 1: 
                      model.setValueAt(value,row,col) 
              elif coltype == 'text': 
                  model.setValueAt(value,row,col) 
   
              color = self.model.getColorAt(row,col,'fg') 
              self.drawText(row, col, value, color, align=self.align) 
              if e.keysym=='Return': 
                  self.delete('entry') 
                  #self.drawRect(row, col) 
                  #self.gotonextCell(e) 
              return
          #for creating a table drop
          def createobject(e):


            mycustomizedtable = tabledrop() 
            
            
           
            
            
            
            valuesfromproduct = mycustomizedtable.valueofentry
            #print(valuesfromproduct)
            self.model.setValueAt(valuesfromproduct[0],row,0) 
            self.model.setValueAt(valuesfromproduct[1],row,1) 
            
            self.model.setValueAt(1,row,2) 
            self.model.setValueAt(valuesfromproduct[4],row,3) 
            self.model.setValueAt(float(valuesfromproduct[2]),row,4) 
            self.model.setValueAt(0,row,5) 
            subtotal=1*(float(valuesfromproduct[2]))
            self.model.setValueAt(subtotal,row,6)
           # self.model.addRow()
            self.redraw()
        # for getting values whe entering code data
          def datafromcode(e):
                codevar=txtvar.get()
                if codevar == "":
                     pass
                else:
                    record=[]
                    getlineofcode=connection
                    record=getlineofcode.getrow('select id,ProductName,Quantity,Vat,price from Product where id=?',codevar)
                    #print(record)
                    self.model.setValueAt(record[0],row,0) 
                    self.model.setValueAt(record[1],row,1) 
                    self.model.setValueAt(1,row,2) 
                    self.model.setValueAt(int(record[3]),row,3) 
                    self.model.setValueAt(float(record[4]),row,4) 
                    self.model.setValueAt(0,row,5) 
                    self.model.setValueAt(float(record[4]),row,6) 

                    self.setSelectedCol(4)
                noofrows=self.model.getRowCount()
               # print(self.row,noofrows)
                if   (noofrows-self.row1)==1:
                        self.row1=self.row1 +1
                        self.model.addRow()
                    
                   # self.model.addRow()
                self.redraw()
          def thequantity(e):
             # print('the value of me is ',quantityvar.get())
              if quantityvar.get() != 1 :
                   varqty=quantityvar.get()
                   self.model.setValueAt(varqty,row,2)
                   self.redrawCell(row,col)
                   thenewquantity= quantityvar.get()
                   price=self.model.getValueAt(row,4)
                   if thenewquantity != '':  
                       # int(thenewquantity)
                     #   print(type(thenewquantity))
                       # int(price)
                      #  print(type(price))
                        subtotal=float(thenewquantity)*float(price)
                      #  print(subtotal)
                        
                        self.model.setValueAt(subtotal,row,6)
                        self.cellentry.icursor(END)
                        self.sumquantity()
                        self.redrawCell(row,6)
                        
          def thediscount(e):
                #print('the value of me is ',discvar.get())
                
                     
                if discvar.get() != 0 :
                     vardisc=discvar.get()
                     self.model.setValueAt(vardisc,row,5)
                     self.redrawCell(row,col)
                     varqty=self.model.getValueAt(row,2)
                     price=self.model.getValueAt(row,4)
                     discnew=discvar.get()
                     if discnew != '':
                        #  print(discnew,type(discnew),varqty,price)

                          discnewfloatpercent=1-(float(discnew)/100)
                          subtotalwithdisc=(float(varqty)*float(price))*discnewfloatpercent
                        #  print(subtotalwithdisc)
                          self.model.setValueAt(subtotalwithdisc,row,6)
                          self.cellentry.icursor(END)
                          self.redrawCell(row,6)
                if discvar.get() =='':
                     self.model.setValueAt(0,row,5)
                     self.redrawCell(row,5)



                   
               
                     
          if col == 0:
                    self.cellentry=Entry(self.parentframe,textvariable=txtvar,bg=self.entrybackgr, 
                          relief=FLAT, 
                          takefocus=1, 
                          font=self.thefont) 
                    #self.cellentry.icursor(END) 
                    self.cellentry.focus_set()
                    #self.cellentry.bind('<Enter>', createobject)
                    self.cellentry.bind('<Return>', datafromcode)
                    self.entrywin=self.create_window(x1+self.inset,y1+self.inset, 
                                  width=w-self.inset*2,height=h-self.inset*2, 
                                  window=self.cellentry,anchor='nw', 
                                  tag='entry') 
                    return 
                     
                  

               

          if  col == 1:
                # self.cellentry=ttk.Combobox(self.parentframe,width=20, 
                #           textvariable=txtvar, 
                #           values=['apple','bannan','orange'],
                #           takefocus=1, 
                #           ) 
                # self.cellentry.icursor(END) 
                # self.cellentry.bind('<Return>', callback) 
                # self.cellentry.bind('<KeyRelease>', callback) 
                # self.cellentry.focus_set() 
                # self.entrywin=self.create_window(x1+self.inset,y1+self.inset, 
                #                         width=w-self.inset*2,height=h-self.inset*2, 
                #                         window=self.cellentry,anchor='nw', 
                #   return
                
                    self.cellentry=Entry(self.parentframe,textvariable=txtvar,bg=self.entrybackgr, 
                          relief=FLAT, 
                          takefocus=1, 
                          font=self.thefont) 
                    #self.cellentry.icursor(END) 
                    self.cellentry.focus_set()
                    self.cellentry.bind('<Enter>', createobject)
                    self.cellentry.bind('<Return>', createobject)
                    self.cellentry.bind("<space>", createobject)
                    self.entrywin=self.create_window(x1+self.inset,y1+self.inset, 
                                  width=w-self.inset*2,height=h-self.inset*2, 
                                  window=self.cellentry,anchor='nw', 
                                  tag='entry') 
                    self.focus_displayof()
                    return
          if col == 2:
                    self.cellentry=Entry(self.parentframe,textvariable=quantityvar,bg=self.entrybackgr, 
                          relief=FLAT, 
                          takefocus=1, 
                          font=self.thefont) 
                    #self.cellentry.icursor(END) 
                    self.cellentry.focus_set()
                    #self.cellentry.bind('<Enter>', createobject)
                    self.cellentry.bind('<Return>', thequantity)
                    self.entrywin=self.create_window(x1+self.inset,y1+self.inset, 
                                  width=w-self.inset*2,height=h-self.inset*2, 
                                  window=self.cellentry,anchor='nw', 
                                  tag='entry') 
                    return 
          if col==4:
               return
          if col ==5:
               self.cellentry=Entry(self.parentframe,textvariable=discvar,bg=self.entrybackgr,relief=FLAT,takefocus=1,font=self.thefont)
               self.cellentry.focus_set()
               self.cellentry.bind('<Return>', thediscount)
               self.entrywin=self.create_window(x1+self.inset,y1+self.inset, 
                                  width=w-self.inset*2,height=h-self.inset*2, 
                                  window=self.cellentry,anchor='nw', 
                                  tag='entry') 
               return 

          if col == 6:
               if self.model.getValueAt(row,col) !='':
                    noofrows=self.model.getRowCount()
                    print('number of rows',self.row ,'number of row count',noofrows)
                    if   (noofrows-self.row)==1:
                        self.row=self.row +1
                       
                        self.model.addRow()
                    
                    
                   
                    
                    self.sumquantity()
                    self.redraw()
               else:
                    return     
              

          
          else:
               
                self.cellentry=Entry(self.parentframe,width=20, 
                                textvariable=txtvar, 
                                bg=self.entrybackgr, 
                                relief=FLAT, 
                                takefocus=1, 
                                font=self.thefont) 
                self.cellentry.icursor(END) 
                self.cellentry.bind('<Return>', callback) 
                self.cellentry.bind('<KeyRelease>', callback) 
                self.cellentry.focus_set() 
                self.entrywin=self.create_window(x1+self.inset,y1+self.inset, 
                                        width=w-self.inset*2,height=h-self.inset*2, 
                                        window=self.cellentry,anchor='nw', 
                                        tag='entry') 
                return
          
          
   
          
         
    def handle_left_click(self, event): 
           """Respond to a single press""" 
           #which row and column is the click inside? 
           self.clearSelected() 
           self.allrows = False 
           rowclicked = self.get_row_clicked(event) 
           colclicked = self.get_col_clicked(event) 
           #print(rowclicked,colclicked)
           self.focus_set() 
           if self.mode == 'formula': 
               self.handleFormulaClick(rowclicked, colclicked) 
               return 
           if hasattr(self, 'cellentry'): 
                self.cellentry.destroy() 
            #ensure popup menus are removed if present 
           if hasattr(self, 'rightmenu'): 
                self.rightmenu.destroy() 
           if hasattr(self.tablecolheader, 'rightmenu'): 
                self.tablecolheader.rightmenu.destroy() 
        
           self.startrow = rowclicked 
           self.endrow = rowclicked 
           self.startcol = colclicked 
           self.endcol = colclicked 
            #reset multiple selection list 
           self.multiplerowlist=[] 
           self.multiplerowlist.append(rowclicked) 
           if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols: 
                self.setSelectedRow(rowclicked) 
                self.setSelectedCol(colclicked) 
                self.drawSelectedRect(self.currentrow, self.currentcol) 
                self.drawSelectedRow() 
                self.tablerowheader.drawSelectedRows(rowclicked) 
                coltype = self.model.getColumnType(colclicked) 
                if coltype == 'text' or coltype == 'number': 
                    self.drawCellEntry(rowclicked, colclicked) 
           return 
    def createMenuBar(self):
    #"""Create the menu bar for the application. """

        self.menu=Menu(self.tablesapp_win)
        self.proj_menu={'01New':{'cmd':self.new_project},
                        '02Open':{'cmd':self.open_project},
                        '03Close':{'cmd':self.close_project},
                        '04Save':{'cmd':self.save_project},
                        '05Save As':{'cmd':self.save_as_project},
                        '06Preferences..':{'cmd':self.showPrefsDialog},
                        '08Quit':{'cmd':self.quit}}
        if self.parent:
            self.proj_menu['08Return to Database']={'cmd':self.return_data}
        self.proj_menu=self.create_pulldown(self.menu,self.proj_menu)
        self.menu.add_cascade(label='Project',menu=self.proj_menu['var'])

        self.records_menu={'01Add Row':{'cmd':self.add_Row},
                        '02Delete Row':{'cmd':self.delete_Row},
                        '03Add Column':{'cmd':self.add_Column},
                        '04Delete Column':{'cmd':self.delete_Column},
                        '05Auto Add Rows':{'cmd':self.autoAdd_Rows},
                        '06Auto Add Columns':{'cmd':self.autoAdd_Columns},
                        '07Find':{'cmd':self.createSearchBar},
                        }
        self.records_menu=self.create_pulldown(self.menu,self.records_menu)
        self.menu.add_cascade(label='Records',menu=self.records_menu['var'])

        self.sheet_menu={'01Add Sheet':{'cmd':self.add_Sheet},
                        '02Remove Sheet':{'cmd':self.delete_Sheet},
                        '03Copy Sheet':{'cmd':self.copy_Sheet},
                        '04Rename Sheet':{'cmd':self.rename_Sheet},
                        }
        self.sheet_menu=self.create_pulldown(self.menu,self.sheet_menu)
        self.menu.add_cascade(label='Sheet',menu=self.sheet_menu['var'])

        self.IO_menu={'01Import from csv file':{'cmd':self.import_csv},
                    '02Export to csv file':{'cmd':self.export_csv},
                    }

        self.IO_menu=self.create_pulldown(self.menu,self.IO_menu)
        self.menu.add_cascade(label='Import/Export',menu=self.IO_menu['var'])

        # Help menu
        self.help_menu={'01Online Help':{'cmd':self.online_documentation},
                        '02About':{'cmd':self.about_Tables}}
        self.help_menu=self.create_pulldown(self.menu,self.help_menu)
        self.menu.add_cascade(label='Help',menu=self.help_menu['var'])

        self.tablesapp_win.config(menu=self.menu)

        return
    def deleteRow(self):
         rowclicked=self.getSelectedRow()
         
         print(rowclicked)
         deletedrow=self.model.getRecordAtRow(rowclicked)
         print(deletedrow)
         self.model.deleteRow(rowIndex=rowclicked)
         self.row=self.row-1
         
         self.redraw()
         self.gotoprevRow()
         self.focus_set()
         self.sumquantity()
    def gotoprev(self):
         self.gotoprevRow()
         self.focus_set()
    def gotonext(self):
         self.gotonextRow()
         self.focus_set()
    def addarow(self):
         self.model.addRow()
         self.redraw()
         self.gotonextRow()
         
         
         self.focus_set()
         self.drawCellEntry(self.row,self.cols)
    def rowandquantity(self):
         rowcount=self.model.getRowCount() 
         
         self.quantityvalues=self.model.getColCells(2)
         #print(self.quantityvalues)
              
       #  print(rowcount)
         self.entryqtynorecords.configure(text=rowcount)
         #self.entryqtynorecords.config(text=rowcount)
    def sumquantity(self):
         self.values=self.model.getAllCells()
       #  print('the sum of quantity is=')  
         print(self.values)
         getsumofsubtotal=[]
         for row in self.values:
              getsumofsubtotal.append(self.values[row][6])      
         if getsumofsubtotal != '':
              for value in getsumofsubtotal:
                   if type(value)==str:
                        getsumofsubtotal.remove(value)
        # print(getsumofsubtotal)
         Sum=sum(getsumofsubtotal)
         #print(Sum)
         self.entrysummation.configure(text=Sum)
         self.salesamt=Sum
         # print(self.salesamt)
    def getsalesvalues(self):
         salesvalues=self.salesamt
        # print(salesvalues)
         if salesvalues==0:
              
              return
         
         return salesvalues
    def cleardata(self):
         x=self.model.getRowCount()

         print(x)
         self.model.deleteRows()
         
         self.entrysummation.configure(text=0)
         
         
         self.redraw()
         
        
        
         self.addRow()
        


         
         self.setSelectedRow(0)
         
         self.row=0
         self.row1=0
    def getallvalues(self):
         if self.model.getAllCells !='':
              
            alldata=self.model.getAllCells()
            #print(alldata)

            return alldata
         else:
              return
            