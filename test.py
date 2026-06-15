import os

import socket

computer_name = socket.gethostname()
print(f"Running on computer: {computer_name}")

name = "7283600430+7283600530A"
print(len(str(name)))

if(len(str(name)) == 8):
    new_name = name[0:4] + " " + name[4:8] + " " + name[8:10]
    print(new_name)
elif(len(str(name)) == 10):
    new_name = name[0:4] + " " + name[4:8]
    print(new_name)
elif(len(str(name)) == 20 and name[10:11] == "+"): #7283 2233 60 + 7283 2233A
    new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + name[19:20]
    print(new_name) 
elif(len(str(name)) == 21 and name[10:11] == "+"): #7283 6004 30 + 7283 6005 30
    new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21]
    print(new_name)  
elif(len(str(name)) == 22 and name[10:11] == "+"): #7283 2233 60 + 7283 2233 60A
    new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21] + name[21:22]
    print(new_name)   
elif(len(str(name)) == 31 and name[10:11] == "+"): #7283 6004 30 + 7283 6005 30 + 7283 2244A
    new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21] + " " + name[21:22] + " " + name[22:26] + " " + name[26:30] + name[30:31]
    print(new_name) 
         
elif(len(str(name)) == 33 and name[10:11] == "+"): #7283 6004 30 + 7283 6005 30 + 7283 2244 60A
    new_name = name[0:4] + " " + name[4:8] + " " + name[8:10] + " " + name[10:11] + " " + name[11:15] + " " + name[15:19] + " " + name[19:21] + " " + name[21:22] + " " + name[22:26] + " " + name[26:30] + " " + name[30:33]
    print(new_name)
else:
    print(name)


# file_path = "S:/JO"

# # Use a list to store multiple job numbers
# job_order_numbers = []

# for file in os.listdir(file_path):
#     if file.endswith(".xlsm") or file.endswith(".xlsx"):
#         # os.listdir gives just the file name, so we can split it directly
#         file_name_only, file_extension = os.path.splitext(file)   
        
#         # Slice index 2 to 8 to get the JO number
#         jo = file_name_only[2:8]
#         job_order_numbers.append(jo)

# # FIX: Put the [-1] inside the print function, attached to the list name
# if job_order_numbers:
#     next_job_number = None

#     # Loop through the list BACKWARDS (starting from the last element)
#     for job in reversed(job_order_numbers):
#         # Clean up the element (convert to string just in case it's already an int)
#         job_str = str(job).strip()
        
#         # Check if this specific item is a number
#         if job_str.isdigit():
#             next_job_number = int(job_str)
#             break  # We found the last number! Exit the loop immediately.

#     # Check if we successfully found a number anywhere in the list
#     if next_job_number is not None:
#         print(f"Next job order number: {next_job_number}")
#     else:
#         print("Warning: No valid numeric job order numbers found in the entire list.")

# else:
#     print("No .xlsx or .xlsm files found.")
    
