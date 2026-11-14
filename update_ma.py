import datetime
from utils import log, get_connection, safe_str


def update_ma(old_ma, new_ma):
    old_ma = safe_str(old_ma)
    new_ma = safe_str(new_ma)

    if not old_ma or not new_ma:
        log("❌ Both old and new MA numbers are required", "ERROR")
        return False

    if old_ma == new_ma:
        log("⚠️ Old and new MA are identical, nothing to do", "WARNING")
        return False

    conn = get_connection()
    if not conn:
        return False

    cursor = conn.cursor()

    try:
        # 1. Product must exist
        cursor.execute(
            "SELECT id FROM products WHERE ma_number = %s",
            (old_ma,),
        )
        row = cursor.fetchone()
        if row is None:
            log(f"⚠️ No product found with MA {old_ma}", "WARNING")
            return False
        product_id = row[0]

        # 2. New MA must not be used by another product
        cursor.execute(
            "SELECT 1 FROM products WHERE ma_number = %s",
            (new_ma,),
        )
        if cursor.fetchone():
            log(f"❌ MA {new_ma} already exists", "ERROR")
            return False

        # 3. New part number must not be used by another product's parts
        cursor.execute(
            """
            SELECT 1 FROM parts
            WHERE LOWER(part_number) = LOWER(%s) AND product_id <> %s
            """,
            (new_ma, product_id),
        )
        if cursor.fetchone():
            log(f"❌ part_number {new_ma} already exists", "ERROR")
            return False

        now = datetime.datetime.now()

        # 4. Update both tables (same transaction)
        cursor.execute(
            """
            UPDATE products
            SET ma_number = %s, updated_at = %s
            WHERE id = %s
            """,
            (new_ma, now, product_id),
        )

        cursor.execute(
            """
            UPDATE parts
            SET part_number = %s, updated_at = %s
            WHERE product_id = %s
            """,
            (new_ma, now, product_id),
        )
        parts_updated = cursor.rowcount

        conn.commit()

        log("=" * 70)
        log("✅ PRODUCT MA UPDATED!", "SUCCESS")
        log(f"   {old_ma} → {new_ma} ({parts_updated} part(s) updated)")
        log("=" * 70)
        return True

    except Exception as e:
        log(f"❌ Error: {e}", "ERROR")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()