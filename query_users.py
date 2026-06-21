import MySQLdb

try:
    # Connect to MySQL database
    conn = MySQLdb.connect(
        host="localhost",
        user="root",
        passwd="root",
        db="ECGproject"
    )
    print("[SUCCESS] Connected to ECGproject database")
    
    cursor = conn.cursor()
    
    # 1. SELECT all users with their id, username, email, role
    print("\n" + "="*60)
    print("ALL USERS IN DATABASE:")
    print("="*60)
    cursor.execute("SELECT id, username, email, role FROM users")
    all_users = cursor.fetchall()
    print("Total users: " + str(len(all_users)))
    for user in all_users[:20]:  # Show first 20
        print("ID: " + str(user[0]) + ", User: " + str(user[1]) + ", Email: " + str(user[2]) + ", Role: " + str(user[3]))
    
    # 2. Show specifically doctors with ID 4, 6, 7
    print("\n" + "="*60)
    print("SPECIFIC DOCTORS (ID 4, 6, 7):")
    print("="*60)
    cursor.execute("SELECT id, username, email, role FROM users WHERE id IN (4, 6, 7)")
    doctors = cursor.fetchall()
    for doctor in doctors:
        user_id, username, email, role = doctor
        print("ID: " + str(user_id) + ", User: " + str(username) + ", Email: " + str(email) + ", Role: " + str(role))
    
    # 3. Check what role they have (should be 'doctor')
    print("\n" + "="*60)
    print("ROLE VALIDATION FOR IDs 4, 6, 7:")
    print("="*60)
    for doctor in doctors:
        user_id, username, email, role = doctor
        is_doctor = role == 'doctor'
        status = "CORRECT" if is_doctor else "ISSUE"
        print("ID " + str(user_id) + ": Role = '" + str(role) + "' [" + status + "]")
    
    # 4. Check for any data issues
    print("\n" + "="*60)
    print("DATA INTEGRITY CHECK:")
    print("="*60)
    
    # Check for NULL values
    cursor.execute("SELECT COUNT(*) FROM users WHERE id IS NULL OR username IS NULL OR email IS NULL OR role IS NULL")
    null_count = cursor.fetchone()[0]
    print("NULL values found: " + str(null_count))
    
    # Check for duplicate usernames
    cursor.execute("SELECT username, COUNT(*) as count FROM users GROUP BY username HAVING count > 1")
    duplicates = cursor.fetchall()
    print("Duplicate usernames: " + str(len(duplicates)))
    
    # Check for duplicate emails
    cursor.execute("SELECT email, COUNT(*) as count FROM users GROUP BY email HAVING count > 1")
    dup_emails = cursor.fetchall()
    print("Duplicate emails: " + str(len(dup_emails)))
    
    # Check all distinct roles
    cursor.execute("SELECT DISTINCT role FROM users")
    roles = cursor.fetchall()
    roles_list = [str(r[0]) for r in roles]
    print("Distinct roles: " + str(roles_list))
    
    cursor.close()
    conn.close()
    print("\n[SUCCESS] Query complete")
    
except MySQLdb.Error as e:
    print("[ERROR] MySQL Error: " + str(e))
except Exception as e:
    print("[ERROR] Exception: " + str(e))
