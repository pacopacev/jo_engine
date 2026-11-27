import pandas as pd
from psycopg2 import pool
from datetime import datetime
import os
import re
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

class GlobalModel:
    MIN_CONNECTIONS = 1
    MAX_CONNECTIONS = 2
    _db_pool = None
    _db_pool_lock = Lock()

    def __init__(self):
        
        print("GlobalModel initialized")
 
        self.db_config = {
                    'host': os.getenv("DB_HOST"),
                    'database': os.getenv("DB_NAME"),
                    'user': os.getenv("DB_USER"), 
                    'password': os.getenv("DB_PASSWORD"),
                    'port': os.getenv("DB_PORT", "11821"),
                    'sslmode': 'require'
                }  
        
        self._conn = None

    @property
    def conn(self):
        if self._conn is not None and getattr(self._conn, 'closed', 0) != 0:
            self.close_connection()
        if self._conn is None:
            self._conn = self.connect_db()
        return self._conn

    @conn.setter
    def conn(self, connection):
        self._conn = connection

    @classmethod
    def _get_db_pool(cls, db_config):
        if cls._db_pool is None:
            with cls._db_pool_lock:
                if cls._db_pool is None:
                    cls._db_pool = pool.ThreadedConnectionPool(
                        cls.MIN_CONNECTIONS,
                        cls.MAX_CONNECTIONS,
                        **db_config
                    )
        return cls._db_pool
    
    def connect_db(self):
        """Borrows a live connection from the shared pool."""
        try:
            return self._get_db_pool(self.db_config).getconn()
        except Exception as e:
            self.log(f"Failed to get a database connection from the pool: {e}", "ERROR")
            return None 
    def log(self, message, type="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            print(f"[{timestamp}] [{type}] {message}")
        except OSError:
            pass  # Handle cases where the output stream is closed or unavailable
        
        
    def safe_bool(self, value):
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
    def safe_int(self, value, default=0):
        """Safely convert to integer"""
        if value is None or pd.isna(value):
            return default
        try:
            return int(float(value))
        except:
            return default    
    def safe_float(self, value, default=None):
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except:
            return default    
    def safe_str(self, value, default=None):    
        if value is None or pd.isna(value):
            return default
        try:
            return str(value)
        except:
            return default   
    def safe_date(self, value, default=None):
        if value is None or pd.isna(value):
            return default
        if isinstance(value, datetime):
            return value.date()
        try:
            return pd.to_datetime(value).date()
        except:
            return default
        
    def close_connection(self):
        """Returns the borrowed connection to the shared pool."""
        conn = getattr(self, '_conn', None)
        if conn is None:
            return

        self._conn = None
        try:
            discard = getattr(conn, 'closed', 0) != 0
            if not discard:
                try:
                    conn.rollback()
                except Exception as e:
                    self.log(f"Failed to reset database connection before returning it to the pool: {e}", "ERROR")
                    discard = True

            db_pool = type(self)._db_pool
            if db_pool is None:
                conn.close()
            else:
                db_pool.putconn(conn, close=discard)
            if discard:
                self.log("Discarded unusable database connection.", "WARNING")
            else:
                print("Database connection returned to pool.")
        except Exception as e:
            self.log(f"Error while returning database connection to pool: {e}", "ERROR")
            
    def findT(self, ma):
        return bool(re.findall("T$", ma))

    


    def name_replace(self, name: str):
        new_name = ""
        # print(len(str(name)))

        if(len(str(name)) == 10):
            new_name = name[0:4] + " " + name[4:8] + " " + name[8:10]
            return new_name
        elif(len(str(name)) == 8):
            new_name = name[0:4] + " " + name[4:8]
            return new_name
        elif(len(str(name)) == 20 and name[10:11] == "+"): #7283 2233 60 + 7283 2233A
            new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + name[19:20]
            return new_name 
        elif(len(str(name)) == 21 and name[10:11] == "+"): #7283 6004 30 + 7283 6005 30
            new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21]
            return new_name  
        elif(len(str(name)) == 22 and name[10:11] == "+"): #7283 2233 60 + 7283 2233 60A
            new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21] + name[21:22]
            return new_name   
        elif(len(str(name)) == 31 and name[10:11] == "+"): #7283 6004 30 + 7283 6005 30 + 7283 2244A
            new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21] + " " + name[21:22] + " " + name[22:26] + " " + name[26:30] + name[30:31]
            return new_name 
        elif(len(str(name)) == 33 and name[10:11] == "+"): #7283 6004 30 + 7283 6005 30 + 7283 2244 60A
            new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21] + " " + name[21:22] + " " + name[22:26] + " " + name[26:30] + " " + name[30:33]
            return new_name
        else:
            return name
    
    
    def __del__(self):
            """Destructor to clean up resources when the object is destroyed"""
            self.close_connection()
