import pyodbc

class connection():
            

            def contogetrows(sql= '',data=[]):
            
                    try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sql)
                    except:
                        print("cant open connection") 
                    else:         

                        for row in cursor:
                            data.append(row)
                        cursor.commit()
                         
            
            def contogetheaders(sqlh='',datah=[]):
                   try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sqlh)
                   except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                   else:
                        
                        #datah = [i[0] for i in cursor.description]
                        for i in cursor.description:
                              datah.append(i[0])
                         
            def insertingtodatabase(sqli='',values=()):
                   try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sqli,values)
                   except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                   else:
                        
                        #datah = [i[0] for i in cursor.description]
                        cursor.commit()      
            def deleterow(sqli='',name=''):
                   try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sqli,name)
                   except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                   else:
                        
                        #datah = [i[0] for i in cursor.description]
                        if cursor.commit()==True:
                              print("deleted")
                         
            def getid(sql='',name=''):# return the id from the table accordint to name
                  
                  try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sql,name)
                  except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                  else:
                       # print('test')
                        #datah = [i[0] for i in cursor.description]
                        result=cursor.fetchall()
                        if result:
                             # print(result)
                              for row in result:
                                    #print(row[0])
                                    return row[0]
            def getrow(sql='',id=0):# return the row from the table accordint to name
                  
                  try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sql,id)
                  except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                  else:
                       # print('test')
                        #datah = [i[0] for i in cursor.description]
                        result=cursor.fetchall()
                        if result:
                             # print(result)
                              for row in result:
                                    #print(row[0])
                                    return row                   
                                  
                  
                              
      
                         
testting= connection.getrow('select * from Product where id=?',2)
#print(testting)
# variable=[]
# query=testting('SELECT * FROM dbo.customer',variable) 
# print (variable)
# testting2=connection.contogetheaders
# variable2=[]
# query2=testting2('SELECT * FROM dbo.customer')
# print(query2)
# getidnew=connection

# name="case study"
# query="select id from category where category_name=?"


# id1=getidnew.getid(sql=query,name=name)
# print(id1)
                  



             