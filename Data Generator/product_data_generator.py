import random
import time
import hashlib
from datetime import datetime, timedelta
from faker import Faker
from db_connection import get_db_connection

# Initialize Faker
fake = Faker()

# Configuration
NUM_RECORDS = 50000
BATCH_SIZE = 10000  

print("🔌 Connecting to Dockerized MS SQL Server...")
conn = get_db_connection()
cursor = conn.cursor()
cursor.fast_executemany = True

print("🧹 Recreating enhanced products table...")
cursor.execute("""
IF OBJECT_ID('products', 'U') IS NOT NULL 
    DROP TABLE products;

CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    sku VARCHAR(100) NOT NULL UNIQUE,
    mpn VARCHAR(100) NULL,
    upc VARCHAR(20) NULL,
    product_name VARCHAR(255) NULL,
    brand VARCHAR(100) NULL,
    category VARCHAR(100) NULL,
    description VARCHAR(MAX) NULL,
    cost_price VARCHAR(50) NULL,
    retail_price VARCHAR(50) NULL,
    stock_quantity VARCHAR(50) NULL,
    weight_lbs VARCHAR(50) NULL,
    dimensions_inch VARCHAR(100) NULL,
    is_discontinued VARCHAR(50) NULL,
    supplier_id VARCHAR(50) NULL,
    created_at VARCHAR(50) NULL,
    updated_at VARCHAR(50) NULL
);
""")
conn.commit()


def generate_product_pk(num):
    """Generates a deterministic enterprise alphanumeric Product ID."""
    short_hash = hashlib.md5(f"PROD-{num}".encode()).hexdigest()[:4].upper()
    return f"PROD-{str(num).zfill(5)}-{short_hash}"


def introduce_product_chaos(field_name, value, cost_price_ref=None):
    """Introduces operational and logistical corruption into 15% of fields."""
    if random.random() > 0.15:
        return value

    # Chaos Engine Mechanics
    if field_name == 'cost_price':
        return random.choice([-10.00, "NaN", "0.00", None])
        
    elif field_name == 'retail_price':
        if cost_price_ref and isinstance(cost_price_ref, (int, float)):
            return round(cost_price_ref * 0.5, 2) # Sells at a loss paradox
        return "PRICE_ERROR"
        
    elif field_name == 'stock_quantity':
        return random.choice(["-5", "OUT_OF_STOCK", "999999", None])
        
    elif field_name == 'upc':
        # Simulates dropping leading zeros or total barcode failure
        return random.choice(["883929", "000000000000", "CORRUPTED", None])
        
    elif field_name == 'weight_lbs':
        return f"{value} lbs"  # Appends unit characters to break pure decimal conversions
        
    elif field_name == 'dimensions_inch':
        return random.choice(["⚠️ INVALID", "0x0x0", None])
        
    elif field_name == 'is_discontinued':
        return random.choice(["Y", "N", "1", "0", "TRUE", "FALSE", "ARCHIVED"])

    elif field_name == 'supplier_id':
        return random.choice(["SUPP-UNKNOWN", "NULL", "", None])

    return value


print(f"🚀 Starting direct ingestion of {NUM_RECORDS} expanded master product records...")
start_time = time.time()

insert_query = """
INSERT INTO products (
    product_id, sku, mpn, upc, product_name, brand, category, description,
    cost_price, retail_price, stock_quantity, weight_lbs, dimensions_inch,
    is_discontinued, supplier_id, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

categories = ['Electronics', 'Apparel', 'Home & Kitchen', 'Automotive', 'Beauty', 'Sports', 'Books']
brands = ['LogiTech', 'Nike', 'Samsung', 'Sony', 'Apple', 'Dell', 'HP', 'Adidas', 'Anker']

batch = []

for i in range(1, NUM_RECORDS + 1):
    product_id = generate_product_pk(i)
    category = random.choice(categories)
    brand = random.choice(brands)
    
    hash_seed = hashlib.md5(f"PROD-SKU-{i}".encode()).hexdigest().upper()
    sku = f"{category[:4].upper()}-{brand[:4].upper()}-{hash_seed[:10]}-{i}"
    mpn = f"MPN-{hash_seed[6:12]}-{brand[:2].upper()}"
    upc = "".join([str(random.randint(0, 9)) for _ in range(12)]) # Standard 12 digit format
    
    product_name = f"{brand} {fake.catch_phrase()}"
    description = f"<p>{fake.paragraph(nb_sentences=3)}</p>" if random.random() > 0.5 else fake.paragraph(nb_sentences=2)
    
    # Financials
    cost_price = round(random.uniform(3.0, 750.0), 2)
    retail_price = round(cost_price * random.uniform(1.3, 2.5), 2)
    stock_quantity = random.randint(0, 2500)
    
    # Logistics
    weight = round(random.uniform(0.5, 45.0), 2)
    dimensions = f"{random.randint(5,24)}x{random.randint(5,24)}x{random.randint(2,12)}"
    
    # Structural details
    is_discontinued = random.choice([True, False])
    supplier_id = f"SUPP-{str(random.randint(1, 150)).zfill(4)}"
    
    # Time Matrices
    c_date = fake.date_time_between(start_date='-5y', end_date='-2y')
    created_at = c_date.strftime('%Y-%m-%d %H:%M:%S')
    updated_at = fake.date_time_between(start_date=c_date, end_date='now').strftime('%Y-%m-%d %H:%M:%S')
    
    row_tuple = (
        product_id,
        sku,
        mpn,
        introduce_product_chaos('upc', upc),
        product_name,
        brand,
        category,
        description,
        introduce_product_chaos('cost_price', cost_price),
        introduce_product_chaos('retail_price', retail_price, cost_price_ref=cost_price),
        introduce_product_chaos('stock_quantity', stock_quantity),
        introduce_product_chaos('weight_lbs', weight),
        introduce_product_chaos('dimensions_inch', dimensions),
        introduce_product_chaos('is_discontinued', is_discontinued),
        introduce_product_chaos('supplier_id', supplier_id),
        created_at,
        updated_at
    )
    
    batch.append(row_tuple)
    
    if len(batch) == BATCH_SIZE:
        cursor.executemany(insert_query, batch)
        conn.commit()
        batch.clear()
        print(f"✔ Flushed batch up to product {i}...")

if batch:
    cursor.executemany(insert_query, batch)
    conn.commit()

end_time = time.time()
print(f"✅ Success! Injected {NUM_RECORDS} highly complex products into MS SQL Docker in {round(end_time - start_time, 2)} seconds.")

cursor.close()
conn.close()