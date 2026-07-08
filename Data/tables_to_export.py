import json
import os
import re

# Current directory where the script resides
current_dir = os.path.dirname(os.path.abspath(__file__))

def natural_sort_key(s):
    """
    Splits string into a list of integers and text to enable natural sorting.
    e.g., 'file_10.csv' becomes ['file_', 10, '.csv']
    """
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split('([0-9]+)', s)]

def generate_index(folders_to_index, output_filename="index.json"):
    index_data = []
    
    for folder_name in folders_to_index:
        folder_path = os.path.join(current_dir, folder_name)
        
        if os.path.exists(folder_path):
            # 1. Get all CSV files
            files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]
            
            # 2. Sort them using the natural sort key
            files.sort(key=natural_sort_key)
            
            for file in files:
                entry = {
                    "p_rel_url": f"{folder_name}/{file}",
                    "p_sink_folder": folder_name,
                    "p_sink_file": f"{file}"
                }
                index_data.append(entry)
    
    # Save the index file
    output_path = os.path.join(current_dir, output_filename)
    with open(output_path, "w") as f:
        json.dump(index_data, f, indent=2)
    
    print(f"[+] Index generated at: {output_path}")

if __name__ == "__main__":
    # Specify the folders to scan
    folders = ["Customers", "Invoices", "Orders", "Order_Items", "Products"]
    
    generate_index(folders)
    print("\n[!] Indexing complete with natural sorting applied.")