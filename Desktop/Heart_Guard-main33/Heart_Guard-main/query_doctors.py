import MySQLdb

try:
    # Connect to MySQL database
    conn = MySQLdb.connect(
        host='localhost',
        user='root',
        passwd='root',
        db='ECGproject'
    )
    
    print("✓ Connected to MySQL database 'ECGproject'")
    print("-" * 60)
    
    # Create cursor
    cursor = conn.cursor()
    
    # Query all doctors
    query = "SELECT id, username, email FROM users WHERE role='doctor'"
    cursor.execute(query)
    
    # Fetch all results
    doctors = cursor.fetchall()
    
    # Display results
    print(f"{'ID':<5} {'Username':<20} {'Email':<35}")
    print("-" * 60)
    
    for doctor in doctors:
        doctor_id, username, email = doctor
        print(f"{doctor_id:<5} {username:<20} {email:<35}")
    
    # Count total doctors
    total_doctors = len(doctors)
    print("-" * 60)
    print(f"Total Doctors: {total_doctors}")
    
    # Close connections
    cursor.close()
    conn.close()
    print("\n✓ Database connection closed")
    
except MySQLdb.Error as e:
    print(f"✗ MySQL Error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
