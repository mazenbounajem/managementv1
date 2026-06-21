from tkinter import *
from ttkbootstrap.style import *
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from connection import connection

class CreateTableClass():
    
          
        
          
    def create_table(datafromdatabase=[],columns=[],sql1='',sql2=''):
            
            
            
            
            getdatacategory= connection.contogetrows
            getdatacategoryall=[]
            getdatacategory(sql1,getdatacategoryall)
           # print(getdatacustomerall)
            datafromdatabase.append(getdatacategoryall)
            #row_data = [
            #    ('mazen','1','ghaboun','76352915','mazenbounajem@gmail.com','2024-05-17','2024-05-17','2024-05-17','100000','1')
             #   ]
            

            getcolumnnames=connection.contogetheaders
            getheaderscategory=[]
            getheaders=getcolumnnames(sql2,getheaderscategory)
          
            for row in getheaderscategory:
                  columns.append(row)
                  
            
            
            
            

       
 
    
                
          
             
                        
      