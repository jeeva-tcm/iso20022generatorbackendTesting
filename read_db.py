import sqlite3
def get_latest():
    conn = sqlite3.connect('iso_validator.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT original_message FROM validation_history ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        if row:
            with open('latest.xml', 'w', encoding='utf-8') as f:
                f.write(row[0])
    except Exception as e:
        print("Error getting record:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    get_latest()
