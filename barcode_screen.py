import tkinter as tk
from tkinter import ttk
from datetime import datetime
import socket
import pandas as pd
import psycopg2
import os
import sys

root = tk.Tk()
root.title("Barcode Screen")

# if os.path.exists("favicon.ico"):
#     root.iconbitmap("favicon.ico")
# else:
#     print("Icon file not found")

root.attributes("-fullscreen", True)
root.configure(bg="#0047AB")

style = ttk.Style()
style.configure("TLabel", background="#0047AB", foreground="red")

# Configure grid weights for responsive layout
root.grid_rowconfigure(0, weight=1)  # Top section expands
root.grid_rowconfigure(1, weight=0)  # Bottom section fixed
root.grid_columnconfigure(0, weight=1)  # Left side expands
root.grid_columnconfigure(1, weight=0)  # Separator fixed
root.grid_columnconfigure(2, weight=0)  # Right side fixed

current_barcode = "WAITING FOR SCAN"
station_name = "Зареждане..."  # Default text until fetched
station_id = None
status_label = None
scan_locked = False

computer_name = socket.gethostname()

# Find the folder where the .exe is running
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

# =============================================
# DATABASE CONFIGURATION (AIVEN CLOUD)
# =============================================
DB_CONFIG = {
    'host': 'pg-143cbe8e-pacopacev277-7915.e.aivencloud.com',
    'database': 'defaultdb',
    'user': 'avnadmin',
    'password': 'AVNS_LqW5lU_kmJDiLuips8n',
    'port': 11821,
    'sslmode': 'require',
}

# =============================================
# LOGGING
# =============================================
def log(message, type="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        print(f"[{timestamp}] [{type}] {message}")
    except OSError:
        pass

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
    log('Scan unlocked: ready for next barcode', 'INFO')

# =============================================
# DATABASE CONNECTION
# =============================================
def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        log(f"Database connection failed: {e}", "ERROR")
        return None

# =============================================
# CONVERSION FUNCTIONS
# =============================================
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
        log("Cannot fetch station info: No connection", "ERROR")
        station_label.config(text="Работно място: Грешка във връзката")
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, station_name FROM production_stations WHERE computer_name = %s", (computer_name,))
            result = cursor.fetchone()
            if result:
                station_id = result[0]
                station_name = result[1]
                log(f"Station info fetched: {station_name} (ID: {station_id})")
                station_label.config(text=f"Работно място: {station_name}")
            else:
                log(f"No station found for computer name: {computer_name}", "WARNING")
                station_label.config(text=f"Работно място: Непознато ({computer_name})")
    except Exception as e:
        log(f"Failed to fetch station info: {e}", "ERROR")
    finally:
        conn.close()

def check_database_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        database_status_label = tk.Label(
            right_container,
            text="DB: Connected",
            font=("ArialBold", 10),
            fg="Green",
        )
        database_status_label.grid(row=1, column=0, sticky="new", padx=10, pady=5)
        return True
    except Exception as e:
        database_status_label = tk.Label(
            right_container,
            text="DB: NC",
            font=("ArialBold", 10),
            fg="Red",
        )
        database_status_label.grid(row=1, column=0, sticky="new", padx=10, pady=5)
        log(f"Database connection failed: {e}", "ERROR")
        return False
    finally:
        if conn:
            conn.close()

def delete_scan():
    barcode = entry_field.get().strip()
    if not barcode or barcode == "Scanned barcode ...":
        log("No valid barcode to delete", "WARNING")
        return
    
    try:
        new_barcode = int(barcode)
    except ValueError:
        log(f"Invalid barcode format: {barcode}", "ERROR")
        return
    
    log(f"Attempting to delete scan from database: {new_barcode}")
    conn = get_connection()
    if conn is None:
        log("Cannot delete scan from database: No connection", "ERROR")
        return

    try:
        with conn.cursor() as cursor:
            delete_query = """
                DELETE FROM station_scans WHERE job_order_id = %s
            """
            cursor.execute(delete_query, (new_barcode, ))
            conn.commit()
            log(f"Scan deleted from database: {new_barcode}")
            entry_field.delete(0, tk.END)
            entry_field.insert(0, "Scanned barcode ...")
            entry_field.config(fg='gray')
    except Exception as e:
        log(f"Failed to delete scan from database: {e}", "ERROR")
    finally:
        conn.close()

def barcode_scanned(event):
    global current_barcode, scan_locked
    barcode = entry.get().strip()
    
    # Update the visible entry field
    entry_field.delete(0, tk.END)
    entry_field.insert(0, barcode)
    entry_field.config(fg='black')

    if scan_locked:
        log("Scan ignored: wait for previous scan to finish", "WARNING")
        entry.delete(0, tk.END)
        return

    if barcode:
        current_barcode = barcode
        barcode_label.config(text=f"BARCODE: {barcode}")
        log(f"BARCODE SCANNED: {barcode}")
        record_scan_to_db(barcode)

    entry.delete(0, tk.END)

def record_scan_to_db(barcode):
    global computer_name, station_name, station_id, status_label, scan_locked
    log(f"Attempting to record scan to database: {barcode}")
    job_order_id = safe_str(barcode)
    
    scanned_at = datetime.now()
    scanned_by_user = computer_name
    conn = get_connection()
    if conn is None:
        log("Cannot record scan to database: No connection", "ERROR")
        return

    try:
        with conn.cursor() as cursor:
            insert_query = """
                INSERT INTO station_scans (job_order_id, station_id, scanned_at, scanned_by_user)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (job_order_id, station_id, scanned_at, scanned_by_user))
            conn.commit()
            log(f"Scanned at: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} by {scanned_by_user}")
            
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
            log(f"Scan recorded to database: {barcode}")
    except Exception as e:
        log(f"Failed to record scan to database: {e}", "ERROR")
    finally:
        conn.close()


def getLastScannedJobOrderID():
    global station_id
    
    # station_id = 4
    # print(station_id)
    conn = get_connection()
    if conn is None:
        log("Cannot fetch last scanned job order ID: No connection", "ERROR")
        return None

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT job_order_id, scanned_at FROM station_scans
                WHERE station_id = %s and scanned_at >= (CURRENT_DATE - INTERVAL '3 days')
                ORDER BY scanned_at DESC
                
            """
            cursor.execute(query, (station_id,))
            result = cursor.fetchall()
            if result:
                for item in result:
                    listbox.insert(tk.END, f" {item[0]} - {item[1].strftime('%d.%m.%Y %H:%M')}")
            else:
                listbox.grid_remove() 
    
                empty_label = tk.Label(
                    right_container,
                    text="Няма сканирани\nработни поръчки в\nпоследните 3 дни",
                    font=("Arial", 10, "italic"),
                    fg="gray",
                    justify="center"
                )
                empty_label.grid(row=4, column=0, sticky="n", padx=10, pady=10)
    except Exception as e:
        log(f"Failed to fetch last scanned job order ID: {e}", "ERROR")
        return None
    finally:
        conn.close()
# =============================================
# UI LAYOUT ELEMENTS
# =============================================
left_container = tk.Frame(root, bg="#0047AB")
left_container.grid(row=0, column=0, rowspan=2, sticky="nsew")

# Configure left_container to center content vertically
left_container.grid_rowconfigure(0, weight=1)
left_container.grid_rowconfigure(1, weight=0)
left_container.grid_rowconfigure(2, weight=1)
left_container.grid_columnconfigure(0, weight=1)

# Create a center frame for all widgets
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
    bg="#0047AB"
)
barcode_label.pack(pady=30)

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

# Separator (full height of screen)
separator = ttk.Separator(root, orient="vertical")
separator.grid(row=0, column=1, rowspan=2, sticky="ns", padx=1, pady=1)



# Right side container (for label and buttons)
right_container = tk.Frame(root)
right_container.grid(row=0, column=2, rowspan=2, sticky="nsew")

# Configure right_container for vertical layout
right_container.grid_rowconfigure(0, weight=0)  # Version label
right_container.grid_rowconfigure(1, weight=0)  # List of scans label (Upper)
right_container.grid_rowconfigure(2, weight=0)  # Listbox (Upper)
right_container.grid_rowconfigure(3, weight=0)  # Dynamic empty space (pushes buttons down)
right_container.grid_rowconfigure(4, weight=1)  # Button frame row (Bottom)
right_container.grid_rowconfigure(5, weight=0)  # Button frame row (Bottom)
right_container.grid_columnconfigure(0, weight=1)



version = "1.0.1"
version_label = tk.Label(right_container, text=f"v{version}", font=("Arial", 8))
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

listbox = tk.Listbox(right_container, height=21, bg="white", fg="black", font=("Arial", 8))
listbox.grid(row=4, column=0, sticky="new", padx=5, pady=5)





# recent_scans= getLastScannedJobOrderID()

# for item in recent_scans:
#     listbox.insert(tk.END, f" {item[0]} - {item[1].strftime('%d.%m.%Y %H:%M')}")






# Frame for buttons (bottom-right)
button_frame = tk.Frame(right_container)
button_frame.grid(row=6, column=0, sticky="new", padx=10, pady=10)

# Entry widget
entry_field = tk.Entry(button_frame, width=20, fg='gray')
entry_field.insert(0, "Scanned barcode ...")
entry_field.pack(padx=2, pady=5)

entry_field.config(state='normal')
entry_field.bind("<Button-1>", lambda e: entry_field.focus_set())

# Clear placeholder on focus
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

# Configure ttk styles for buttons
style = ttk.Style()
style.theme_use('clam')
style.configure("DELETE.TButton", foreground="red", background="lightgray", font=("Arial", 13))
style.configure("CLEAR.TButton", foreground="green", background="lightgray", font=("Arial", 13))

# Buttons
button_delete = ttk.Button(button_frame, text="Delete Scan", style="DELETE.TButton", width=13, command=delete_scan)
button_delete.pack(pady=5)

button_clear = ttk.Button(button_frame, command=(lambda: [entry_field.delete(0, tk.END), entry_field.insert(0, "Scanned barcode ..."), entry_field.config(fg='gray')]), text="Clear", style="CLEAR.TButton", width=13)
button_clear.pack(pady=5)

# Hidden text field capturing barcode scanner keystrokes
entry = tk.Entry(root)
entry.place(x=-100, y=-100)
entry.focus()
entry.bind("<Return>", barcode_scanned)

# Focus enforcement if operators accidentally click the screen background
root.bind("<Button-1>", lambda e: entry.focus_set())

# =============================================
# INITIALIZATION & RUNTIME
# =============================================
update_time()
check_database_connection()
get_station_info()
getLastScannedJobOrderID()

root.bind("<Escape>", lambda e: root.destroy())
root.mainloop()