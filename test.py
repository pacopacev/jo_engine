
# import os
# import glob
# from pathlib import Path
# from datetime import datetime
# from utils import log, get_connection, safe_int, safe_datetime, safe_str, safe_bool, safe_float
# import shutil


# def getData(root_path, keywords):
#     matching_files = []
#     allowed_extensions = ["", ".txt"]  # Empty string = no extension
#     try:
#         keyword_strs = [str(k) for k in keywords]
        
#         for folder_path, subdirs, files in os.walk(root_path):
#             for filename in files:
#                 file_ext = Path(filename).suffix  # e.g., ".txt" or ""
                
#                 # Only keep files with no extension OR .txt
#                 if file_ext not in allowed_extensions:
#                     continue
                
#                 if any(kw in filename for kw in keyword_strs):
#                     full_path = os.path.join(folder_path, filename)
#                     matching_files.append(full_path)
#     except Exception as e:
#         print(f"Error occurred while fetching drawings: {e}")
#     return matching_files


# search_ids = [96564,
# 77405,
# 64080,
# 70526,
# 69492,
# 77265,
# 90091,
# 53368,
# 72966,
# 83796,
# 71225,
# 38917,
# 43815,
# 43817,
# 38043,
# 37930,
# 96690,
# 69542,
# 77033,
# 63723,
# 84415,
# 73033,
# 83586,
# 77369,
# 43822,
# 43823,
# 48627,
# 71356,
# 69559,
# 72183,
# 84747,
# 72173,
# 37808,
# 79266,
# 79308,
# 79265,
# 90094,
# 48718,
# 37965,
# 37987,
# 38683,
# 37986,
# 37988,
# 37885,
# 37887,
# 52058,
# 83767,
# 83757,
# 77164,
# 65867,
# 73023,
# 73032,
# 73022,
# 76952,
# 80788,
# 76951,
# 37923,
# 41552,
# 73061,
# 6977,
# 77000,
# 9113,
# 43815
# ]
# matching_files = getData(root_path="./", keywords=search_ids)
# print(matching_files)

# BASE_OUTPUT_PATH = Path("C:\\Users\\plamendimitrov\\Desktop\\C-SUB H248 Main  + Engine CCBs\\data")


# batch_dir = BASE_OUTPUT_PATH
# batch_dir.mkdir(parents=True, exist_ok=True)

# if matching_files:
#                     # Create drawings subdirectory
#     drawings_dir = batch_dir / "text_files"
#     drawings_dir.mkdir(exist_ok=True)
                    
#     for drawing_file in matching_files:
#         src_path = Path(drawing_file)
#         dst_path = drawings_dir / src_path.name
#         shutil.copy2(src_path, dst_path)
                    
                    
import json

json_string = """{
    "1": {
        "1.1": {"1.2": "value1.2"},
        "1.3": "value1.3"
    },
    "2": {"2.1": "value2.1", "2.2": "value2.2"},
    "3": {"3.1": "value3.1", "3.2": "value3.2"}
}"""
# print(type(json_string))
real_json = json.loads(json_string)
# print(type(real_json)) if isinstance(real_json, dict) else print("Not a dictionary")

def iteration(data):
    for key, value in data.items():
        
        if isinstance(value, dict):
            iteration(value)
            print(f"{key}: {value}")

for key, value in real_json.items():
    if isinstance(value, dict):
        iteration(value)
