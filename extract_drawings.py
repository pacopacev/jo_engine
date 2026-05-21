
# full_import.py - Complete working version with product_id in parts
import os
import glob
from pathlib import Path
from datetime import datetime
from utils import log, get_connection, safe_int, safe_datetime, safe_str, safe_bool, safe_float



def getDrawing(root_path, keyword, extension=".pdf"):
    matching_files = []
    try:
        for folder_path, subdirs, files in os.walk(root_path):
                for filename in files:
                    if keyword in filename and filename.endswith(extension):
                        full_path = os.path.join(folder_path, filename)
                        matching_files.append(full_path)
    except Exception as e:
        log(f"Error occurred while fetching drawings: {e}", "ERROR")
    return matching_files

