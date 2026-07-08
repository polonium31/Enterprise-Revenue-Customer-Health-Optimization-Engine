-- 1. Setup Environment
USE DATABASE ECOMMERCE;
CREATE SCHEMA IF NOT EXISTS ECOMMERCE_SCHEMA;
USE SCHEMA ECOMMERCE_SCHEMA;

CREATE OR REPLACE TABLE Customers (
    customer_id STRING PRIMARY KEY,
    first_name STRING, middle_name STRING, last_name STRING, suffix STRING,
    email STRING, address STRING, zip_code STRING, country STRING,
    gender STRING, birth_date DATE, created_at TIMESTAMP, updated_at TIMESTAMP,
    is_active STRING, customer_segment STRING, lifetime_value STRING,
    preferred_language STRING, opt_in_email STRING, geography_key BIGINT,
    phone_extension STRING, alt_phone_extension STRING, phone_standard STRING,
    alt_phone_standard STRING
);

CREATE OR REPLACE TABLE Customers_Geography (
    geography_key BIGINT PRIMARY KEY,
    state STRING, city STRING
);

CREATE OR REPLACE TABLE Orders (
    order_id STRING PRIMARY KEY,
    customer_id STRING, order_number STRING, order_date TIMESTAMP,
    required_date TIMESTAMP, shipped_date TIMESTAMP, status STRING, 
    total_amount DOUBLE, tax_amount DOUBLE, shipping_fee DOUBLE, 
    payment_method STRING, shipping_provider STRING, tracking_number STRING, 
    source_channel STRING, notes STRING
);

CREATE OR REPLACE TABLE Invoices (
    invoice_number STRING PRIMARY KEY,
    invoice_id STRING, order_id STRING, customer_id STRING,
    invoice_date TIMESTAMP, due_date TIMESTAMP, paid_date TIMESTAMP,
    amount_due DOUBLE, tax_amount DOUBLE, discount_amount DOUBLE,
    late_fee_charged DOUBLE, amount_paid DOUBLE, payment_status STRING,
    payment_method STRING, credit_terms STRING, billing_currency STRING,
    fiscal_year INT, fiscal_period INT, internal_gl_code STRING,
    billing_address_id STRING, is_disputed BOOLEAN
);

CREATE OR REPLACE TABLE Order_Items (
    order_item_id STRING PRIMARY KEY,
    order_id STRING, product_id STRING, quantity INT,
    unit_price DOUBLE, discount_applied INT
);

CREATE OR REPLACE TABLE Products (
    product_id STRING PRIMARY KEY,
    sku STRING, mpn STRING, upc STRING, product_name STRING,
    brand STRING, category STRING, description STRING, cost_price DOUBLE,
    retail_price DOUBLE, stock_quantity DOUBLE, weight_lbs DOUBLE,
    dimensions_inch STRING, is_discontinued STRING, supplier_id STRING,
    created_at TIMESTAMP, updated_at TIMESTAMP, length_in DOUBLE,
    width_in DOUBLE, height_in DOUBLE
);

-- 3. Apply Foreign Key Relationships
ALTER TABLE Orders ADD FOREIGN KEY (customer_id) REFERENCES Customers(customer_id);
ALTER TABLE Order_Items ADD FOREIGN KEY (order_id) REFERENCES Orders(order_id);
ALTER TABLE Order_Items ADD FOREIGN KEY (product_id) REFERENCES Products(product_id);
ALTER TABLE Invoices ADD FOREIGN KEY (order_id) REFERENCES Orders(order_id);
ALTER TABLE Customers ADD FOREIGN KEY (geography_key) REFERENCES Customers_Geography(geography_key);