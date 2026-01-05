import sqlite3

DB_NAME = "aadhaar.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """
    Create documents table if it doesn't exist.
    Includes filename, blur status, name, DOB, Aadhaar number.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        is_blur INTEGER,
        name TEXT,
        dob TEXT,
        aadhaar TEXT
    )
    """)

    conn.commit()
    conn.close()
