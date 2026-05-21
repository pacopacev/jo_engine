
import pandas as pd
from pathlib import Path
from utils import log, get_connection, safe_float, safe_int, safe_datetime, safe_str


def import_materials(excel_file):
    
    excel_path = Path(excel_file)
    
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='material_list')
        
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
            material_code = safe_str(row['material_code'])
            material_name = safe_str(row['material_name'])
            material_name_bg = safe_str(row['material_name_bg'])
            category = safe_str(row.get('category'))
            density_kg_per_m3 = safe_float(row.get('density_kg_per_m3'))
            tensile_strength_mpa = safe_float(row.get('tensile_strength_mpa'))
            cost_per_kg = safe_float(row.get('cost_per_kg'))
            created_at = safe_datetime(row.get('created_at'))
            updated_at = safe_datetime(row.get('updated_at'))
            created_by = safe_str(row.get('created_by'), 'system')
            
            cursor.execute("""
                INSERT INTO materials (material_code, material_name, material_name_bg, category, density_kg_per_m3, tensile_strength_mpa, cost_per_kg, created_at, updated_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (material_code) DO UPDATE SET
                    material_name = EXCLUDED.material_name,
                    material_name_bg = EXCLUDED.material_name_bg,
                    category = EXCLUDED.category,
                    density_kg_per_m3 = EXCLUDED.density_kg_per_m3,
                    tensile_strength_mpa = EXCLUDED.tensile_strength_mpa,
                    cost_per_kg = EXCLUDED.cost_per_kg,
                    updated_at = NOW(),
                    created_by = EXCLUDED.created_by
            """, (material_code, material_name, material_name_bg, category, density_kg_per_m3, tensile_strength_mpa, cost_per_kg, created_at, updated_at, created_by))
            
            stats['inserted'] += 1
            log(f"   ✅ Material {material_code} processed")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ MATERIALS IMPORT COMPLETED!", "SUCCESS")
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