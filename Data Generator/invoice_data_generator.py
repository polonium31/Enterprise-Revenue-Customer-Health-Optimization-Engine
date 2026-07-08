import random
import time
import hashlib
from datetime import datetime, timedelta
from faker import Faker
from db_connection import get_db_connection

fake = Faker()

# Configuration
NUM_INVOICES = 1000000
BATCH_SIZE = 25000  
TOTAL_CUSTOMERS = 500000  

print("🔌 Connecting to Dockerized MS SQL Server...")
conn = get_db_connection()
cursor = conn.cursor()
cursor.fast_executemany = True

print("扫 Recreating clean invoices table...")
cursor.execute("""
IF OBJECT_ID('invoices', 'U') IS NOT NULL DROP TABLE invoices;
CREATE TABLE invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    invoice_number VARCHAR(100) NULL,
    invoice_date VARCHAR(50) NULL,
    due_date VARCHAR(50) NULL,
    paid_date VARCHAR(50) NULL,
    amount_due VARCHAR(50) NULL,
    tax_amount VARCHAR(50) NULL,
    discount_amount VARCHAR(50) NULL,
    late_fee_charged VARCHAR(50) NULL,
    amount_paid VARCHAR(50) NULL,
    payment_status VARCHAR(50) NULL,
    payment_method VARCHAR(50) NULL,
    credit_terms VARCHAR(50) NULL,
    billing_currency VARCHAR(20) NULL,
    fiscal_year VARCHAR(10) NULL,
    fiscal_period VARCHAR(10) NULL,
    internal_gl_code VARCHAR(50) NULL,
    billing_address_id VARCHAR(50) NULL,
    is_disputed VARCHAR(50) NULL
);
""")
conn.commit()

def gen_customer_fk(num):
    h = hashlib.md5(str(num).encode()).hexdigest()[:4].upper()
    return f"CUST-{str(num).zfill(6)}-{h}"

def gen_order_fk(num):
    h = hashlib.md5(f"ORD-{num}".encode()).hexdigest()[:4].upper()
    return f"ORD-{str(num).zfill(7)}-{h}"

def gen_invoice_pk(num):
    h = hashlib.md5(f"INV-{num}".encode()).hexdigest()[:4].upper()
    return f"INV-{str(num).zfill(7)}-{h}"

print(f"🚀 Ingesting {NUM_INVOICES} 1:1 customer-aligned invoices...")
start_time = time.time()

insert_query = "INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
batch = []

for i in range(1, NUM_INVOICES + 1):
    invoice_id = gen_invoice_pk(i)
    order_id = gen_order_fk(i) 
    
    # MATCHING ENGINE: Forces the randomizer to output the exact same customer number as order i
    random.seed(f"ORDER_SEED_{i}")
    customer_num = random.randint(1, TOTAL_CUSTOMERS)
    customer_id = gen_customer_fk(customer_num)
    
    # Resume normal, un-seeded timeline generation for billing details
    random.seed() 
    
    inv_date = fake.date_time_between(start_date='-2y', end_date='now')
    invoice_date_str = inv_date.strftime('%Y-%m-%d %H:%M:%S')
    due_date_str = (inv_date + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    
    status = random.choice(['Paid', 'Unpaid'])
    paid_date_str = (inv_date + timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S') if status == 'Paid' else None
    
    amount = round(random.uniform(50.0, 1500.0), 2)
    tax = round(amount * 0.08, 2)
    paid = round(amount + tax, 2) if status == 'Paid' else 0.0

    batch.append((
        invoice_id, order_id, customer_id, f"INV-2026-{i}", invoice_date_str, due_date_str, paid_date_str,
        str(amount), str(tax), "0.00", "0.00", str(paid), status, "ACH", "Net 30", "USD",
        str(inv_date.year), str(inv_date.month).zfill(2), f"GL-REV-{i}", f"ADDR-{i}", "FALSE"
    ))
    
    if len(batch) == BATCH_SIZE:
        cursor.executemany(insert_query, batch)
        conn.commit()
        batch.clear()
        print(f"✔ Flushed invoice batch up to row {i}...")

if batch:
    cursor.executemany(insert_query, batch)
    conn.commit()

print(f"✅ Invoices successfully aligned and loaded in {round(time.time() - start_time, 2)}s.")
cursor.close()
conn.close()