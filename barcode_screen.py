
import tkinter as tk
from datetime import datetime
import socket
import pandas as pd
import psycopg2
import os
import sys

root = tk.Tk()
# root.title("Barcode Screen")
root.attributes("-fullscreen", True)
root.configure(bg="#0047AB")

main_frame = tk.Frame(root, bg="#0047AB")
main_frame.pack(expand=True)

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

def check_database_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        database_status_label = tk.Label(
            main_frame,
            text="Database: Connected",
            font=("ArialBold", 14),
            fg="Yellow",
            bg="#0047AB"
        )
        database_status_label.pack(pady=10)
        return True
    except Exception as e:
        database_status_label = tk.Label(
            main_frame,
            text="Database: Not Connected",
            font=("ArialBold", 14),
            fg="Red",
            bg="#0047AB"
        )
        database_status_label.pack(pady=10)
        log(f"Database connection failed: {e}", "ERROR")
        return False
    finally:
        if conn:
            conn.close()

# =============================================
# LOGGING
# =============================================
def log(message, type="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Safe printing wrapper to prevent crashes when compiled under --noconsole
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

def barcode_scanned(event):
    global current_barcode, scan_locked
    barcode = entry.get().strip()

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
            # insert_to_job_orders_query = """
            #     update job_orders set scanned_at = %s, scanned_by_user = %s where job_order_id = %s 
            #     RETURNING job_orders (job_order_id, scanned_at, scanned_by_user)
            #     VALUES (%s, %s, %s)
            #     ON CONFLICT (job_order_id) DO UPDATE SET
            #         scanned_at = EXCLUDED.scanned_at,
            #         scanned_by_user = EXCLUDED.scanned_by_user,
            #         updated_at = NOW()
            # """
            # cursor.execute(insert_to_job_orders_query, (job_order_id, scanned_at, scanned_by_user, ))
            
            insert_query = """
                INSERT INTO station_scans (job_order_id, station_id, scanned_at, scanned_by_user)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (job_order_id, station_id, scanned_at, scanned_by_user, ))
            conn.commit()
            log(f"Scanned at: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} by {scanned_by_user}")
            
            if status_label is not None:
                try:
                    status_label.destroy()
                except Exception:
                    pass

            # Formatted clean status on 2 distinct rows
            status_label = tk.Label(
                main_frame,
                text=f"Сканирана работна поръчка: {job_order_id}\nна {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} от {scanned_by_user}",
                font=("Arial", 28, "bold"),
                fg="white",
                bg="#0047AB",
                justify="center"
            )
            status_label.pack(pady=20)

            scan_locked = True
            delay = 3000  # milliseconds
            root.after(delay, lambda label=status_label: destroy_status_label_if_same(label))
            root.after(delay, unlock_scan)
            root.after(delay, lambda: barcode_label.config(text="BARCODE: ИЗЧАКВА СКАНИРАНЕ...")) 
            log(f"Scan recorded to database: {barcode}")
    except Exception as e:
        log(f"Failed to record scan to database: {e}", "ERROR")
    finally:
        conn.close()

# =============================================
# UI LAYOUT ELEMENTS
# =============================================
station_label = tk.Label(
    main_frame,
    text=f"Работно място: {station_name}",
    font=("Arial", 28, "bold"),
    fg="white",
    bg="#0047AB"
)
station_label.pack(pady=20)

operator_label = tk.Label(
    main_frame,
    text=f"Оператор: {computer_name}",
    font=("Arial", 28, "bold"),
    fg="white",
    bg="#0047AB"
)
operator_label.pack(pady=20)

barcode_label = tk.Label(
    main_frame,
    text="BARCODE: ИЗЧАКВА СКАНИРАНЕ...",
    font=("Arial", 42, "bold"),
    fg="white",
    bg="#0047AB"
)
barcode_label.pack(pady=30)

date_label = tk.Label(
    main_frame,
    text="",
    font=("Arial", 24),
    fg="white",
    bg="#0047AB"
)
date_label.pack(pady=40)

help_label = tk.Label(
    main_frame,
    text="Натисни ESC за изход | Press ESC to exit",
    font=("Arial", 13),
    fg="white",
    bg="#0047AB"
)
help_label.pack(pady=20)

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
get_station_info()  # Dynamically updates UI elements with data rows securely

root.bind("<Escape>", lambda e: root.destroy())
root.mainloop()

