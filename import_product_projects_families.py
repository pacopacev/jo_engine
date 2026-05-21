
import pandas as pd
from pathlib import Path
from utils import log, get_connection, safe_int, safe_datetime, safe_str





def import_product_projects(excel_file):
    """Import product-project relationships"""
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='product_projects')
        log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    stats = {'inserted': 0, 'errors': 0}
    
    try:
        for idx, row in df.iterrows():
            product_ma = safe_str(row.get('product_ma'))
            project_name = safe_str(row.get('project_name'))
            
            if not product_ma or not project_name:
                log(f"   ⚠️ Skipping row {idx}: missing product_ma or project_name", "WARNING")
                stats['errors'] += 1
                continue
            
            # Get product_id
            cursor.execute("SELECT id FROM products WHERE ma_number = %s", (product_ma,))
            product_result = cursor.fetchone()
            if not product_result:
                log(f"   ⚠️ Product not found: {product_ma}", "WARNING")
                stats['errors'] += 1
                continue
            product_id = product_result[0]
            
            # Get or create project
            cursor.execute("SELECT id FROM projects WHERE project_code = %s OR project_name = %s", 
                          (project_name, project_name))
            project_result = cursor.fetchone()
            
            if project_result:
                project_id = project_result[0]
            else:
                cursor.execute("""
                    INSERT INTO projects (project_code, project_name, created_by)
                    VALUES (%s, %s, %s) RETURNING id
                """, (project_name.upper(), project_name, 'import'))
                project_id = cursor.fetchone()[0]
                log(f"   📁 Created new project: {project_name}")
            
            # Create relationship
            cursor.execute("""
                INSERT INTO product_projects (product_id, project_id, created_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (product_id, project_id) DO NOTHING
            """, (product_id, project_id, 'import'))
            
            if cursor.rowcount > 0:
                stats['inserted'] += 1
                log(f"   ✅ Linked {product_ma} -> project: {project_name}")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ PRODUCT-PROJECT IMPORT COMPLETED!", "SUCCESS")
        log(f"   Inserted: {stats['inserted']}")
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


def import_product_families(excel_file):
    """Import product-family relationships"""
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='product_families')
        log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    stats = {'inserted': 0, 'errors': 0}
    
    try:
        for idx, row in df.iterrows():
            product_ma = safe_str(row.get('product_ma'))
            family_name = safe_str(row.get('family_name'))
            
            if not product_ma or not family_name:
                log(f"   ⚠️ Skipping row {idx}: missing product_ma or family_name", "WARNING")
                stats['errors'] += 1
                continue
            
            # Get product_id
            cursor.execute("SELECT id FROM products WHERE ma_number = %s", (product_ma,))
            product_result = cursor.fetchone()
            if not product_result:
                log(f"   ⚠️ Product not found: {product_ma}", "WARNING")
                stats['errors'] += 1
                continue
            product_id = product_result[0]
            
            # Get or create family
            cursor.execute("SELECT id FROM families WHERE family_code = %s OR family_name = %s", 
                          (family_name, family_name))
            family_result = cursor.fetchone()
            
            if family_result:
                family_id = family_result[0]
            else:
                cursor.execute("""
                    INSERT INTO families (family_code, family_name, created_by)
                    VALUES (%s, %s, %s) RETURNING id
                """, (family_name.upper(), family_name, 'import'))
                family_id = cursor.fetchone()[0]
                log(f"   👨‍👩‍👧‍👦 Created new family: {family_name}")
            
            # Create relationship
            cursor.execute("""
                INSERT INTO product_families (product_id, family_id, created_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (product_id, family_id) DO NOTHING
            """, (product_id, family_id, 'import'))
            
            if cursor.rowcount > 0:
                stats['inserted'] += 1
                log(f"   ✅ Linked {product_ma} -> family: {family_name}")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ PRODUCT-FAMILY IMPORT COMPLETED!", "SUCCESS")
        log(f"   Inserted: {stats['inserted']}")
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