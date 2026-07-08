import random
import time
import hashlib
from faker import Faker
from db_connection import get_db_connection

# Initialize Faker
fake = Faker()

# Configuration
NUM_RECORDS = 500000
BATCH_SIZE = 25000  

# Connect to DB
print("🔌 Connecting to Dockerized MS SQL Server...")
conn = get_db_connection()
cursor = conn.cursor()
cursor.fast_executemany = True

print("🧹 Recreating customers table with VARCHAR Primary Key...")
cursor.execute("""
IF OBJECT_ID('customers', 'U') IS NOT NULL 
    DROP TABLE customers;

CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(150) NULL,
    middle_name VARCHAR(150) NULL,
    last_name VARCHAR(150) NULL,
    suffix VARCHAR(50) NULL,
    email VARCHAR(320) NULL,
    phone VARCHAR(100) NULL,
    alternative_phone VARCHAR(100) NULL,
    address VARCHAR(300) NULL,
    city VARCHAR(150) NULL,
    state VARCHAR(50) NULL,
    zip_code VARCHAR(50) NULL,
    country VARCHAR(100) NULL,
    gender VARCHAR(10) NULL,
    birth_date VARCHAR(50) NULL,
    created_at VARCHAR(50) NULL,
    updated_at VARCHAR(50) NULL,
    is_active VARCHAR(50) NULL,
    customer_segment VARCHAR(50) NULL,
    lifetime_value VARCHAR(50) NULL,
    preferred_language VARCHAR(10) NULL,
    opt_in_email VARCHAR(50) NULL
);
""")
conn.commit()


def generate_enterprise_id(num):
    """Generates a deterministic enterprise alphanumeric ID."""
    short_hash = hashlib.md5(str(num).encode()).hexdigest()[:4].upper()
    return f"CUST-{str(num).zfill(6)}-{short_hash}"


def introduce_chaos(field_name, value):
    """85% clean data, 15% chaos logic with target constraint protections."""
    if random.random() > 0.15:
        return value

    # Your custom targeted name-chaos strategy
    if field_name in ['first_name', 'last_name', 'middle_name']:
        chaos_type = random.choice(['upper', 'lower', 'whitespace', 'null'])
        if field_name == 'first_name':
            if chaos_type == 'upper': return str(value).upper()
            if chaos_type == 'lower': return str(value).lower()
            if chaos_type == 'whitespace': return f"   {value}   "
            # Explicitly drops out here so first_name remains untouched if 'null' was chosen
        else:
            if chaos_type == 'upper': return str(value).upper()
            if chaos_type == 'lower': return str(value).lower()
            if chaos_type == 'whitespace': return f"   {value}   "
            if chaos_type == 'null': return None
        
    elif field_name == 'email':
        return random.choice([None, "corrupted_email.com", f"{value}.csv"])
        
    elif field_name in ['phone', 'alternative_phone']:
        return random.choice(["000-000-0000", "99999", None, "NOT_PROVIDED"])
        
    elif field_name == 'zip_code':
        return random.choice(["000", "99999999999", "ABCDE", " "])
        
    elif field_name in ['birth_date', 'updated_at']:
        return random.choice(["1776-07-04", "2050-01-01", "0000-00-00", None])
        
    elif field_name in ['is_active', 'opt_in_email']:
        return random.choice(["Y", "N", "1", "0", "TRUE", "FALSE"])

    elif field_name == 'lifetime_value':
        return random.choice([-150.75, "NaN", "1,450.00$", None])

    return value


print(f"🚀 Starting direct ingestion of {NUM_RECORDS} alphanumeric enterprise records...")
start_time = time.time()

insert_query = """
INSERT INTO customers (
    customer_id, first_name, middle_name, last_name, suffix, 
    email, phone, alternative_phone, address, city, 
    state, zip_code, country, gender, birth_date, 
    created_at, updated_at, is_active, customer_segment, lifetime_value, 
    preferred_language, opt_in_email
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

batch = []

for i in range(1, NUM_RECORDS + 1):
    customer_id = generate_enterprise_id(i)
    
    gender_pick = random.choice(['M', 'F', 'O', 'U'])
    f_name = fake.first_name_male() if gender_pick == 'M' else fake.first_name_female() if gender_pick == 'F' else fake.first_name()
    m_name = fake.first_name() if random.random() > 0.3 else None
    l_name = fake.last_name()
    suffix = random.choice(["Jr.", "Sr.", "III", None]) if random.random() > 0.9 else None
    
    email = fake.ascii_free_email()
    phone = fake.phone_number()
    alt_phone = fake.phone_number() if random.random() > 0.7 else None
    
    address = fake.street_address().replace("\n", ", ")
    city = fake.city()
    state = fake.state_abbr()
    zip_code = fake.zipcode()
    country = "USA"
    
    birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%Y-%m-%d')
    c_at = fake.date_time_between(start_date='-5y', end_date='-1y')
    created_at = c_at.strftime('%Y-%m-%d %H:%M:%S')
    updated_at = fake.date_time_between(start_date=c_at, end_date='now').strftime('%Y-%m-%d %H:%M:%S')
    
    is_active = random.choice([True, False])
    segment = random.choice(["VIP", "Regular", "Churn-Risk", "New"])
    ltv = round(random.uniform(0.0, 10000.0), 2)
    lang = random.choice(["EN", "ES", "FR", "ZH"])
    opt_in = random.choice([True, False])
    
    row_tuple = (
        customer_id,
        introduce_chaos('first_name', f_name),
        introduce_chaos('middle_name', m_name),
        introduce_chaos('last_name', l_name),
        suffix,
        introduce_chaos('email', email),
        introduce_chaos('phone', phone),
        introduce_chaos('alternative_phone', alt_phone),
        address,
        city,
        state,
        introduce_chaos('zip_code', zip_code),
        country,
        gender_pick,
        introduce_chaos('birth_date', birth_date),
        created_at,
        introduce_chaos('updated_at', updated_at),
        introduce_chaos('is_active', is_active),
        segment,
        introduce_chaos('lifetime_value', ltv),
        lang,
        introduce_chaos('opt_in_email', opt_in)
    )
    
    batch.append(row_tuple)
    
    if len(batch) == BATCH_SIZE:
        cursor.executemany(insert_query, batch)
        conn.commit()
        batch.clear()
        print(f"✔ Flushed batch up to row {i}...")

if batch:
    cursor.executemany(insert_query, batch)
    conn.commit()

end_time = time.time()
print(f"✅ Ingestion complete! 500,000 records updated into MS SQL Docker in {round(end_time - start_time, 2)} seconds.")

cursor.close()
conn.close()