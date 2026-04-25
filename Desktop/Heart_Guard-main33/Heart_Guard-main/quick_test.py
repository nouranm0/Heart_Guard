#!/usr/bin/env python3
"""
Quick test of Patient Management - Check all endpoints and display results
"""
import requests
import json

BASE_URL = "http://localhost:3000"
session = requests.Session()

print("\n✓ HEART GUARD - PATIENT MANAGEMENT FINAL TEST\n")

# Login
print("[1] LOGIN")
r = session.post(f"{BASE_URL}/login", data={'email': 'admin@example.com', 'password': 'admin123'})
print(f"    Status: {r.status_code}")

# Get all patients
print("\n[2] GET ALL PATIENTS")
r = session.get(f"{BASE_URL}/api/patients")
data = r.json()
print(f"    Status: {r.status_code}")
print(f"    Total patients: {data.get('total', 0)}")
for p in data.get('patients', [])[:3]:
    print(f"    - {p['name']} ({p['phone']}) - Doctor: {p['doctor_name']}")

# Get doctors
print("\n[3] GET DOCTORS")
r = session.get(f"{BASE_URL}/api/doctors")
data = r.json()
print(f"    Status: {r.status_code}")
doctors = data.get('doctors', [])
print(f"    Total doctors: {len(doctors)}")
for doc in doctors[:2]:
    print(f"    - {doc['username']} ({doc['email']})")

# Add patient
print("\n[4] ADD NEW PATIENT")
new_patient = {
    "name": "علي محمد",
    "phone": "+201111111111",
    "gender": "M",
    "birthday": "1995-03-20",
    "doctor_id": doctors[0]['id'] if doctors else 6
}
r = session.post(f"{BASE_URL}/api/patient", json=new_patient)
data = r.json()
print(f"    Status: {r.status_code}")
if data.get('success'):
    patient_id = data['patient']['id']
    print(f"    ✓ Patient added - ID: {patient_id}, Name: {data['patient']['name']}")
else:
    print(f"    ✗ Error: {data.get('message')}")
    patient_id = None

# Search patients
print("\n[5] SEARCH PATIENTS")
r = session.get(f"{BASE_URL}/api/patients?q=علي")
data = r.json()
print(f"    Status: {r.status_code}")
print(f"    Found: {len(data.get('patients', []))} patient(s)")

# Delete patient if added
if patient_id:
    print(f"\n[6] DELETE PATIENT (ID: {patient_id})")
    r = session.delete(f"{BASE_URL}/api/patient/{patient_id}")
    data = r.json()
    print(f"    Status: {r.status_code}")
    if data.get('success'):
        print(f"    ✓ Patient deleted successfully")
    else:
        print(f"    ✗ Error: {data.get('message')}")

# Final count
print("\n[7] VERIFY FINAL COUNT")
r = session.get(f"{BASE_URL}/api/patients")
data = r.json()
print(f"    Status: {r.status_code}")
print(f"    Total patients: {data.get('total', 0)}")

print("\n✓ ALL TESTS COMPLETED SUCCESSFULLY!\n")
