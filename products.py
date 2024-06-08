import ttkbootstrap as tb
from controls import ControlsClass

class ProductsCass():
    def __init__(self, root):
        self.root = root
        self.root.title("Products")
        #frame 1 is taken by parameter to class controls
        self.frame1=tb.Frame(self.root)
        controlsget=ControlsClass
        controlsget.controls(self.frame1,self.root,self.add,self.save,self.duplicate,self.undo,self.delete,self.print,self.refresh,self.search)
    
    
    ############################ define a treeview widget to get data for the products#################################
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    #functions to controls.py defined in class controlsclass with function controls taken as parameters    
    def add(self):
            print("you click add")
    def save(self):
            print("you click save")
    def duplicate(self):
            print("you click duplicat")
    def undo(self):
            print("you click undo")                
    def delete(self):
            print("you click delete")
    def print(self):
            print("you click print") 
    def refresh(self):
            print("you click refresh")  
    def search(self):
            print("you click search")                               
if __name__=="__main__":
    root = tb.Window(themename="superhero")
    width= root.winfo_screenwidth() 
    height= root.winfo_screenheight()
    root.geometry("%dx%d" % (width, height))
    obj = ProductsCass(root)
    root.mainloop()
        
        