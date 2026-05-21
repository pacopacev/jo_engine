import pandas as pd
import os
from pathlib import Path
from datetime import datetime
from utils import log, get_connection, safe_int, safe_datetime, safe_str, safe_bool, safe_float


def create_job_orders_from_batch(excel_file, target_batch_id=None):
    """
    Specifically create job orders from Excel with batch_id
    (Without re-importing products)
    
    Args:
        excel_file: Path to Excel file
        target_batch_id: Optional - only create jobs for this specific batch_id
                         If None, creates for all batches
    """
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='product_list')
        log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    stats = {'batches': 0, 'job_orders': 0, 'errors': 0}
    processed_combinations = set()
    
    try:
        # =============================================
        # GET THE LAST JOB ORDER NUMBER FROM DATABASE
        # =============================================
        # cursor.execute("""
        #     SELECT job_order_number FROM job_orders 
        #     ORDER BY CAST(job_order_number AS INTEGER) DESC 
        #     LIMIT 1
        # """)
        # last_job = cursor.fetchone()
        
        # if last_job:
        #     next_job_number = int(last_job[0]) + 1
        #     log(f"📋 Last job order number found: {last_job[0]}")
        #     log(f"📋 Next job order will start from: {next_job_number}")
        # else:
        #     next_job_number = 265000  # Starting number if no job orders exist
        #     log(f"📋 No existing job orders. Starting from: {next_job_number}")
        # =============================================
        file_path_to_search = "S:/JO"

# Use a list to store multiple job numbers
        job_order_numbers = []

        for file in os.listdir(file_path_to_search):
            if file.endswith(".xlsm") or file.endswith(".xlsx"):
                # os.listdir gives just the file name, so we can split it directly
                file_name_only, file_extension = os.path.splitext(file)   
        
                # # Slice index 2 to 8 to get the JO number
                # jo = file_name_only[2:8]
                job_order_numbers.append(file_name_only)

        # FIX: Put the [-1] inside the print function, attached to the list name
        if job_order_numbers:
            next_job_number = None

            # Loop through the list BACKWARDS (starting from the last element)
            for job in reversed(job_order_numbers):
                # Clean up the element (convert to string just in case it's already an int)
                job_str = str(job).strip()
        
                # Check if this specific item is a number
                if job_str.isdigit():
                    next_job_number = int(job_str)
                    break  # We found the last number! Exit the loop immediately.

    # Check if we successfully found a number anywhere in the list
            if next_job_number is not None:
                print(f"Next job order number: {next_job_number}")
            else:
                print("Warning: No valid numeric job order numbers found in the entire list.")

        else:
            print("No .xlsx or .xlsm files found.")
            
            
        # Process only parent rows (where MA_Number is not empty)
        for _, row in df.iterrows():
            ma_number = safe_str(row.get('MA_Number'))
            
            # Skip empty MA_Number (child rows)
            if not ma_number:
                continue
            
            batch_id = safe_int(row.get('batch_id'), None)
            
            # =============================================
            # FILTER BY TARGET BATCH_ID IF SPECIFIED
            # =============================================
            if target_batch_id is not None and batch_id != target_batch_id:
            
                continue  # Skip this row - not the target batch
            
            quantity = safe_int(row.get('qty', 1), 0)
            
            if not batch_id:
                continue
            
            # Skip if already processed this combination
            combo = f"{batch_id}_{ma_number}"
            if combo in processed_combinations:
                continue
            processed_combinations.add(combo)
            
            # Get product_id
            cursor.execute("SELECT id FROM products WHERE ma_number = %s", (ma_number,))
            product_result = cursor.fetchone()
            if not product_result:
                log(f"   ⚠️ Product not found: {ma_number}", "WARNING")
                stats['errors'] += 1
                continue
            product_id = product_result[0]
            
            # Create batch if not exists
            cursor.execute("SELECT id, batch_number FROM batch WHERE id = %s", (batch_id,))
            batch_result = cursor.fetchone()
            
            if batch_result:
                batch_number = batch_result[1]
                log(f"   📁 Using existing batch: {batch_number}")
            else:
                batch_number = f"BATCH-{batch_id:04d}"
                cursor.execute("""
                    INSERT INTO batch (id, batch_number, created_by, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, (batch_id, batch_number, 'job_import'))
                stats['batches'] += 1
                log(f"   📁 Created batch: {batch_number}")
            
            # Use the next_job_number and increment it
            job_order_number = next_job_number + 1
            next_job_number += 1
            
            price_offer_num_raw = row.get('price_offer_num')
            if pd.notna(price_offer_num_raw):
                try:
                    price_offer_num = str(int(float(price_offer_num_raw)))
                except (ValueError, TypeError):
                    price_offer_num = safe_str(price_offer_num_raw)
            else:
                price_offer_num = None
            
            cursor.execute("""
                INSERT INTO job_orders (
                    job_order_number, batch_id, product_id, quantity,
                    status, priority, created_by, created_at, updated_at, price_offer_num
                )
                VALUES (%s, %s, %s, %s, 'pending', 'normal', %s, NOW(), NOW(), %s)
                ON CONFLICT (job_order_number) DO NOTHING
            """, (job_order_number, batch_id, product_id, quantity, 'job_import', price_offer_num))
            
            if cursor.rowcount > 0:
                stats['job_orders'] += 1
                log(f"   📋 Created job order: {job_order_number} - {ma_number} x{quantity}")
            else:
                log(f"   📋 Job order already exists: {job_order_number}")

            
            #insert in batch_qty table
            if batch_id is not None and batch_id > 0:
                if product_id is None:
                    log(f"   ⚠️ Cannot create batch quantity record - product_id is None for {ma_number}", "WARNING")
                log(f"   🔖 Batch ID: {batch_id}")
            
                cursor.execute("""
                    INSERT INTO batch_qty (batch_id, qty, created_by, product_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (batch_id, quantity, 'import batch', product_id))
                batch_qty_id = cursor.fetchone()[0]
                print(f"   📊 Batch quantity record created with id: {batch_qty_id}")
            
            
               
                

        conn.commit()
        
        # Show which batch was processed
        if target_batch_id:
            log(f"\n📁 Processed ONLY batch_id: {target_batch_id}")
        else:
            log(f"\n📁 Processed ALL batches")
        
        log("\n" + "=" * 70)
        log("✅ JOB ORDERS CREATED FROM BATCH!", "SUCCESS")
        log(f"   Batches created/used: {stats['batches']}")
        log(f"   Job orders created: {stats['job_orders']}")
        log(f"   Errors: {stats['errors']}")
        log("=" * 70)
        
        return True
        
    except Exception as e:
        log(f"❌ Error: {e}", "ERROR")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()