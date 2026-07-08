import os
import sys
import pyodbc
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """Establishes and returns a connection to the MS SQL Docker container."""
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    uid = os.getenv("DB_UID")
    pwd = os.getenv("DB_PWD")

    # Validate that all environment variables are present
    if not all([server, database, uid, pwd]):
        print("❌ Error: Missing database configuration in .env file.")
        sys.exit(1)

    # Build ODBC connection string
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={uid};"
        f"PWD={pwd};"
        f"Encrypt=no;"
        f"TrustServerCertificate=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except pyodbc.Error as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)