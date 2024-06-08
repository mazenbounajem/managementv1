from tkinter import *
from ttkbootstrap.style import *
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from connection import connection

class CreateTableClass():
    
          
        
          
    def create_table(datafromdatabase=[],columns=[]):
            
            
            
            
            getdatacategory= connection.contogetrows
            getdatacategoryall=[]
            getdatacategory('select * from category order by id desc',getdatacategoryall)
           # print(getdatacustomerall)
            datafromdatabase.append(getdatacategoryall)
            #row_data = [
            #    ('mazen','1','ghaboun','76352915','mazenbounajem@gmail.com','2024-05-17','2024-05-17','2024-05-17','100000','1')
             #   ]
            

            getcolumnnames=connection.contogetheaders
            getheaderscategory=[]
            getheaders=getcolumnnames('select * from category',getheaderscategory)
          
            for row in getheaderscategory:
                  columns.append(row)
                  
            
            
            
            

       
 
    
                
          
             
                        
      