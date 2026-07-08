# Import python packages
import streamlit as st
import os
from datetime import datetime

# 1. Page Config & Title
st.set_page_config(
    page_title="E-Commerce Enterprise Executive Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Enterprise Performance Executive Dashboard")
st.markdown("---")

# 2. Native Snowflake Connection
conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL", 600))
session = conn.session()

def run_query(query_string):
    return session.sql(query_string).to_pandas()

# 3. Sidebar Filters (Dynamic & Defaults to Current Year)
st.sidebar.header("🗓️ Global Filters")

current_year = datetime.now().year

try:
    year_df = run_query("SELECT DISTINCT year FROM ECOMMERCE.ECOMMERCE_DN_SCHEMA.Date_Table ORDER BY year DESC;")
    year_list = year_df['YEAR'].tolist() if not year_df.empty else [current_year]
except Exception:
    year_list = [current_year]

# Set the default selection index to match the current year if it exists in your list
default_index = year_list.index(current_year) if current_year in year_list else 0

# Horizontal radio buttons inside the sidebar
selected_year = st.sidebar.radio(
    "Select Reporting Fiscal Year",
    options=year_list,
    index=default_index,
    horizontal=True
)

# 4. Pull Aggregated Metrics via Dynamic Tables
rev_query = f"""
    SELECT 
        LPAD(TO_VARCHAR(d.MONTH_NUMBER), 2, '0') || '-' || SUBSTR(d.MONTH_NAME, 1, 3) AS "Month", 
        dt.SOURCE_CHANNEL AS "Sales Channel", 
        SUM(dt.TOTAL_NET_REVENUE) AS "Net Revenue ($)",
        SUM(dt.TOTAL_ORDERS) AS "Total Orders"
    FROM ECOMMERCE.ECOMMERCE_DN_SCHEMA.DT_REVENUE_GROWTH_TRACKER dt
    JOIN ECOMMERCE.ECOMMERCE_DN_SCHEMA.Date_Table d 
      ON TO_VARCHAR(dt.ORDER_DATE_KEY) = TO_VARCHAR(d.DATE_KEY)
    WHERE d.YEAR = {selected_year}
    GROUP BY d.MONTH_NUMBER, d.MONTH_NAME, dt.SOURCE_CHANNEL
    ORDER BY d.MONTH_NUMBER;
"""
df_rev = run_query(rev_query)

risk_query = f"""
    SELECT 
        dt.PAYMENT_STATUS AS "Payment Status",
        SUM(dt.NET_REVENUE_AT_RISK) AS "Accounts Receivable At Risk ($)",
        SUM(dt.TOTAL_LATE_FEES_LEVIED) AS "Late Fees Levied ($)"
    FROM ECOMMERCE.ECOMMERCE_DN_SCHEMA.DT_FINANCIAL_RISK_AUDIT dt
    JOIN ECOMMERCE.ECOMMERCE_DN_SCHEMA.Date_Table d 
      ON TO_VARCHAR(dt.INVOICE_DATE_KEY) = TO_VARCHAR(d.DATE_KEY)
    WHERE d.YEAR = {selected_year}
    GROUP BY dt.PAYMENT_STATUS;
"""
df_risk = run_query(risk_query)

# 5. Top-Level Summary KPI Cards (Industry Standard Naming)
if not df_rev.empty:
    total_net_rev = df_rev["Net Revenue ($)"].sum()
    total_orders = df_rev["Total Orders"].sum()
    aov = total_net_rev / total_orders if total_orders > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Net Revenue", f"${total_net_rev:,.2f}")
    col2.metric("📦 Gross Order Volume (GOV)", f"{total_orders:,}")
    col3.metric("💳 Average Order Value (AOV)", f"${aov:,.2f}")
st.markdown("---")

# 6. Presentation Tabs
tab1, tab2, tab3 = st.tabs(["📈 Channel Revenue Performance", "⚡ Product Velocity & Volume", "⚠️ Credit & Collection Risk"])

with tab1:
    st.subheader("Monthly Net Revenue Breakdown by Sales Channel")
    if not df_rev.empty:
        # Native line chart utilizing standard corporate naming layout
        st.line_chart(
            data=df_rev, 
            x="Month", 
            y="Net Revenue ($)", 
            color="Sales Channel"
        )
    else:
        st.warning("No sales transactions mapped to this timeline parameter.")

with tab2:
    st.subheader("Top 10 High-Velocity Product Categories")
    velocity_query = f"""
        SELECT 
            p.CATEGORY AS "Product Category", 
            SUM(dt.TOTAL_UNITS_SOLD) AS "Units Sold"
        FROM ECOMMERCE.ECOMMERCE_DN_SCHEMA.DT_PRODUCT_VELOCITY dt
        JOIN ECOMMERCE.ECOMMERCE_DN_SCHEMA.PRODUCTS p ON dt.PRODUCT_KEY = p.PRODUCT_KEY
        JOIN ECOMMERCE.ECOMMERCE_DN_SCHEMA.Date_Table d ON TO_VARCHAR(dt.ORDER_DATE_KEY) = TO_VARCHAR(d.DATE_KEY)
        WHERE d.YEAR = {selected_year}
        GROUP BY p.CATEGORY
        ORDER BY "Units Sold" DESC
        LIMIT 10;
    """
    df_vel = run_query(velocity_query)
    
    if not df_vel.empty:
        st.bar_chart(
            data=df_vel, 
            x="Product Category", 
            y="Units Sold"
        )
    else:
        st.warning("No product movement tracking matches this query filter.")

with tab3:
    st.subheader("Accounts Receivable Aging & Risk Aggregation")
    if not df_risk.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.bar_chart(
                data=df_risk, 
                x="Payment Status", 
                y="Accounts Receivable At Risk ($)"
            )
        with c2:
            total_late_fees = df_risk["Late Fees Levied ($)"].sum()
            st.info(f"💵 **Total Secondary Penalties Invoiced:**\n\n${total_late_fees:,.2f}")
    else:
        st.warning("No outstanding risk indicators logged for this annual parameter.")