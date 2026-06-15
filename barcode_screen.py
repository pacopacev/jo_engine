import tkinter as tk
from tkinter import ttk
from datetime import datetime
import socket
import pandas as pd
import psycopg2
import os
import sys
from globalModel import GlobalModel

global_model = GlobalModel()

root = tk.Tk()
root.title("Barcode Screen")

root.attributes("-fullscreen", True)
root.configure(bg="#0047AB")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", background="#0047AB", foreground="red")
style.configure("DELETE.TButton", foreground="red", background="lightgray", font=("Arial", 13))
style.configure("CLEAR.TButton", foreground="green", background="lightgray", font=("Arial", 13))

# Configure grid weights for responsive layout
root.grid_rowconfigure(0, weight=1)  
root.grid_rowconfigure(1, weight=0)  
root.grid_columnconfigure(0, weight=1)  
root.grid_columnconfigure(1, weight=0)  
root.grid_columnconfigure(2, weight=0)  

current_barcode = "WAITING FOR SCAN"
station_name = "Зареждане..."  
station_id = None
status_label = None
empty_label = None  # Track globally to prevent memory leaks
scan_locked = False

computer_name = socket.gethostname()

if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

def destroy_status_label():
    global status_label
    if status_label is not None:
        try:
            status_label.destroy()
        except Exception:
            pass
        status_label = None

def destroy_status_label_if_same(label):
    global status_label
    if status_label is label:
        try:
            label.destroy()
        except Exception:
            pass
        status_label = None

def unlock_scan():
    global scan_locked
    scan_locked = False
    global_model.log('Scan unlocked: ready for next barcode', 'INFO')

# =============================================
# DATABASE CONNECTION
# =============================================
def get_connection():
    try:
        # Check if global connection exists and is still open
        if (not hasattr(global_model, 'conn') or 
                global_model.conn is None or 
                getattr(global_model.conn, 'closed', 0) != 0):
            
            # Fall back to creating/restoring a live database connection if closed
            if hasattr(global_model, 'connect_db'):
                global_model.conn = global_model.connect_db()
            else:
                global_model.log("Global connection instance is closed or uninitialized.", "ERROR")
                return None
                
        return global_model.conn
    except Exception as e:
        global_model.log(f"Database connection factory recovery failed: {e}", "ERROR")
        return None

def safe_str(value, default=None):
    if value is None or pd.isna(value):
        return default
    return str(value).strip()

def update_time():
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    date_label.config(text=now)
    root.after(1000, update_time)
    
def get_station_info():
    global station_name, station_id
    conn = get_connection()
    
    if conn is None:
        global_model.log("Cannot fetch station info: No connection", "ERROR")
        station_label.config(text="Работно място: Грешка във връзката")
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, station_name FROM production_stations WHERE computer_name = %s", (computer_name,))
            result = cursor.fetchone()
            if result:
                # station_id = result[0]
                station_id = 4
                station_name = result[1]
                global_model.log(f"Station info fetched: {station_name} (ID: {station_id})")
                station_label.config(text=f"Работно място: {station_name}")
            else:
                global_model.log(f"No station found for computer name: {computer_name}", "WARNING")
                station_label.config(text=f"Работно място: Непознато ({computer_name})")
    except Exception as e:
        global_model.log(f"Failed to fetch station info: {e}", "ERROR")

def check_database_connection():
    conn = get_connection()
    if conn is not None and getattr(conn, 'closed', 0) == 0:
        database_status_label = tk.Label(
            right_container,
            text="DB: Connected",
            font=("Arial", 10, "bold"),
            fg="Green",
        )
        database_status_label.grid(row=1, column=0, sticky="new", padx=10, pady=5)
        return True
    else:
        database_status_label = tk.Label(
            right_container,
            text="DB: NC",
            font=("Arial", 10, "bold"),
            fg="Red",
        )
        database_status_label.grid(row=1, column=0, sticky="new", padx=10, pady=5)
        global_model.log("Database connection verification check failed", "ERROR")
        return False

def delete_scan():
    barcode = entry_field.get().strip()
    if not barcode or barcode == "Scanned barcode ...":
        global_model.log("No valid barcode to delete", "WARNING")
        return
    
    try:
        new_barcode = int(barcode)
    except ValueError:
        global_model.log(f"Invalid barcode format: {barcode}", "ERROR")
        return
    
    global_model.log(f"Attempting to delete scan from database: {new_barcode}")
    conn = get_connection()
    if conn is None:
        global_model.log("Cannot delete scan from database: No connection", "ERROR")
        return

    try:
        with conn.cursor() as cursor:
            delete_query = "DELETE FROM station_scans WHERE job_order_id = %s"
            cursor.execute(delete_query, (str(new_barcode), ))
            conn.commit()
            global_model.log(f"Scan deleted from database: {new_barcode}")
            entry_field.delete(0, tk.END)
            entry_field.insert(0, "Scanned barcode ...")
            entry_field.config(fg='gray')
            getLastScannedJobOrderID()
    except Exception as e:
        global_model.log(f"Failed to delete scan from database: {e}", "ERROR")

def barcode_scanned(event):
    global current_barcode, scan_locked
    barcode = entry.get().strip()
    
    entry_field.delete(0, tk.END)
    entry_field.insert(0, barcode)
    entry_field.config(fg='black')

    if scan_locked:
        global_model.log("Scan ignored: wait for previous scan to finish", "WARNING")
        entry.delete(0, tk.END)
        return

    if barcode:
        current_barcode = barcode
        barcode_label.config(text=f"BARCODE: {barcode}")
        global_model.log(f"BARCODE SCANNED: {barcode}")
        record_scan_to_db(barcode)

    entry.delete(0, tk.END)

def record_scan_to_db(barcode):
    global computer_name, station_name, station_id, status_label, scan_locked
    global_model.log(f"Attempting to record scan to database: {barcode}")
    job_order_id = safe_str(barcode)
    
    if checkBArcodeIfExists(job_order_id):
        global_model.log(f"BARCODE ALREADY EXISTENT IN DB: {barcode}", "WARNING")
        
        if status_label is not None:
            try:
                status_label.destroy()
            except Exception:
                pass
            
        root.configure(bg="#FF0000")
        
        status_label = tk.Label(
            center_frame,
            text=f"ГРЕШКА: Поръчката {job_order_id}\nвече е сканирана на това работно място!",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="#FF0000",
            justify="center"
        )
        status_label.pack(pady=20)
        
        left_container.configure(bg="#FF0000")
        center_frame.configure(bg="#FF0000")
        station_label.configure(bg="#FF0000")
        operator_label.configure(bg="#FF0000")
        barcode_label.configure(bg="#FF0000")
        date_label.configure(bg="#FF0000")
        help_label.configure(bg="#FF0000")
        
        scan_locked = True
        delay = 3000
        root.after(delay, lambda label=status_label: destroy_status_label_if_same(label))
        root.after(delay, unlock_scan)
        
        root.after(delay, lambda: [
            root.configure(bg="#0047AB"),
            left_container.configure(bg="#0047AB"),
            center_frame.configure(bg="#0047AB"),
            station_label.configure(bg="#0047AB"),
            operator_label.configure(bg="#0047AB"),
            barcode_label.configure(bg="#0047AB"),
            date_label.configure(bg="#0047AB"),
            help_label.configure(bg="#0047AB"),
            barcode_label.config(text="BARCODE: ИЗЧАКВА СКАНИРАНЕ...")
        ])
            
        getLastScannedJobOrderID()
        return

    scanned_at = datetime.now()
    scanned_by_user = computer_name
    conn = get_connection()
    
    if conn is None:
        global_model.log("Cannot record scan to database: No connection", "ERROR")
        return

    try:
        with conn.cursor() as cursor:
            insert_query = """
                INSERT INTO station_scans (job_order_id, station_id, scanned_at, scanned_by_user)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (job_order_id, station_id, scanned_at, scanned_by_user))
            conn.commit()
            global_model.log(f"Scanned at: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} by {scanned_by_user}")
            
            if status_label is not None:
                try:
                    status_label.destroy()
                except Exception:
                    pass

            status_label = tk.Label(
                center_frame,
                text=f"Сканирана работна поръчка: {job_order_id}\nна {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} от {scanned_by_user}",
                font=("Arial", 28, "bold"),
                fg="white",
                bg="#0047AB",
                justify="center"
            )
            status_label.pack(pady=20)

            scan_locked = True
            delay = 3000
            root.after(delay, lambda label=status_label: destroy_status_label_if_same(label))
            root.after(delay, lambda: [entry_field.delete(0, tk.END), 
                                       entry_field.insert(0, "Scanned barcode ..."), 
                                       entry_field.config(fg='gray')])

            root.after(delay, unlock_scan)
            root.after(delay, lambda: barcode_label.config(text="BARCODE: ИЗЧАКВА СКАНИРАНЕ..."))
            global_model.log(f"Scan recorded to database: {barcode}")
            
            getLastScannedJobOrderID()
    except Exception as e:
        global_model.log(f"Failed to record scan to database: {e}", "ERROR")

def getLastScannedJobOrderID():
    global empty_label
    active_station = station_id if station_id is not None else 4
    active_station = 4
    conn = get_connection()
    if conn is None:
        global_model.log("Cannot fetch last scanned job order ID: No connection", "ERROR")
        root.after(5000, getLastScannedJobOrderID)
        return

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT job_order_id, scanned_at FROM station_scans
                WHERE station_id = %s and scanned_at >= (CURRENT_DATE - INTERVAL '3 days')
                ORDER BY scanned_at DESC
            """
            cursor.execute(query, (active_station,))
            result = cursor.fetchall()
            
            listbox.delete(0, tk.END)
            
            if result:
                if empty_label is not None:
                    empty_label.grid_remove()
                listbox.grid()
                for item in result:
                    listbox.insert(tk.END, f" {item[0]} - {item[1].strftime('%d.%m.%Y %H:%M')}")
            else:
                listbox.grid_remove() 
                if empty_label is None:
                    empty_label = tk.Label(
                        right_container,
                        text="Няма сканирани работни поръчки\nза последните 3 дни.",
                        font=("Arial", 9, "italic"),
                        fg="gray"
                    )
                empty_label.grid(row=4, column=0, sticky="new", padx=5, pady=5)
    except Exception as e:
        global_model.log(f"Failed to fetch last scanned job order ID: {e}", "ERROR")
        
    root.after(5000, getLastScannedJobOrderID)

def checkBArcodeIfExists(barcode):
    # active_station = station_id if station_id is not None else 4
    active_station = 4
    try:
        barcode_str = int(barcode)
    except ValueError:
        barcode_str = str(barcode).strip()
    
    conn = get_connection()
    if conn is None:
        global_model.log("Cannot check barcode existence: No connection", "ERROR")
        return False

    try:
        with conn.cursor() as cursor:
            query = "SELECT COUNT(*) FROM station_scans WHERE job_order_id = %s AND station_id = %s"
            cursor.execute(query, (str(barcode_str), active_station))
            count = cursor.fetchone()[0]
            print(count)
            return count > 0
    except Exception as e:
        global_model.log(f"Failed to check barcode existence: {e}", "ERROR")
        return False

def update_dot():
        current_text = barcode_label.cget("text")
        print(current_text)
        if current_text.endswith("..."):
            new_text = current_text[:-3] + "."
        else:
            new_text = current_text + "."
        barcode_label.config(text=new_text)
        root.after(440, update_dot)

# =============================================
# UI LAYOUT ELEMENTS
# =============================================
left_container = tk.Frame(root, bg="#0047AB")
left_container.grid(row=0, column=0, rowspan=2, sticky="nsew")

left_container.grid_rowconfigure(0, weight=1)
left_container.grid_rowconfigure(1, weight=0)
left_container.grid_rowconfigure(2, weight=1)
left_container.grid_columnconfigure(0, weight=1)

center_frame = tk.Frame(left_container, bg="#0047AB")
center_frame.grid(row=1, column=0, sticky="nsew")
center_frame.grid_columnconfigure(0, weight=1)

station_label = tk.Label(
    center_frame,
    text=f"Работно място: {station_name}",
    font=("Arial", 28, "bold"),
    fg="white",
    bg="#0047AB"
)
station_label.pack(pady=20)

operator_label = tk.Label(
    center_frame,
    text=f"Оператор: {computer_name}",
    font=("Arial", 28, "bold"),
    fg="white",
    bg="#0047AB"
)
operator_label.pack(pady=20)

barcode_label = tk.Label(
    center_frame,
    text="BARCODE: ИЗЧАКВА СКАНИРАНЕ...",
    font=("Arial", 42, "bold"),
    fg="white",
    bg="#0047AB",
    anchor="w",
    justify="center"
)
barcode_label.pack(pady=30, fill="x", padx=180)

date_label = tk.Label(
    center_frame,
    text="",
    font=("Arial", 24),
    fg="white",
    bg="#0047AB"
)
date_label.pack(pady=40)

help_label = tk.Label(
    center_frame,
    text="Натисни ESC за изход | Press ESC to exit",
    font=("Arial", 13),
    fg="white",
    bg="#0047AB"
)
help_label.pack(pady=20)

separator = ttk.Separator(root, orient="vertical")
separator.grid(row=0, column=1, rowspan=2, sticky="ns", padx=1, pady=1)

# Right side container
right_container = tk.Frame(root)
right_container.grid(row=0, column=2, rowspan=2, sticky="nsew")

right_container.grid_rowconfigure(0, weight=0)  
right_container.grid_rowconfigure(1, weight=0)  
right_container.grid_rowconfigure(2, weight=0)  
right_container.grid_rowconfigure(3, weight=0)  
right_container.grid_rowconfigure(4, weight=1)  
right_container.grid_rowconfigure(5, weight=0)  
right_container.grid_rowconfigure(6, weight=0)  
right_container.grid_columnconfigure(0, weight=1)

version = "1.0.5"
build_date = datetime.now().strftime("%Y-%m-%d")

version_label = tk.Label(right_container, text=f"v{version} ({build_date})", font=("Arial", 8))
version_label.grid(row=0, column=0, sticky="new", padx=10, pady=5)

separator2 = ttk.Separator(right_container, orient="horizontal")
separator2.grid(row=5, column=0, sticky="ew", padx=3)

separator3 = ttk.Separator(right_container, orient="horizontal")    
separator3.grid(row=2, column=0, sticky="ew", padx=3)

list_of_scans_label = tk.Label(
    right_container,
    text="Последни сканирани\nработни поръчки:",
    font=("Arial", 9),
    fg="black", padx=5, pady=5
)
list_of_scans_label.grid(row=3, column=0, sticky="new", padx=5, pady=5)

listbox = tk.Listbox(right_container, height=25, bg="white", fg="black", font=("Arial", 8))
listbox.grid(row=4, column=0, sticky="nsew", padx=5, pady=5)

# Frame for buttons (bottom-right)
button_frame = tk.Frame(right_container)
button_frame.grid(row=6, column=0, sticky="snew", padx=10, pady=10)

entry_field = tk.Entry(button_frame, width=20, fg='gray')
entry_field.insert(0, "Scanned barcode ...")
entry_field.pack(padx=2, pady=5)

entry_field.config(state='normal')
entry_field.bind("<Button-1>", lambda e: entry_field.focus_set())

def on_entry_click(event):
    if entry_field.get() == "Scanned barcode ..." and entry_field['fg'] == 'gray':
        entry_field.delete(0, tk.END)
        entry_field.config(fg='black')

def on_focus_out(event):
    if entry_field.get() == "":
        entry_field.insert(0, "Scanned barcode ...")
        entry_field.config(fg='gray')

entry_field.bind('<FocusIn>', on_entry_click)
entry_field.bind('<FocusOut>', on_focus_out)

button_delete = ttk.Button(button_frame, text="Delete Scan", style="DELETE.TButton", width=13, command=delete_scan)
button_delete.pack(pady=5)

button_clear = ttk.Button(button_frame, command=(lambda: [entry_field.delete(0, tk.END), entry_field.insert(0, "Scanned barcode ..."), entry_field.config(fg='gray')]), text="Clear", style="CLEAR.TButton", width=13)
button_clear.pack(pady=5)

# Hidden system background entry field capturing barcode inputs natively
entry = tk.Entry(root)
entry.place(x=-100, y=-100)
entry.focus()
entry.bind("<Return>", barcode_scanned)

root.bind("<Button-1>", lambda e: entry.focus_set())

# =============================================
# INITIALIZATION & RUNTIME
# =============================================
update_time()
update_dot()
check_database_connection()
get_station_info()

root.after(200, getLastScannedJobOrderID)  

root.bind("<Escape>", lambda e: root.destroy())
root.mainloop()