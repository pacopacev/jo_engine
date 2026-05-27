import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.geometry("700x400")

# Configure grid weights for responsive layout
root.grid_rowconfigure(0, weight=1)  # Top section expands
root.grid_rowconfigure(1, weight=0)  # Bottom section fixed
root.grid_columnconfigure(0, weight=1)  # Left side expands
root.grid_columnconfigure(1, weight=0)  # Separator fixed
root.grid_columnconfigure(2, weight=0)  # Right side fixed

# Label 1 on the left (full height)
label1 = tk.Label(root, text="Label 1 - Left Side", bg="#0047AB", fg="white")
label1.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=1, pady=1)

# Separator (full height of screen)
separator = ttk.Separator(root, orient="vertical")
separator.grid(row=0, column=1, rowspan=2, sticky="ns", padx=1, pady=1)

# Right side container (for label and buttons)
right_container = tk.Frame(root)
right_container.grid(row=0, column=2, rowspan=2, sticky="nsew")

# Configure right_container for vertical layout
right_container.grid_rowconfigure(0, weight=1)  # Pushes buttons down
right_container.grid_rowconfigure(1, weight=0)  # Buttons row
right_container.grid_columnconfigure(0, weight=1)

# # Label 2 on top-right
# label2 = tk.Label(right_container, text="Label 2 - Right Side", bg="#0047AB", fg="white")
# label2.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

# Frame for buttons (bottom-right)
button_frame = tk.Frame(right_container)
button_frame.grid(row=1, column=0, sticky="se", padx=10, pady=10)

# Entry widget
entry = tk.Entry(button_frame, width=20)
entry.insert(0, "Enter barcode ...")
entry.pack(pady=5)  # Added pack to display the entry

# 3 Buttons stacked vertically in lower right side
button_delete = tk.Button(button_frame, text="Delete Scan", width=15)
button_delete.pack(pady=5)


button_clear = tk.Button(button_frame, text="Clear", width=15)
button_clear.pack(pady=5)

root.mainloop()