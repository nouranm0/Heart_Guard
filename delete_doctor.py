import mysql.connector
import requests
import json

# Step 1: Connect to MySQL database
print("=" * 60)
print("STEP 1: Connect to MySQL database")
print("=" * 60)

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ECGproject"
    )
    cursor = connection.cursor()
    print("✓ Connected to MySQL database successfully")
except Exception as e:
    print(f"✗ Failed to connect to database: {e}")
    exit(1)

# Step 2: Check all doctors in the database with their IDs
print("\n" + "=" * 60)
print("STEP 2: Check all doctors in the database")
print("=" * 60)

try:
    cursor.execute("SELECT id, name, email FROM doctors")
    doctors_before = cursor.fetchall()
    print(f"✓ Found {len(doctors_before)} doctors:")
    for doctor in doctors_before:
        print(f"  ID: {doctor[0]}, Name: {doctor[1]}, Email: {doctor[2]}")
except Exception as e:
    print(f"✗ Failed to query doctors: {e}")
    exit(1)

# Step 3: Start session and login to Flask app
print("\n" + "=" * 60)
print("STEP 3: Login to Flask app with admin credentials")
print("=" * 60)

session = requests.Session()
login_url = "http://localhost:3000/login"
login_data = {
    "email": "admin@example.com",
    "password": "admin123"
}

try:
    response = session.post(login_url, data=login_data)
    if response.status_code == 200:
        print(f"✓ Login successful (HTTP {response.status_code})")
    else:
        print(f"✗ Login failed (HTTP {response.status_code})")
        print(f"  Response: {response.text}")
except Exception as e:
    print(f"✗ Failed to login: {e}")
    exit(1)

# Step 4: Make a DELETE request to /api/doctor/4
print("\n" + "=" * 60)
print("STEP 4: Delete doctor with ID 4")
print("=" * 60)

delete_url = "http://localhost:3000/api/doctor/4"
try:
    response = session.delete(delete_url)
    print(f"✓ DELETE request sent to {delete_url}")
    print(f"  Response HTTP Status: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✓ HTTP 200 received (success)")
        print(f"  Response body: {response.text}")
    else:
        print(f"  ✗ Expected HTTP 200, got {response.status_code}")
        print(f"  Response body: {response.text}")
except Exception as e:
    print(f"✗ Failed to send DELETE request: {e}")
    exit(1)

# Step 5: Check database again to confirm doctor 4 is deleted
print("\n" + "=" * 60)
print("STEP 5: Verify doctor 4 is deleted from database")
print("=" * 60)

try:
    cursor.execute("SELECT id, name, email FROM doctors WHERE id = 4")
    result = cursor.fetchone()
    if result is None:
        print("✓ Doctor with ID 4 has been deleted from the database")
    else:
        print(f"✗ Doctor with ID 4 still exists: {result}")
except Exception as e:
    print(f"✗ Failed to query database: {e}")
    exit(1)

# Step 6: Show all remaining doctors
print("\n" + "=" * 60)
print("STEP 6: Show all remaining doctors in database")
print("=" * 60)

try:
    cursor.execute("SELECT id, name, email FROM doctors")
    doctors_after = cursor.fetchall()
    print(f"✓ Found {len(doctors_after)} doctors remaining:")
    for doctor in doctors_after:
        print(f"  ID: {doctor[0]}, Name: {doctor[1]}, Email: {doctor[2]}")
    
    print(f"\n✓ Summary: {len(doctors_before)} doctors before → {len(doctors_after)} doctors after")
    print(f"✓ Deletion successful: {len(doctors_before) - len(doctors_after)} doctor(s) deleted")
except Exception as e:
    print(f"✗ Failed to query doctors: {e}")
    exit(1)

# Close database connection
cursor.close()
connection.close()
print("\n" + "=" * 60)
print("✓ Database connection closed")
print("=" * 60)
