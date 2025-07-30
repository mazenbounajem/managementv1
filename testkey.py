
import tkinter as tk

def key_handler(Key):
    if Key:
        print(Key)
        print(Key.char)

r = tk.Tk()
t = tk.Text()
t.pack()
r.bind('<Key>', key_handler)
r.mainloop()