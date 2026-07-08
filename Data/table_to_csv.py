import os
import sys
import csv
import random

# Fix Python path so it can find db_connection.py one directory level up
current_dir = os.path.dirname(os.path.abspath(__file__)) # Data folder
project_root = os.path.dirname(current_dir)              # Project root folder
if project_root not in sys.path:
    sys.path.append(project_root)

# Now we can safely import your connection logic
from db_connection import get_db_connection  

def export_table_to_bounded_csv(table_name, subfolder_name, id_column):
    """
    Fetches data from a Docker SQL table and splits it into CSV chunks 
    containing between 25,000 and 35,000 records.
    """
    # Dynamically build the target folder path: Data/<Subfolder>
    output_folder = os.path.join(current_dir, subfolder_name)
    os.makedirs(output_folder, exist_ok=True)
    
    # Connect to the Docker sandbox database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Get total row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cursor.fetchone()[0]
    
    if total_rows == 0:
        print(f"[-] Table {table_name} is empty. Skipping.")
        cursor.close()
        conn.close()
        return

    print(f"[+] Exporting {total_rows} rows from {table_name}...")
    
    offset = 0
    file_index = 1
    
    # 2. Extract and chunk sequentially
    while offset < total_rows:
        # Determine dynamic size matching your constraint
        chunk_size = random.randint(25000, 35000)
        
        # SQL Server offset-fetch pagination
        query = f"""
            SELECT * FROM {table_name}
            ORDER BY {id_column}
            OFFSET {offset} ROWS
            FETCH NEXT {chunk_size} ROWS ONLY;
        """
        cursor.execute(query)
        
        headers = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        
        if not rows:
            break
            
        # Format filename based on the table name
        clean_name = table_name.split('.')[-1]
        file_name = f"{clean_name}_chunk_{file_index}.csv"
        file_path = os.path.join(output_folder, file_name)
        
        # Write to the specific subfolder
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"    -> Saved {len(rows)} records to: {subfolder_name}/{file_name}")
        
        offset += len(rows)
        file_index += 1

    cursor.close()
    conn.close()

# --- Execution Matrix ---
if __name__ == "__main__":
    # Table maps pointing exactly to your VS Code structure
    tables_to_export = [
        {"table": "dbo.customers", "folder": "Customer", "pk": "customer_id"},
        {"table": "dbo.invoice", "folder": "Invoice", "pk": "invoice_id"},
        {"table": "dbo.orders", "folder": "Orders", "pk": "order_id"},
        {"table": "dbo.order_items", "folder": "Order Items", "pk": "order_item_id"},
        {"table": "dbo.products", "folder": "Products", "pk": "product_id"}
    ]
    
    for target in tables_to_export:
        export_table_to_bounded_csv(
            table_name=target["table"], 
            subfolder_name=target["folder"], 
            id_column=target["pk"]
        )
    print("\n[!] All database tables processed successfully.")