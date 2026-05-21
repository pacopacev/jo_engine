
import pandas as pd
from pathlib import Path
from utils import log, get_connection, safe_int, safe_datetime, safe_str


def import_price_offers(excel_file):
    
    excel_path = Path(excel_file)
    if not excel_path.exists():
        log(f"File not found: {excel_file}", "ERROR")
        return False
    
    try:
        df = pd.read_excel(excel_path, sheet_name='price_offer_list')
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
            price_offer_num = safe_int(row['price_offer_num'])
            created_at = safe_datetime(row.get('created_at'))
            updated_at = safe_datetime(row.get('updated_at'))
            created_by = safe_str(row.get('created_by'), 'system')
            
            cursor.execute("""
                INSERT INTO price_offers (price_offer_num, created_at, updated_at, created_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (price_offer_num) DO UPDATE SET
                    updated_at = NOW(),
                    created_by = EXCLUDED.created_by
            """, (price_offer_num, created_at, updated_at, created_by))
            
            stats['inserted'] += 1
            log(f"   ✅ Price offer {price_offer_num} processed")
        
        conn.commit()
        
        log("\n" + "=" * 70)
        log("✅ PRICE OFFERS IMPORT COMPLETED!", "SUCCESS")
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