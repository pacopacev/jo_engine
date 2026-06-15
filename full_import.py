# full_import.py - Complete working version with product_id in parts
import pandas as pd
from pathlib import Path
from datetime import datetime
# from utils import log, get_connection, safe_int, safe_datetime, safe_str, safe_bool, safe_float
from globalModel import GlobalModel

global_model = GlobalModel()



def import_full_production_data(excel_file, target_batch_id=None):
    """
    Import products, parts, BOM from Excel with parent-child structure
    Parent row: Has MA_Number, Is_Assembly=TRUE, Part_Number empty
    Child rows: Have Part_Number, parent_ma (references parent MA_Number)
    """
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        global_model.log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='product_list')
        global_model.log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        global_model.log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = global_model.conn
    if not conn:
        return False
    
    cursor = conn.cursor()
    stats = {
        'products': 0, 'parts': 0, 'bom': 0, 
        'colors': 0, 'materials': 0, 'types': 0,
        'batches': 0, 'errors': 0
    }
    
    # Cache for colors and materials
    color_cache = {}
    material_cache = {}
    
    # Store parent product IDs
    parent_products = {}
    
    # Store part IDs for BOM
    part_ids = {}
    
    try:
        # =============================================
        # FIRST PASS: Create all parent products
        # =============================================
        for idx, row in df.iterrows():
            
            # Get batch_id first
            batch_id = global_model.safe_int(row.get('batch_id'), None)
            
            # Filter by target batch_id
            if target_batch_id is not None and batch_id != target_batch_id:
                continue
            
            # Insert price offer
            price_offer_num_raw = row.get('price_offer_num')
            if pd.notna(price_offer_num_raw):
                try:
                    price_offer_num = str(int(float(price_offer_num_raw)))
                except (ValueError, TypeError):
                    price_offer_num = global_model.safe_str(price_offer_num_raw)
            else:
                price_offer_num = None

            if price_offer_num:
                global_model.log(f"Inserting price offer: {price_offer_num}")
                created_by = 'import batch'
                cursor.execute("""
                    INSERT INTO price_offers (price_offer_num, created_at, updated_at, created_by, batch_id)
                    VALUES (%s, NOW(), NOW(), %s, %s)
                    ON CONFLICT (price_offer_num) DO UPDATE SET
                        updated_at = NOW(),
                        created_by = EXCLUDED.created_by,
                        batch_id = EXCLUDED.batch_id
                    RETURNING id
                """, (price_offer_num, created_by, batch_id))
                price_offer_id = cursor.fetchone()[0]
                global_model.log(f"   ✅ Price offer {price_offer_num} processed with id {price_offer_id}")
            
            ma_number = global_model.safe_str(row.get('MA_Number'))
            
            # Skip rows without MA_Number (child rows)
            if not ma_number:
                continue
            
            global_model.log(f"\n📦 Processing product: {ma_number}")
            
            product_name = global_model.safe_str(row.get('Product_Name'), '')
            description = global_model.safe_str(row.get('Description'))
            is_assembly = global_model.safe_bool(row.get('Is_Assembly', False))
            type_code = global_model.safe_str(row.get('type_code'))
            alt_name = global_model.safe_str(row.get('alt_name'))
            
            # Get or create product type
            type_id = None
            if type_code:
                cursor.execute("SELECT id FROM product_type WHERE type_code = %s", (type_code,))
                result = cursor.fetchone()
                if result:
                    type_id = result[0]
                else:
                    cursor.execute("""
                        INSERT INTO product_type (type_code, type_name, created_by, updated_at, alt_name)
                        VALUES (%s, %s, %s, NOW(), %s)
                        ON CONFLICT (type_code) 
                        DO UPDATE SET 
                        type_name = EXCLUDED.type_name,
                        updated_at = NOW(),
                        created_by = EXCLUDED.created_by,
                        alt_name = EXCLUDED.alt_name
                        RETURNING id
                    """, (type_code, type_code, 'system', alt_name))
                    type_id = cursor.fetchone()[0]
                    stats['types'] += 1
                    global_model.log(f"   🏷️ Created type: {type_code}")
            
            # Insert or update product
            cursor.execute("""
                INSERT INTO products (ma_number, name, description, is_assembly, type_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ma_number) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_assembly = EXCLUDED.is_assembly,
                    type_id = EXCLUDED.type_id,
                    updated_at = NOW()
                RETURNING id
            """, (ma_number, product_name, description, is_assembly, type_id, 'import'))
            
            parent_id = cursor.fetchone()[0]
            parent_products[ma_number] = parent_id
            stats['products'] += 1
            global_model.log(f"   ✅ Product saved: {ma_number} (id={parent_id})")
            
            # Get color and material IDs
            color_code = global_model.safe_str(row.get('color_code'))
            material_code = global_model.safe_str(row.get('material_code'))
            
            # Get or create color
            color_id = None
            if color_code:
                color_code_upper = color_code.upper()
                if color_code_upper in color_cache:
                    color_id = color_cache[color_code_upper]
                else:
                    cursor.execute("SELECT id FROM colors WHERE color_code = %s", (color_code_upper,))
                    result = cursor.fetchone()
                    if result:
                        color_id = result[0]
                        color_cache[color_code_upper] = color_id
            
            # Get or create material
            material_id = None
            if material_code:
                material_code_upper = material_code.upper()
                if material_code_upper in material_cache:
                    material_id = material_cache[material_code_upper]
                else:
                    cursor.execute("SELECT id FROM materials WHERE material_code = %s", (material_code_upper,))
                    result = cursor.fetchone()
                    if result:
                        material_id = result[0]
                        material_cache[material_code_upper] = material_id
            
            # Get dimensions
            part_dim_x = global_model.safe_float(row.get('Part_Length'))
            part_dim_y = global_model.safe_float(row.get('Part_Width'))
            part_dim_z = global_model.safe_float(row.get('Part_Height'))
            process_cut = global_model.safe_bool(row.get('process_cut'))
            process_mill = global_model.safe_bool(row.get('process_mill'))
            
            
            # Insert or update part (parent part with product_id)
            cursor.execute("""
                INSERT INTO parts (part_number, part_name, dimension_x, dimension_y, dimension_z, color_id, material_id, parent_id, product_id, created_by, process_cut, process_mill)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (part_number) DO UPDATE SET
                    part_name = EXCLUDED.part_name,
                    dimension_x = EXCLUDED.dimension_x,
                    dimension_y = EXCLUDED.dimension_y,
                    dimension_z = EXCLUDED.dimension_z,
                    color_id = EXCLUDED.color_id,
                    material_id = EXCLUDED.material_id,
                    parent_id = EXCLUDED.parent_id,
                    product_id = EXCLUDED.product_id,
                    updated_at = NOW(),
                    process_cut = EXCLUDED.process_cut,
                    process_mill = EXCLUDED.process_mill
                RETURNING id
            """, (ma_number, product_name, part_dim_x, part_dim_y, part_dim_z, color_id, material_id, None, parent_id, 'system', process_cut, process_mill))
            
            part_id = cursor.fetchone()[0]
            part_ids[ma_number] = part_id
            stats['parts'] += 1
            global_model.log(f"   🔧 Created/Updated part record for product: {ma_number} (product_id={parent_id})")
        
            #create group processing
            group_processing = global_model.safe_bool(row.get('group_processing'))
            if group_processing:
                dimension_x_g = global_model.safe_float(row.get('dimension_x_g'))
                dimension_y_g = global_model.safe_float(row.get('dimension_y_g'))
                dimension_z_g = global_model.safe_float(row.get('dimension_z_g'))
                qty_per_group = global_model.safe_int(row.get('qty_per_group'), 1)
                cursor.execute("""
                    INSERT INTO parts_group_process (part_number, part_name, 
                    dimension_x_g, 
                    dimension_y_g, 
                    dimension_z_g, 
                    qty_per_group, 
                    color_id, 
                    material_id, 
                    created_at, 
                    updated_at, 
                    created_by, 
                    parent_id, 
                    product_id, 
                    process_cut, 
                    process_mill)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s, %s)
                    ON CONFLICT (part_number) DO UPDATE SET
                        updated_at = NOW(),
                        created_by = EXCLUDED.created_by,
                        parent_id = EXCLUDED.parent_id,
                        product_id = EXCLUDED.product_id,
                        dimension_x_g = EXCLUDED.dimension_x_g,
                        dimension_y_g = EXCLUDED.dimension_y_g,
                        dimension_z_g = EXCLUDED.dimension_z_g,
                        qty_per_group = EXCLUDED.qty_per_group,
                        process_cut = EXCLUDED.process_cut,
                        process_mill = EXCLUDED.process_mill
                    RETURNING id
                """, (ma_number, product_name, dimension_x_g, dimension_y_g, dimension_z_g, qty_per_group, color_id, material_id, 'system', parent_id, parent_id, process_cut, process_mill))
                group_id = cursor.fetchone()[0]
                global_model.log(f"   👥 Group processing assigned: {group_processing} (id={group_id})")
        # =============================================
        # SECOND PASS: Process child parts and BOM
        # =============================================
        for idx, row in df.iterrows():
            parent_ma = global_model.safe_str(row.get('parent_ma'))
            
            # Skip if not a child row
            if not parent_ma:
                continue
            
            # Filter by target batch_id
            batch_id = global_model.safe_int(row.get('batch_id'), None)
            if target_batch_id is not None and batch_id != target_batch_id:
                continue
            
            # Get parent product ID
            parent_product_id = parent_products.get(parent_ma)
            if not parent_product_id:
                global_model.log(f"   ⚠️ Parent product not found: {parent_ma}", "WARNING")
                stats['errors'] += 1
                continue
            
            part_number = global_model.safe_str(row.get('Part_Number'))
            if not part_number:
                continue
            
            part_qty = global_model.safe_int(row.get('Part_Qty'), 1)
            part_dim_x = global_model.safe_float(row.get('Part_Length'))
            part_dim_y = global_model.safe_float(row.get('Part_Width'))
            part_dim_z = global_model.safe_float(row.get('Part_Height'))
            assembly_order = global_model.safe_int(row.get('Assembly_Order'), 0)
            
            # Get color and material IDs for this child part
            color_code = global_model.safe_str(row.get('color_code'))
            material_code = global_model.safe_str(row.get('material_code'))
            process_cut = global_model.safe_bool(row.get('process_cut'))
            process_mill = global_model.safe_bool(row.get('process_mill'))
            
            # Get or use cached color
            color_id = None
            if color_code:
                color_code_upper = color_code.upper()
                if color_code_upper in color_cache:
                    color_id = color_cache[color_code_upper]
                else:
                    cursor.execute("SELECT id FROM colors WHERE color_code = %s", (color_code_upper,))
                    result = cursor.fetchone()
                    if result:
                        color_id = result[0]
                        color_cache[color_code_upper] = color_id
            
            # Get or use cached material
            material_id = None
            if material_code:
                material_code_upper = material_code.upper()
                if material_code_upper in material_cache:
                    material_id = material_cache[material_code_upper]
                else:
                    cursor.execute("SELECT id FROM materials WHERE material_code = %s", (material_code_upper,))
                    result = cursor.fetchone()
                    if result:
                        material_id = result[0]
                        material_cache[material_code_upper] = material_id
            
            # Insert or update child part with product_id
            cursor.execute("""
                INSERT INTO parts (
                    part_number, part_name, 
                    dimension_x, dimension_y, dimension_z,
                    color_id, material_id, 
                    current_stock, unit_of_measure, 
                    parent_id, product_id, created_by, process_cut, process_mill
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (part_number) DO UPDATE SET
                    part_name = EXCLUDED.part_name,
                    dimension_x = EXCLUDED.dimension_x,
                    dimension_y = EXCLUDED.dimension_y,
                    dimension_z = EXCLUDED.dimension_z,
                    color_id = EXCLUDED.color_id,
                    material_id = EXCLUDED.material_id,
                    parent_id = EXCLUDED.parent_id,
                    product_id = EXCLUDED.product_id,
                    updated_at = NOW(),
                    process_cut = EXCLUDED.process_cut,
                    process_mill = EXCLUDED.process_mill
                RETURNING id
            """, (part_number, part_number,
                  part_dim_x, part_dim_y, part_dim_z,
                  color_id, material_id,
                  0, 'pcs',
                  parent_product_id, parent_product_id, 'system', process_cut, process_mill)
            )
            part_id = cursor.fetchone()[0]
            stats['parts'] += 1
            global_model.log(f"      🔧 Created/Updated part: {part_number} (product_id={parent_product_id})")
            
            # Create BOM relationship
            cursor.execute("""
                INSERT INTO bill_of_materials (product_id, part_id, quantity, assembly_order, created_by)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (product_id, part_id) DO UPDATE SET
                    quantity = EXCLUDED.quantity,
                    assembly_order = EXCLUDED.assembly_order,
                    updated_at = NOW()
            """, (parent_product_id, part_id, part_qty, assembly_order, 'import'))
            stats['bom'] += 1
            global_model.log(f"      🔗 Added part: {part_number} x{part_qty}")
        
        # =============================================
        # COMMIT ALL CHANGES
        # =============================================
        conn.commit()
        global_model.log("✅ All changes committed to database")
        
        # Final summary
        global_model.log("\n" + "=" * 70)
        global_model.log("✅ FULL PRODUCTION IMPORT COMPLETED!", "SUCCESS")
        global_model.log("=" * 70)
        global_model.log(f"   📦 Products: {stats['products']}")
        global_model.log(f"   🔧 Parts: {stats['parts']}")
        global_model.log(f"   🔗 BOM relationships: {stats['bom']}")
        global_model.log(f"   🎨 Colors: {stats['colors']}")
        global_model.log(f"   🔩 Materials: {stats['materials']}")
        global_model.log(f"   🏷️ Product types: {stats['types']}")
        global_model.log(f"   📁 Batches: {stats['batches']}")
        global_model.log(f"   ❌ Errors: {stats['errors']}")
        global_model.log("=" * 70)
        
        return True
       
    except Exception as e:
        global_model.log(f"❌ Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()