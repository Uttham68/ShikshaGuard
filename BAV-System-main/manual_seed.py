import bcrypt
import sqlite3
import os

db_path = "shikshasgaurd.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

admin_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
school_hash = bcrypt.hashpw(b"school123", bcrypt.gensalt()).decode('utf-8')

try:
    c.execute("INSERT INTO users (username, hashed_password, full_name, role, is_active) VALUES ('admin', ?, 'System Administrator', 'admin', 1)", (admin_hash,))
    c.execute("INSERT INTO users (username, hashed_password, full_name, role, school_pseudocode, is_active) VALUES ('principal1', ?, 'Dr. Pranav Kumar', 'principal', '1003076', 1)", (school_hash,))
    conn.commit()
    print("Users seeded successfully.")
except sqlite3.IntegrityError:
    print("Users might already exist.")
finally:
    conn.close()
