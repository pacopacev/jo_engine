import os


file_path = "S:/JO"

# Use a list to store multiple job numbers
job_order_numbers = []

for file in os.listdir(file_path):
    if file.endswith(".xlsm") or file.endswith(".xlsx"):
        # os.listdir gives just the file name, so we can split it directly
        file_name_only, file_extension = os.path.splitext(file)   
        
        # Slice index 2 to 8 to get the JO number
        jo = file_name_only[2:8]
        job_order_numbers.append(jo)

# FIX: Put the [-1] inside the print function, attached to the list name
if job_order_numbers:
    next_job_number = None

    # Loop through the list BACKWARDS (starting from the last element)
    for job in reversed(job_order_numbers):
        # Clean up the element (convert to string just in case it's already an int)
        job_str = str(job).strip()
        
        # Check if this specific item is a number
        if job_str.isdigit():
            next_job_number = int(job_str)
            break  # We found the last number! Exit the loop immediately.

    # Check if we successfully found a number anywhere in the list
    if next_job_number is not None:
        print(f"Next job order number: {next_job_number}")
    else:
        print("Warning: No valid numeric job order numbers found in the entire list.")

else:
    print("No .xlsx or .xlsm files found.")
    
