
import pandas as pd
from pathlib import Path
from utils import log, get_connection, safe_int, safe_datetime, safe_str


def import_types(excel_file):
    
    excel_path = Path(excel_file)
    
    
    
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='type_list')
        
        print("Columns in Excel:", df.columns.tolist())
        print("\nFirst row:")
        print(df.head(1))

        log(f"✅ Loaded {len(df)} rows from Excel")
    except Exception as e:
        log(f"Error reading Excel: {e}", "ERROR")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    stats = {'inserted': 0, 'updated': 0, 'errors': 0}
    
    try:
        for idx, row in df.iterrows():
            # Get values from Excel row (INDENTED PROPERLY)
            type_code = safe_str(row['type_code'])
            type_name = safe_str(row['type_name'])
            description = safe_str(row.get('description'))
            created_at = safe_datetime(row.get('created_at'))
            updated_at = safe_datetime(row.get('updated_at'))
            created_by = safe_str(row.get('created_by'), 'system')
            
            cursor.execute("""
                INSERT INTO product_type (type_code, type_name, description, created_at, updated_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (type_code) DO UPDATE SET
                    type_name = EXCLUDED.type_name,
                    description = EXCLUDED.description,
                    updated_at = NOW(),
                    created_by = EXCLUDED.created_by
            """, (type_code, type_name, description, created_at, updated_at, created_by))
            
            stats['inserted'] += 1
            log(f"   ✅ Product type {type_code} processed")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ PRODUCT TYPES IMPORT COMPLETED!", "SUCCESS")
        log(f"   Processed: {stats['inserted']}")
        log("=" * 70)
        
        return True
        
    except Exception as e:
        log(f"❌ Error: {e}", "ERROR")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()   