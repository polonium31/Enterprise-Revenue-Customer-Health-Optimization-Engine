-- 1. Connect orders to customers (N:1)
ALTER TABLE orders
ADD CONSTRAINT FK_orders_customers 
FOREIGN KEY (customer_id) REFERENCES customers(customer_id);

-- 2. Connect order_items to orders (N:1 with Cascade Delete or Standard protection)
ALTER TABLE order_items
ADD CONSTRAINT FK_order_items_orders 
FOREIGN KEY (order_id) REFERENCES orders(order_id);

-- 3. Connect order_items to products (N:1) - ADDED
ALTER TABLE order_items
ADD CONSTRAINT FK_order_items_products 
FOREIGN KEY (product_id) REFERENCES products(product_id);

-- 4. Enforce strict 1:1 rule on invoices before linking - ADDED
-- This prevents the same order from accidentally getting multiple invoices assigned
ALTER TABLE invoice
ADD CONSTRAINT UC_invoices_order_id UNIQUE (order_id);

-- 5. Connect invoice to orders (1:1 Anchor)
ALTER TABLE invoice
ADD CONSTRAINT FK_invoices_orders 
FOREIGN KEY (order_id) REFERENCES orders(order_id);

-- 6. Connect invoices to customers (Direct Ledger Link)
ALTER TABLE invoice
ADD CONSTRAINT FK_invoices_customers 
FOREIGN KEY (customer_id) REFERENCES customers(customer_id);

SELECT 
    (SELECT COUNT(*) FROM customers) AS Total_Customers,
    (SELECT COUNT(*) FROM products) AS Total_Products,
    (SELECT COUNT(*) FROM orders) AS Total_Orders,
    (SELECT COUNT(*) FROM order_items) AS Total_Order_Items,
    (SELECT COUNT(*) FROM invoice) AS Total_Invoices;

SELECT 
    COUNT(i.invoice_id) AS Total_Evaluated_Invoices,
    SUM(CASE WHEN i.customer_id = o.customer_id THEN 1 ELSE 0 END) AS Perfectly_Matched_Customers,
    SUM(CASE WHEN i.customer_id <> o.customer_id THEN 1 ELSE 0 END) AS Mismatched_Cross_Billed_Customers
FROM invoice i
JOIN orders o ON i.order_id = o.order_id;

SELECT TOP 10
    o.order_id,
    o.total_amount AS Header_Total,
    SUM(CAST(oi.quantity AS INT) * CAST(oi.unit_price AS DECIMAL(10,2))) + CAST(o.tax_amount AS DECIMAL(10,2)) AS Calculated_Item_Total
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount, o.tax_amount;

SELECT TOP 10 * FROM customers;
SELECT TOP 10 * FROM products;
SELECT TOP 10 * FROM orders;
SELECT TOP 10 * FROM invoice;
SELECT TOP 10 * FROM order_items;

