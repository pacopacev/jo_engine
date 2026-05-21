# batch_production_system.py - UPDATED WITH PROJECTS AND TYPES
"""
COMPLETE BATCH PRODUCTION SYSTEM - WITH PROJECTS AND PRODUCT TYPES
"""

import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os
from pathlib import Path
from datetime import datetime
from full_import import import_full_production_data
import querys
from utils import log, get_connection, safe_int, safe_str, safe_datetime, safe_bool, safe_float
from import_price_offer import import_price_offers
from import_type import import_types
from full_import import import_full_production_data
from import_color import import_colors
from import_material import import_materials
from create_job_order import create_job_orders_from_batch
from print_job_order import print_job_orders
from import_product_projects_families import import_product_projects, import_product_families




# =============================================
# PROJECT FUNCTIONS
# =============================================

def get_or_create_project(cursor, project_code, project_name=None, created_by='import'):
    """Get or create project"""
    if not project_code or pd.isna(project_code):
        return None
    
    project_code = safe_str(project_code)
    if not project_code:
        return None
    
    cursor.execute("SELECT id FROM projects WHERE project_code ILIKE %s", (project_code,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    if not project_name:
        project_name = project_code
    
    cursor.execute("""
        INSERT INTO projects (project_code, project_name, created_by)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (project_code, project_name, created_by))
    
    log(f"   📁 Created new project: {project_code} - {project_name}")
    return cursor.fetchone()[0]

# =============================================
# PRODUCT TYPE FUNCTIONS
# =============================================

def get_or_create_product_type(cursor, type_code, type_name=None, created_by='import'):
    """Get or create product type"""
    print(f"   🏷️ Processing product type: '{type_code}'")
    if not type_code or pd.isna(type_code):
        return None
    
    type_code = safe_str(type_code)
    if not type_code:
        return None
    
    cursor.execute("SELECT id FROM product_type WHERE type_code ILIKE %s", (type_code,))
    result = cursor.fetchone()
    
    if result:
        # print(f"   🏷️ Found existing product type: '{type_code}' (id={result[0]})")
        return result[0]
    
    if not type_name:
        type_name = type_code
    
    # cursor.execute("""
    #     INSERT INTO product_type (type_code, type_name, created_by)
    #     VALUES (%s, %s, %s)
    #     RETURNING id
    # """, (type_code, type_name, created_by))
    
    log(f"   🏷️ Created new product type: {type_code} - {type_name}")
    return cursor.fetchone()[0]

# =============================================
# COLOR FUNCTIONS
# =============================================

def get_or_create_color(cursor, color_name, created_by='import'):
    if not color_name or pd.isna(color_name):
        return None
    
    color_name = safe_str(color_name)
    if not color_name:
        return None
    
    cursor.execute("SELECT id FROM colors WHERE color_name ILIKE %s", (color_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    color_code = color_name.upper().replace(' ', '_')
    cursor.execute("""
        INSERT INTO colors (color_code, color_name, created_by)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (color_code, color_name, created_by))
    
    log(f"   🎨 Created new color: {color_name}")
    return cursor.fetchone()[0]

# =============================================
# MATERIAL FUNCTIONS
# =============================================

def get_or_create_material(cursor, material_name, created_by='import'):
    if not material_name or pd.isna(material_name):
        return None
    
    material_name = safe_str(material_name)
    if not material_name:
        return None
    
    cursor.execute("SELECT id FROM materials WHERE material_name ILIKE %s", (material_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    material_code = material_name.upper().replace(' ', '_')
    cursor.execute("""
        INSERT INTO materials (material_code, material_name, created_by)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (material_code, material_name, created_by))
    
    log(f"   🔩 Created new material: {material_name}")
    return cursor.fetchone()[0]

# =============================================
# PART FUNCTIONS
# =============================================

def get_or_create_part(cursor, part_number, dim_x, dim_y, dim_z, color_id, material_id, created_by='import'):
    if not part_number or pd.isna(part_number):
        return None
    
    part_number = safe_str(part_number)
    if not part_number:
        return None
    
    cursor.execute("SELECT id FROM parts WHERE part_number = %s", (part_number,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    cursor.execute("""
        INSERT INTO parts (
            part_number, part_name, 
            dimension_x, dimension_y, dimension_z,
            color_id, material_id, 
            current_stock, unit_of_measure, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (part_number, part_number, dim_x, dim_y, dim_z, color_id, material_id, 0, 'pcs', created_by))
    
    log(f"   🔧 Created new part: {part_number}")
    return cursor.fetchone()[0]

def upsert_product(cursor, ma_number, type_id, name, description, is_assembly, created_by='import'):
    """Insert or update product with project and type"""
    print(type_id)
    cursor.execute("""
        INSERT INTO products (ma_number, name, type_id, description, is_assembly, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (ma_number) DO UPDATE SET
            name = EXCLUDED.name,
            type_id = EXCLUDED.type_id,
            description = EXCLUDED.description,
            is_assembly = EXCLUDED.is_assembly,
            updated_at = NOW()
        RETURNING id
    """, (ma_number, name, type_id, description, is_assembly, created_by))
    
    return cursor.fetchone()[0]

# =============================================
# IMPORT FUNCTION
# =============================================


def import_products_and_parts(excel_file):
    """Import products, parts, and BOM from Excel with projects and types"""
    
    log("=" * 70, "START")
    log("📦 IMPORTING PRODUCTS & PARTS (with Projects & Types)", "START")
    log("=" * 70, "START")
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='products')
        log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    
    try:
        for ma_number in df['MA_Number'].dropna().unique():
            ma_number = safe_str(ma_number)
            log(f"\n📦 Processing product: {ma_number}")
            
            product_rows = df[df['MA_Number'] == ma_number]
            first_row = product_rows.iloc[0]
            
            product_name = safe_str(first_row.get('Product_Name'), '')
            description = safe_str(first_row.get('Description'))
            is_assembly = safe_bool(first_row.get('Is_Assembly', False))
            

            
            # Get or create product type
            type_code = safe_str(first_row.get('type_code'))
            print(f"Type code from Excel: '{type_code}'")
            type_id = None
            if type_code:
                type_id = get_or_create_product_type(cursor, type_code, type_code, 'excel_import')
               
            
            # Insert product
            product_id = upsert_product(
                cursor, 
                ma_number,
                type_id, 
                product_name,
                description,
                is_assembly,
                'excel_import'
            )
           
            log(f"   ✅ Product saved: {ma_number} (id={product_id})")

 
            
            # If assembly, process parts
            if is_assembly:
                cursor.execute("DELETE FROM bill_of_materials WHERE product_id = %s", (product_id,))
                
                for _, part_row in product_rows.iterrows():
                    part_number = part_row.get('Part_Number')
                    if pd.isna(part_number) or part_number is None:
                        continue
                    
                    part_number = safe_str(part_number)
                    if not part_number:
                        continue
                    
                    part_qty = safe_int(part_row.get('Part_Qty'), 1)
                    part_dim_x = safe_float(part_row.get('Part_Length'))
                    part_dim_y = safe_float(part_row.get('Part_Width'))
                    part_dim_z = safe_float(part_row.get('Part_Height'))
                    part_color = safe_str(part_row.get('Part_Color'))
                    part_material = safe_str(part_row.get('Part_Material'))
                    assembly_order = safe_int(part_row.get('Assembly_Order'), 0)
                    
                    part_color_id = None
                    if part_color:
                        part_color_id = get_or_create_color(cursor, part_color, 'excel_import')
                        
                    
                    part_material_id = None
                    if part_material:
                        part_material_id = get_or_create_material(cursor, part_material, 'excel_import')
                        
                    
                    part_id = get_or_create_part(
                        cursor,
                        part_number,
                        part_dim_x,
                        part_dim_y,
                        part_dim_z,
                        part_color_id,
                        part_material_id,
                        'excel_import'
                    )
                  
                    
                    cursor.execute("""
                        INSERT INTO bill_of_materials (product_id, part_id, quantity, assembly_order, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (product_id, part_id) DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            updated_at = NOW()
                    """, (product_id, part_id, part_qty, assembly_order, 'excel_import'))
                    
                    log(f"   🔗 Added part: {part_number} x{part_qty}")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ PRODUCTS & PARTS IMPORT COMPLETED!", "SUCCESS")
        
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

# # =============================================
# # VIEW FUNCTIONS
# # =============================================

# def list_all_products():
#     """List all products with projects and types"""
#     conn = get_connection()
#     if not conn:
#         return None
    
#     cursor = conn.cursor()
    
#     try:
#         cursor.execute("""
#             SELECT 
#                 p.ma_number, 
#                 p.name, 
#                 p.is_assembly,
#                 pr.project_code,
#                 pt.type_code
#             FROM products p
#             LEFT JOIN projects pr ON p.project_id = pr.id
#             LEFT JOIN product_type pt ON p.type_id = pt.id
#             ORDER BY p.ma_number
#         """)
        
#         results = cursor.fetchall()
        
#         if results:
#             print("\n" + "=" * 80)
#             print("📦 PRODUCTS CATALOG")
#             print("=" * 80)
#             for row in results:
#                 type_str = "Assembly" if row[2] else "Simple"
#                 project = row[3] or "No Project"
#                 prod_type = row[4] or "No Type"
#                 print(f"   {row[0]} - {row[1]} ({type_str}) | Project: {project} | Type: {prod_type}")
#             print("=" * 80)
#         else:
#             print("\n❌ No products found")
        
#         cursor.close()
#         conn.close()
#         return results
        
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         return None

# def list_all_projects():
#     """List all projects"""
#     conn = get_connection()
#     if not conn:
#         return None
    
#     cursor = conn.cursor()
    
#     try:
#         cursor.execute("""
#             SELECT project_code, project_name, status, 
#                    COUNT(p.id) as product_count
#             FROM projects pr
#             LEFT JOIN products p ON pr.id = p.project_id
#             GROUP BY pr.id
#             ORDER BY project_code
#         """)
        
#         results = cursor.fetchall()
        
#         if results:
#             print("\n" + "=" * 80)
#             print("📁 PROJECTS")
#             print("=" * 80)
#             for row in results:
#                 print(f"   {row[0]} - {row[1]} | Status: {row[2]} | Products: {row[3]}")
#             print("=" * 80)
#         else:
#             print("\n❌ No projects found")
        
#         cursor.close()
#         conn.close()
#         return results
        
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         return None

# def list_all_product_types():
#     """List all product types"""
#     conn = get_connection()
#     if not conn:
#         return None
    
#     cursor = conn.cursor()
    
#     try:
#         cursor.execute("""
#             SELECT type_code, type_name, 
#                    COUNT(p.id) as product_count
#             FROM product_type pt
#             LEFT JOIN products p ON pt.id = p.type_id
#             GROUP BY pt.id
#             ORDER BY type_code
#         """)
        
#         results = cursor.fetchall()
        
#         if results:
#             print("\n" + "=" * 80)
#             print("🏷️ PRODUCT TYPES")
#             print("=" * 80)
#             for row in results:
#                 print(f"   {row[0]} - {row[1]} | Products: {row[2]}")
#             print("=" * 80)
#         else:
#             print("\n❌ No product types found")
        
#         cursor.close()
#         conn.close()
#         return results
        
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         return None

# =============================================
# MAIN
# =============================================

# =============================================
# MAIN
# =============================================

def main():
    
    if len(sys.argv) < 2:
        print("\n" + "=" * 60)
        print("BATCH PRODUCTION SYSTEM (with Projects & Types)")
        print("=" * 60)
        print("\nCommands:")
        print("  pr <excel_file>              - Import products & parts from Excel")
        print("  p <excel_file>               - Import price offers from Excel")
        print("  t <excel_file>               - Import product types from Excel")
        print("  full-import <excel_file> [batch_id] - Full import with job orders")
        print("  create-jobs <excel_file> [batch_id] - Create only job orders")
        print("  products                     - List all products")
        print("  parts                        - List all parts")
        print("  projects                     - List all projects")
        print("  types                        - List all product types")
        print("  active                       - List active jobs")
        print("\nExamples:")
        print("  python batch_production_system.py pr products_data.xlsx")
        print("  python batch_production_system.py p price_offers.xlsx")
        print("  python batch_production_system.py t types.xlsx")
        print("  python batch_production_system.py full-import data.xlsx")
        print("  python batch_production_system.py full-import data.xlsx 1")
        print("  python batch_production_system.py create-jobs data.xlsx 2")
        print("=" * 60)
        return
    
    command = sys.argv[1]

    # Import price offers
    if command == 'price':
        if len(sys.argv) > 2:
            import_price_offers(sys.argv[2])
        else:
            print("Please provide Excel file name")
    
    # Import products and parts
    elif command == 'products':
        if len(sys.argv) > 2:
            import_products_and_parts(sys.argv[2])
        else:
            print("Please provide Excel file name")
    elif command == 'colors':
        if len(sys.argv) > 2:
            import_colors(sys.argv[2])
        else:
            print("Please provide Excel file name")
            
    elif command == 'materials':
        if len(sys.argv) > 2:
            import_materials(sys.argv[2])
        else:
            print("Please provide Excel file name")
            
    elif command == 'families':
        if len(sys.argv) > 2:
            import_product_families(sys.argv[2])
        else:
            print("Please provide Excel file name")
            
    elif command == 'projects':
        if len(sys.argv) > 2:
            import_product_projects(sys.argv[2])
        else:
            print("Please provide Excel file name")
    
    # Import types
    elif command == 'types':
        if len(sys.argv) > 2:
            import_types(sys.argv[2])
        else:
            print("Please provide Excel file name")
    
    # Full import (products, parts, BOM, and job orders)
    elif command == 'full-import':
        if len(sys.argv) > 2:
            excel_file = sys.argv[2]
            batch_id = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
            import_full_production_data(excel_file, batch_id)
        else:
            print("Please provide Excel file name")
    
    # Create only job orders
    elif command == 'cj':
        if len(sys.argv) > 2:
            excel_file = sys.argv[2]
            batch_id = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
            create_job_orders_from_batch(excel_file, batch_id)
        else:
            print("Please provide Excel file name")
    elif command == 'pjobs': 
        # print(sys.argv[2])
        if len(sys.argv) == 3:
            batch_id = int(sys.argv[2])
            print_job_orders(batch_id)
        else:
            print("Please provide batch ID")
    
    # List products
    # elif command == 'products':
    #     list_all_products()
    
    # # List parts
    # elif command == 'parts':
    #     list_all_parts()
    
    # # List projects
    # elif command == 'projects':
    #     list_all_projects()
    
    # # List product types
    # elif command == 'types':
    #     list_all_product_types()
    
    # # List active jobs
    # elif command == 'active':
    #     list_active_jobs()
    
    else:
        print(f"Unknown command: {command}")
        print("\nTry 'python batch_production_system.py' for help")



if __name__ == "__main__":
    main()