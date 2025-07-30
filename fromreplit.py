import tkinter as tk
from tkinter import ttk

class App:
    def __init__(self, master):
        self.master = master
        master.title("Treeview with Dropdown")

        # Create a frame for the dropdown
        dropdown_frame = tk.Frame(master)
        dropdown_frame.pack(pady=10)

        # Create a dropdown list
        options = ["Option 1", "Option 2", "Option 3"]
        self.dropdown = ttk.Combobox(dropdown_frame, values=options)
        self.dropdown.pack(side=tk.LEFT)

        # Create a button to open the treeview
        open_button = tk.Button(dropdown_frame, text="Open Treeview", command=self.open_treeview)
        open_button.pack(side=tk.LEFT)

        # Create the treeview (initially hidden)
        self.treeview = ttk.Treeview(master, columns=("Column 1", "Column 2"), show="headings")
        self.treeview.heading("Column 1", text="Column 1")
        self.treeview.heading("Column 2", text="Column 2")
        self.treeview.pack(pady=10)
        self.treeview.pack_forget()  # Hide initially

    def open_treeview(self):
        # Get the selected option from the dropdown
        selected_option = self.dropdown.get()

        # Display the treeview based on the selected option
        if selected_option == "Option 1":
            self.treeview.pack()
        else:
            self.treeview.pack_forget()

root = tk.Tk()
app = App(root)
root.mainloop()