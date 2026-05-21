
import pandas as pd
from pathlib import Path
from utils import log, get_connection, safe_int, safe_datetime, safe_str


def import_colors(excel_file):
    
    excel_path = Path(excel_file)
    
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='color_list')
        
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
            color_code = safe_str(row['color_code'])
            color_name = safe_str(row['color_name'])
            color_name_bg = safe_str(row['color_name_bg'])
            rgb_value = safe_str(row.get('rgb_value'))
            pantone_code = safe_str(row.get('pantone_code'))
            created_at = safe_datetime(row.get('created_at'))
            updated_at = safe_datetime(row.get('updated_at'))
            created_by = safe_str(row.get('created_by'), 'system')
            
            cursor.execute("""
                INSERT INTO colors (color_code, color_name, color_name_bg, rgb_value, pantone_code, created_at, updated_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (color_code) DO UPDATE SET
                    color_name = EXCLUDED.color_name,
                    color_name_bg = EXCLUDED.color_name_bg,
                    rgb_value = EXCLUDED.rgb_value,
                    pantone_code = EXCLUDED.pantone_code,
                    updated_at = NOW(),
                    created_by = EXCLUDED.created_by
            """, (color_code, color_name, color_name_bg, rgb_value, pantone_code, created_at, updated_at, created_by))
            
            stats['inserted'] += 1
            log(f"   ✅ Color {color_code} processed")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ COLORS IMPORT COMPLETED!", "SUCCESS")
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