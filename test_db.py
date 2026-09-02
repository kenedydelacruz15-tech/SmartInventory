import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cursor = db.cursor()
    
    cursor.execute("SHOW DATABASES;")
    databases = cursor.fetchall()
    
    print("\nDatabases")
    for database in databases:
        print(f" -> {database[0]}")
    
    cursor.close()
    db.close()

except Exception as e:
    print(f"Connection Error: {str(e)}")
