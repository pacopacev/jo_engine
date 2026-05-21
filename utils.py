

import pandas as pd
import psycopg2
from datetime import datetime
import os
from pathlib import Path




# =============================================
# DATABASE CONFIGURATION (AIVEN CLOUD)
# =============================================
DB_CONFIG = {
    'host': 'pg-143cbe8e-pacopacev277-7915.e.aivencloud.com',
    'database': 'defaultdb',
    'user': 'avnadmin',
    'password': 'AVNS_LqW5lU_kmJDiLuips8n',
    'port': 11821,
    'sslmode': 'require'
}



# =============================================
# LOGGING
# =============================================

def log(message, type="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{type}] {message}")

# =============================================
# DATABASE CONNECTION
# =============================================
# =============================================
# HELPER FUNCTIONS
# =============================================

def safe_bool(value):
    """Safely convert to boolean"""
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', 'yes', '1', 't', 'y']
    try:
        return bool(value)
    except:
        return False

def safe_int(value, default=0):
    """Safely convert to integer"""
    if value is None or pd.isna(value):
        return default
    try:
        return int(float(value))
    except:
        return default

def safe_float(value, default=None):
    """Safely convert to float"""
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except:
        return default

def safe_str(value, default=None):
    """Safely convert to string"""
    if value is None or pd.isna(value):
        return default
    return str(value).strip()

def safe_datetime(value, default=None):
    """Safely convert to datetime"""
    if value is None or pd.isna(value):
        return default or datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        return pd.to_datetime(value).to_pydatetime()
    except:
        return default or datetime.now()
def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        log(f"Database connection failed: {e}", "ERROR")
        return None

# =============================================
# CONVERSION FUNCTIONS
# =============================================

def safe_bool(value):
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', 'yes', '1', 't', 'y']
    try:
        return bool(value)
    except:
        return False

def safe_int(value, default=0):
    if value is None or pd.isna(value):
        return default
    try:
        return int(float(value))
    except:
        return default

def safe_float(value, default=None):
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except:
        return default

def safe_str(value, default=None):
    if value is None or pd.isna(value):
        return default
    return str(value).strip()
