import random
import time
import hashlib
from datetime import datetime, timedelta
from faker import Faker
from db_connection import get_db_connection

fake = Faker()

# Configuration
NUM_ORDERS = 1000000
BATCH_SIZE = 25000  
TOTAL_CUSTOMERS = 500000
TOTAL_PRODUCTS = 5000

print("🔌 Connecting to Dockerized MS SQL Server...")
conn = get_db_connection()
cursor = conn.cursor()
cursor.fast_executemany = True

print("扫 Provisioning clean schemas...")
cursor.execute("""
IF OBJECT_ID('orders', 'U') IS NOT NULL DROP TABLE orders;
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY, 
    customer_id VARCHAR(50) NOT NULL, 
    order_number VARCHAR(100) NULL,
    order_date VARCHAR(50) NULL, 
    required_date VARCHAR(50) NULL, 
    shipped_date VARCHAR(50) NULL,
    status VARCHAR(50) NULL, 
    total_amount VARCHAR(50) NULL,
    tax_amount VARCHAR(50) NULL,
    shipping_fee VARCHAR(50) NULL, 
    payment_method VARCHAR(50) NULL, 
    shipping_provider VARCHAR(50) NULL,
    tracking_number VARCHAR(100) NULL, 
    source_channel VARCHAR(50) NULL,
    notes VARCHAR(MAX) NULL
);

IF OBJECT_ID('order_items', 'U') IS NOT NULL DROP TABLE order_items;
CREATE TABLE order_items (
    order_item_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity VARCHAR(50) NULL,
    unit_price VARCHAR(50) NULL,
    discount_applied VARCHAR(50) NULL
);
""")
conn.commit()

def gen_customer_fk(num):
    h = hashlib.md5(str(num).encode()).hexdigest()[:4].upper()
    return f"CUST-{str(num).zfill(6)}-{h}"

def gen_order_pk(num):
    h = hashlib.md5(f"ORD-{num}".encode()).hexdigest()[:4].upper()
    return f"ORD-{str(num).zfill(7)}-{h}"

def gen_product_fk(num):
    h = hashlib.md5(f"PROD-{num}".encode()).hexdigest()[:4].upper()
    return f"PROD-{str(num).zfill(5)}-{h}"

def gen_item_pk(order_num, line_idx):
    h = hashlib.md5(f"ITEM-{order_num}-{line_idx}".encode()).hexdigest()[:4].upper()
    return f"LINE-{str(order_num).zfill(7)}-{line_idx}-{h}"

insert_order_query = "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
insert_item_query = "INSERT INTO order_items VALUES (?,?,?,?,?,?)"

order_batch = []
item_batch = []
total_items = 0

print(f"🚀 Ingesting {NUM_ORDERS} clean structural orders...")
start_time = time.time()

for i in range(1, NUM_ORDERS + 1):
    order_id = gen_order_pk(i)
    
    # SEED REPLICATOR: Guarantees the invoice script selects the same customer for order i
    random.seed(f"ORDER_SEED_{i}")
    customer_num = random.randint(1, TOTAL_CUSTOMERS)
    customer_id = gen_customer_fk(customer_num)
    
    o_date = fake.date_time_between(start_date='-3y', end_date='now')
    order_date_str = o_date.strftime('%Y-%m-%d %H:%M:%S')
    required_date_str = (o_date + timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
    
    status = random.choice(['Pending', 'Processing', 'Shipped', 'Delivered'])
    shipped_date_str = (o_date + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S') if status in ['Shipped', 'Delivered'] else None
    
    num_items = random.randint(1, 3)
    subtotal = 0.0
    
    for line_idx in range(1, num_items + 1):
        total_items += 1
        product_id = gen_product_fk(random.randint(1, TOTAL_PRODUCTS))
        qty = random.randint(1, 4)
        price = round(random.uniform(15.0, 250.0), 2)
        subtotal += (price * qty)
        
        item_batch.append((gen_item_pk(i, line_idx), order_id, product_id, str(qty), str(price), "0.00"))
    
    tax = round(subtotal * 0.08, 2)
    total_amount = round(subtotal + tax, 2)
    
    order_batch.append((
        order_id, customer_id, f"PO-{i}", order_date_str, required_date_str, shipped_date_str,
        status, str(total_amount), str(tax), "0.00", "Credit Card", "UPS" if shipped_date_str else None,
        f"1Z{i}" if shipped_date_str else None, "Web", None
    ))
    
    if len(order_batch) >= BATCH_SIZE:
        cursor.executemany(insert_order_query, order_batch)
        cursor.executemany(insert_item_query, item_batch)
        conn.commit()
        print(f"✔ Flushed batch up to order {i}...")
        order_batch.clear()
        item_batch.clear()

if order_batch:
    cursor.executemany(insert_order_query, order_batch)
    cursor.executemany(insert_item_query, item_batch)
    conn.commit()

print(f"✅ Orders loaded in {round(time.time() - start_time, 2)}s.")
cursor.close()
conn.close()