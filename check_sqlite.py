
import sqlite3
import os

db_path = "iso_validator.db"

if not os.path.exists(db_path):
    print("DB not found!")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        # Check validation_history count
        cursor.execute("SELECT count(*) FROM validation_history")
        count = cursor.fetchone()[0]
        print(f"Total history records: {count}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
