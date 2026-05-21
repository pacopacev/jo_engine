# full_import.py - Complete working version for parent-child Excel structure
import pandas as pd
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
        df = pd.read_excel(excel_path, sheet_name='product')
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
        cursor.execute("""
            SELECT job_order_number FROM job_orders 
            ORDER BY CAST(job_order_number AS INTEGER) DESC 
            LIMIT 1
        """)
        last_job = cursor.fetchone()
        
        if last_job:
            next_job_number = int(last_job[0]) + 1
            log(f"📋 Last job order number found: {last_job[0]}")
            log(f"📋 Next job order will start from: {next_job_number}")
        else:
            next_job_number = 260  # Starting number if no job orders exist
            log(f"📋 No existing job orders. Starting from: {next_job_number}")
        # =============================================
        
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
            
            quantity = safe_int(row.get('quantity', 1), 1)
            
            if not batch_id:
                continue
            
            # Skip if already processed this combination
            combo = f"{batch_id}_{ma_number}"
            if combo in processed_combinations:
                continue
            processed_combinations.add(combo)
            
            # Get product_id
            cursor.execute("SELECT id FROM product WHERE ma_number = %s", (ma_number,))
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
            job_order_number = str(next_job_number)
            next_job_number += 1
            
            cursor.execute("""
                INSERT INTO job_orders (
                    job_order_number, batch_id, product_id, quantity,
                    status, priority, created_by, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 'pending', 'normal', %s, NOW(), NOW())
                ON CONFLICT (job_order_number) DO NOTHING
            """, (job_order_number, batch_id, product_id, quantity, 'job_import'))
            
            if cursor.rowcount > 0:
                stats['job_orders'] += 1
                log(f"   📋 Created job order: {job_order_number} - {ma_number} x{quantity}")
            else:
                log(f"   📋 Job order already exists: {job_order_number}")
        
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
        
        
        
def import_full_production_data(excel_file, target_batch_id=None):
    """
    Import products, parts, BOM from Excel with parent-child structure
    Parent row: Has MA_Number, Product_Name, Is_Assembly=TRUE
    Child rows: Have Part_Number, Part_Qty, dimensions (MA_Number empty)
    """
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='product')
        log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    stats = {
        'products': 0, 'parts': 0, 'bom': 0, 
        'colors': 0, 'materials': 0, 'types': 0,
        'batches': 0, 'job_orders': 0, 'errors': 0
    }
    
    # Track which batch+product combinations already have job orders
    processed_job_orders = set()
    
    try:
        # =============================================
        # GET THE LAST JOB ORDER NUMBER FROM DATABASE
        # =============================================
        cursor.execute("""
            SELECT job_order_number FROM job_orders 
            ORDER BY CAST(job_order_number AS INTEGER) DESC 
            LIMIT 1
        """)
        last_job = cursor.fetchone()
        
        if last_job:
            next_job_number = int(last_job[0]) + 1
            log(f"📋 Last job order number found: {last_job[0]}")
            log(f"📋 Next job order will start from: {next_job_number}")
        else:
            next_job_number = 260  # Starting number if no job orders exist
            log(f"📋 No existing job orders. Starting from: {next_job_number}")
        # =============================================
        
        # Process each parent product (where MA_Number is not empty)
        for idx, row in df.iterrows():
            ma_number = safe_str(row.get('MA_Number'))
            
            # Skip rows without MA_Number (these are child part rows)
            # if not ma_number:
            #     continue
            
            log(f"\n📦 Processing product: {ma_number}")
            
            # Get product details from parent row
            product_name = safe_str(row.get('Product_Name'), '')
            description = safe_str(row.get('Description'))
            is_assembly = safe_bool(row.get('Is_Assembly', False))
            type_code = safe_str(row.get('type_code'))
            batch_id = safe_int(row.get('batch_id'), None)
            qty = safe_int(row.get('qty', 1), 1)
            part_number = safe_str(row.get('Part_Number'))
            part_dim_x = safe_float(row.get('Part_Length'))
            part_dim_y = safe_float(row.get('Part_Width'))
            part_dim_z = safe_float(row.get('Part_Height'))
            color_code = safe_str(row.get('color_code'))
            material_code = safe_str(row.get('material_code'))
            
            # Skip empty rows
            if not part_number:
                log("   📋 Skipping empty row", "WARNING")
                continue
            
            
            
            
           
                   
         
            
        
            
            
            # Get or create product type
            type_id = None
            if type_code:
                cursor.execute("SELECT id FROM product_type WHERE type_code = %s", (type_code,))
                result = cursor.fetchone()
                if result:
                    type_id = result[0]
                # else:
                #     cursor.execute("""
                #         INSERT INTO product_type (type_code, type_name, created_by)
                #         VALUES (%s, %s, %s) RETURNING id
                #     """, (type_code, type_code, 'import'))
                #     type_id = cursor.fetchone()[0]
                #     stats['types'] += 1
                #     log(f"   🏷️ Created type: {type_code}")
            
            # Insert or update product
            cursor.execute("""
                INSERT INTO product (ma_number, name, description, is_assembly, type_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ma_number) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_assembly = EXCLUDED.is_assembly,
                    type_id = EXCLUDED.type_id,
                    updated_at = NOW()
                RETURNING id
            """, (ma_number, product_name, description, is_assembly, type_id, 'import'))
            
            product_id = cursor.fetchone()[0]
            stats['products'] += 1
            log(f"   ✅ Product saved: {ma_number} (id={product_id})")
            
            # Get or create color
            color_id = None
            if color_code:
                cursor.execute("SELECT id FROM colors WHERE color_code = %s", (color_code,))
                result = cursor.fetchone()
                if result:
                    color_id = result[0]
                # else:
                #     cursor.execute("""
                #         INSERT INTO color (color_code, color_name, created_by)
                #         VALUES (%s, %s, %s) RETURNING id
                #     """, (color_code, color_code, 'import'))
                #     color_id = cursor.fetchone()[0]
                #     stats['colors'] += 1
                #     log(f"   🎨 Created color: {color_code}")
            
            # Get or create material
            material_id = None
            if material_code:
                cursor.execute("SELECT id FROM materials WHERE material_code = %s", (material_code,))
                result = cursor.fetchone()
                if result:
                    material_id = result[0]
                # else:
                #     cursor.execute("""
                #         INSERT INTO material (material_code, material_name, created_by)
                #         VALUES (%s, %s, %s) RETURNING id
                #     """, (material_code, material_code, 'import'))
                #     material_id = cursor.fetchone()[0]
                #     stats['materials'] += 1
                #     log(f"   🔩 Created material: {material_code}")
            
            
            cursor.execute("""INSERT INTO parts (part_number, part_name, dimension_x, dimension_y, dimension_z, color_id, material_id, product_id, created_by) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                           ON CONFLICT (part_number) DO NOTHING""", 
                           (part_number, part_number, part_dim_x, part_dim_y, part_dim_z, color_id, material_id, product_id, 'import'))
            
            #insert in batch_qty table
            # if batch_id is not None and batch_id > 0:
            #     if product_id is None:
            #         log(f"   ⚠️ Cannot create batch quantity record - product_id is None for {ma_number}", "WARNING")
            #     log(f"   🔖 Batch ID: {batch_id}")
            
            #     cursor.execute("""
            #         INSERT INTO batch_qty (batch_id, qty, created_by, product_id)
            #         VALUES (%s, %s, %s, %s)
            #         RETURNING id
            #     """, (batch_id, qty, 'import plambe', product_id))
            #     batch_qty_id = cursor.fetchone()[0]
            #     print(f"   📊 Batch quantity record created with id: {batch_qty_id}")
            
            
            
            
            # If assembly, find all child parts (rows after parent with empty MA_Number)
            # if is_assembly:
            #     # Delete existing BOM for this product
            #     cursor.execute("DELETE FROM bill_of_materials WHERE product_id = %s", (product_id,))
                
            #     # Find child rows (next rows until next MA_Number or end of sheet)
            #     child_rows = []
            #     next_idx = idx + 1
            #     while next_idx < len(df):
            #         next_ma = safe_str(df.iloc[next_idx].get('MA_Number'))
            #         if next_ma:  # Found next parent, stop
            #             break
                    
            #         # This is a child row (part)
            #         child_row = df.iloc[next_idx]
            #         part_number = safe_str(child_row.get('Part_Number'))
            #         if part_number:
            #             child_rows.append(child_row)
            #         next_idx += 1
                
            #     for part_row in child_rows:
            #         part_number = safe_str(part_row.get('Part_Number'))
            #         if not part_number:
            #             continue
                    
            #         part_qty = safe_int(part_row.get('Part_Qty'), 1)
            #         part_dim_x = safe_float(part_row.get('Part_Length'))
            #         part_dim_y = safe_float(part_row.get('Part_Width'))
            #         part_dim_z = safe_float(part_row.get('Part_Height'))
            #         part_color = safe_str(part_row.get('color_code'))
            #         part_material = safe_str(part_row.get('material_code'))
            #         assembly_order = safe_int(part_row.get('Assembly_Order'), 0)
            #         print(part_color)
            #         # Get or create color
            #         part_color_id = None
            #         if part_color:
            #             cursor.execute("SELECT id FROM colors WHERE color_code ILIKE %s", (part_color,))
            #             result = cursor.fetchone()
            #             if result:
            #                 part_color_id = result[0]
            #                 print(f"      🎨 Found color: {part_color} (id={part_color_id})")
            #             # else:
            #             #     cursor.execute("""
            #             #         INSERT INTO colors (color_code, color_name, created_by)
            #             #         VALUES (%s, %s, %s) RETURNING id
            #             #     """, (part_color.upper(), part_color, 'import'))
            #             #     part_color_id = cursor.fetchone()[0]
            #             #     stats['colors'] += 1
            #             #     log(f"      🎨 Created color: {part_color}")
                    
            #         # Get or create material
            #         part_material_id = None
            #         if part_material:
            #             cursor.execute("SELECT id FROM materials WHERE material_code ILIKE %s", (part_material,))
            #             result = cursor.fetchone()
            #             if result:
            #                 part_material_id = result[0]
            #             # else:
            #             #     cursor.execute("""
            #             #         INSERT INTO materials (material_code, material_name, created_by)
            #             #         VALUES (%s, %s, %s) RETURNING id
            #             #     """, (part_material.upper(), part_material, 'import'))
            #             #     part_material_id = cursor.fetchone()[0]
            #             #     stats['materials'] += 1
            #             #     log(f"      🔩 Created material: {part_material}")
                    
            #         # Get or create part
            #         cursor.execute("SELECT id FROM parts WHERE part_number = %s", (part_number,))
            #         result = cursor.fetchone()
            #         if result:
            #             part_id = result[0]
            #             # Update existing part
            #             cursor.execute("""
            #                 UPDATE parts 
            #                 SET product_id = %s,
            #                     dimension_x = COALESCE(%s, dimension_x),
            #                     dimension_y = COALESCE(%s, dimension_y),
            #                     dimension_z = COALESCE(%s, dimension_z),
            #                     color_id = COALESCE(%s, color_id),
            #                     material_id = COALESCE(%s, material_id),
            #                     updated_at = NOW()
            #                 WHERE id = %s
            #             """, (product_id, part_dim_x, part_dim_y, part_dim_z, 
            #                 part_color_id, part_material_id, part_id))
            #             log(f"      🔧 Updated part: {part_number}")
            #         else:
            #             # Create new part
            #             cursor.execute("""
            #                 INSERT INTO parts (
            #                     part_number, part_name, 
            #                     dimension_x, dimension_y, dimension_z,
            #                     color_id, material_id, 
            #                     current_stock, unit_of_measure, 
            #                     product_id, created_by
            #                 )
            #                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            #                 RETURNING id
            #             """, (
            #                 part_number,           # part_number
            #                 part_number,           # part_name
            #                 part_dim_x,            # dimension_x
            #                 part_dim_y,            # dimension_y
            #                 part_dim_z,            # dimension_z
            #                 part_color_id,         # color_id
            #                 part_material_id,      # material_id
            #                 0,                     # current_stock
            #                 'pcs',                 # unit_of_measure
            #                 product_id,            # product_id
            #                 'import'               # created_by
            #             ))
            #             part_id = cursor.fetchone()[0]
            #             stats['parts'] += 1
            #             log(f"      🔧 Created part: {part_number} (for product {ma_number})")
                    
            #         # Create BOM relationship
            #         if part_qty > 0:
            #             cursor.execute("""
            #                 INSERT INTO bill_of_materials (product_id, part_id, quantity, assembly_order, created_by)
            #                 VALUES (%s, %s, %s, %s, %s)
            #                 ON CONFLICT (product_id, part_id) DO UPDATE SET
            #                     quantity = EXCLUDED.quantity,
            #                     assembly_order = EXCLUDED.assembly_order,
            #                     updated_at = NOW()
            #             """, (product_id, part_id, part_qty, assembly_order, 'import'))
            #             stats['bom'] += 1
            #             log(f"      🔗 Added part: {part_number} x{part_qty}")
            
            
            
            # # Single part product (not assembly) - treat the product itself as a part
            # if not is_assembly and part_number:
            #     part_name = safe_str(row.get('Part_Name'), part_number)
            #     part_qty = safe_int(row.get('Part_Qty'), 1)
            #     part_dim_x = safe_float(row.get('Part_Length'))
            #     part_dim_y = safe_float(row.get('Part_Width'))
            #     part_dim_z = safe_float(row.get('Part_Height'))
            #     part_color = safe_str(row.get('color_code'))
            #     part_material = safe_str(row.get('material_code'))
            #     assembly_order = safe_int(row.get('Assembly_Order'), 0)

            #     # Get or create color
            #     part_color_id = None
            #     if part_color:
            #         cursor.execute("SELECT id FROM colors WHERE color_code ILIKE %s", (part_color,))
            #         result = cursor.fetchone()
            #         if result:
            #             part_color_id = result[0]
            #             log(f"      🎨 Found color: {part_color} (id={part_color_id})")

            #     # Get or create material
            #     part_material_id = None
            #     if part_material:
            #         cursor.execute("SELECT id FROM materials WHERE material_code ILIKE %s", (part_material,))
            #         result = cursor.fetchone()
            #         if result:
            #             part_material_id = result[0]

            #     # Get or create part
            #     cursor.execute("""SELECT parts.id  FROM parts
            #         LEFT JOIN product ON parts.product_id = product.id
            #         WHERE product.id = %s""", (product_id,))
            #     result = cursor.fetchone()
            #     if result:
            #         part_id = result[0]
            #         cursor.execute("""
            #             UPDATE parts 
            #             SET product_id = %s,
            #                 dimension_x = COALESCE(%s, dimension_x),
            #                 dimension_y = COALESCE(%s, dimension_y),
            #                 dimension_z = COALESCE(%s, dimension_z),
            #                 color_id = COALESCE(%s, color_id),
            #                 material_id = COALESCE(%s, material_id),
            #                 updated_at = NOW()
            #             WHERE id = %s
            #         """, (product_id, part_dim_x, part_dim_y, part_dim_z,
            #               part_color_id, part_material_id, part_id))
            #         log(f"      🔧 Updated part: {part_number}")
            #     else:
            #         cursor.execute("""
            #             INSERT INTO parts (
            #                 part_number, part_name, 
            #                 dimension_x, dimension_y, dimension_z,
            #                 color_id, material_id, 
            #                 current_stock, unit_of_measure, 
            #                 product_id, created_by
            #             )
            #             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            #             RETURNING id
            #         """, (
            #             part_number,
            #             part_name,
            #             part_dim_x,
            #             part_dim_y,
            #             part_dim_z,
            #             part_color_id,
            #             part_material_id,
            #             0,
            #             'pcs',
            #             product_id,
            #             'import'
            #         ))
            #         part_id = cursor.fetchone()[0]
            #         stats['parts'] += 1
            #         log(f"      🔧 Created part: {part_number} (for product {ma_number})")

            #     if part_qty > 0:
            #         cursor.execute("""
            #             INSERT INTO bill_of_materials (product_id, part_id, quantity, assembly_order, created_by)
            #             VALUES (%s, %s, %s, %s, %s)
            #             ON CONFLICT (product_id, part_id) DO UPDATE SET
            #                 quantity = EXCLUDED.quantity,
            #                 assembly_order = EXCLUDED.assembly_order,
            #                 updated_at = NOW()
            #         """, (product_id, part_id, part_qty, assembly_order, 'import'))
            #         stats['bom'] += 1
            #         log(f"      🔗 Added part: {part_number} x{part_qty}")        
                
                
                
                
            
            # =============================================
            # CREATE JOB ORDER (ONE per unique product per batch)
            # =============================================
            # if batch_id and batch_id > 0:
            #     job_key = f"{batch_id}_{ma_number}"
                
            #     if job_key not in processed_job_orders:
                    
            #         # Get or create batch
            #         cursor.execute("SELECT id, batch_number FROM batch WHERE id = %s", (batch_id,))
            #         batch_result = cursor.fetchone()
                    
            #         if batch_result:
            #             batch_number = batch_result[1]
            #             log(f"   📁 Using existing batch: {batch_number} (id={batch_id})")
            #         else:
            #             batch_number = f"BATCH-{batch_id:04d}"
            #             cursor.execute("""
            #                 INSERT INTO batch (id, batch_number, created_by, created_at)
            #                 VALUES (%s, %s, %s, NOW())
            #             """, (batch_id, batch_number, 'import'))
            #             stats['batches'] += 1
            #             log(f"   📁 Created new batch: {batch_number} (id={batch_id})")
                    
            #         quantity = safe_int(row.get('quantity', 1), 1)
                    
            #         # Use the next_job_number and increment it
            #         job_order_number = str(next_job_number)
            #         next_job_number += 1
                    
            #         cursor.execute("SELECT id FROM job_orders WHERE job_order_number = %s", (job_order_number,))
            #         existing_job = cursor.fetchone()
                    
            #         if not existing_job:
            #             cursor.execute("""
            #                 INSERT INTO job_orders (
            #                     job_order_number, batch_id, product_id, quantity, 
            #                     status, priority, created_by, created_at, updated_at
            #                 )
            #                 VALUES (%s, %s, %s, %s, 'pending', 'normal', %s, NOW(), NOW())
            #             """, (job_order_number, batch_id, product_id, quantity, 'import'))
                        
            #             stats['job_orders'] += 1
            #             log(f"   📋 Created job order: {job_order_number} - {ma_number} x{quantity}")
            #         else:
            #             log(f"   📋 Job order already exists: {job_order_number}")
                    
            #         processed_job_orders.add(job_key)
        
        conn.commit()
        
        # Final summary
        log("\n" + "=" * 70)
        log("✅ FULL PRODUCTION IMPORT COMPLETED!", "SUCCESS")
        log("=" * 70)
        log(f"   📦 Products: {stats['products']}")
        log(f"   🔧 Parts: {stats['parts']}")
        log(f"   🔗 BOM relationships: {stats['bom']}")
        log(f"   🎨 Colors: {stats['colors']}")
        log(f"   🔩 Materials: {stats['materials']}")
        log(f"   🏷️ Product types: {stats['types']}")
        log(f"   📁 Batches: {stats['batches']}")
        log(f"   📋 Job orders: {stats['job_orders']}")
        log(f"   ❌ Errors: {stats['errors']}")
        log("=" * 70)
        
        return True
        
    except Exception as e:
        log(f"❌ Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()