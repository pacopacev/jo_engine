
import pandas as pd
import psycopg2

DB_CONFIG = {
    'host': 'pg-143cbe8e-pacopacev277-7915.e.aivencloud.com',
    'database': 'defaultdb',
    'user': 'avnadmin',
    'password': 'AVNS_LqW5lU_kmJDiLuips8n',
    'port': 11821,
    'sslmode': 'require'
}

print('1. Reading Excel...')
df = pd.read_excel('products_data.xlsx', sheet_name='products')
print(f'   Loaded {len(df)} rows')

print('2. Connecting to database...')
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()
print('   Connected!')

print('3. Importing products...')
for idx, row in df.iterrows():
    ma = row['MA_Number']
    name = row['Product_Name']
    is_assembly = str(row.get('Is_Assembly', 'FALSE')).upper() == 'TRUE'
    print(f'   Processing: {ma} - {name}')
    
    cursor.execute('''
        INSERT INTO products (ma_number, name, description, is_assembly, created_by)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (ma_number) DO UPDATE SET
            name = EXCLUDED.name,
            updated_at = NOW()
    ''', (ma, name, row.get('Description'), is_assembly, 'cli_import'))

conn.commit()
print('4. Done!')

cursor.execute('SELECT COUNT(*) FROM products')
count = cursor.fetchone()
print(f'   Total products in database: {count[0]}')

cursor.close()
conn.close()
