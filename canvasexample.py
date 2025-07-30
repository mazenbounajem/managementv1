import tkinter as tk

root = tk.Tk()

canvas = tk.Canvas(root, width=400, height=300, relief="raised")
canvas.pack()

label1 = tk.Label(root, text="Calculate the Square Root")
label1.config(font=("arial", 14))
canvas.create_window(200, 25, window=label1)

label2 = tk.Label(root, text="Type your Number:")
label2.config(font=("arial", 10))
canvas.create_window(200, 100, window=label2)

entry = tk.Entry(root)
canvas.create_window(200, 140, window=entry)


def get_square_root():
    value = entry.get()

    label3 = tk.Label(
        root, text="The Square Root of " + value + " is:", font=("arial", 10)
    )
    canvas.create_window(200, 210, window=label3)

    label4 = tk.Label(root, text=float(value) ** 0.5, font=("arial", 10, "bold"))
    canvas.create_window(200, 230, window=label4)


button = tk.Button(
    text="Get the Square Root",
    command=get_square_root,
    bg="brown",
    fg="white",
    font=("arial", 9, "bold"),
)
canvas.create_window(200, 180, window=button)

root.mainloop()