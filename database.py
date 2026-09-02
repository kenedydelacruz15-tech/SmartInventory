import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="smart_inventory_pool",
    pool_size=10,
    pool_reset_session=True,
    host=os.getenv("DB_HOST"),        
    user=os.getenv("DB_USER"),        
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")     
)

def get_db_connection():
    """
    Fetches an active database connection directly from the connection pool.
    """
    return db_pool.get_connection()
