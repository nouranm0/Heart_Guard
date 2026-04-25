#!/usr/bin/env python3
"""
Insert admin user directly to database
"""
from werkzeug.security import generate_password_hash
import mysql.connector

# Generate password hash
password_hash = generate_password_hash('admin123')
print(f"Password hash: {password_hash}")

try:
    # Connect to MySQL
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='ECGproject'
    )
    
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT id FROM users WHERE email = %s", ('admin@example.com',))
    existing = cursor.fetchone()
    
    if existing:
        print("✅ Admin user already exists")
    else:
        # Insert admin user
        query = """
        INSERT INTO users (username, email, password_hash, role, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        
        cursor.execute(query, (
            'admin',
            'admin@example.com',
            password_hash,
            'admin',
            True
        ))
        
        conn.commit()
        print("✅ Admin user created successfully!")
        print(f"   Email: admin@example.com")
        print(f"   Password: admin123")
    
    # List all users
    cursor.execute("SELECT id, username, email, role FROM users")
    users = cursor.fetchall()
    print("\nAll users in database:")
    for user in users:
        print(f"  - ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Role: {user[3]}")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ Database error: {err}")
except Exception as e:
    print(f"❌ Error: {e}")
