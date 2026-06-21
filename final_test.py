import requests
s = requests.Session()
print("Testing Patient Management...")
r = s.post('http://localhost:3000/login', data={'email': 'admin@example.com', 'password': 'admin123'})
print(f"[1] Login: {r.status_code}")
r = s.get('http://localhost:3000/api/patients')
total = r.json().get('total')
print(f"[2] Get Patients: {r.status_code} - Total: {total}")
p = {'name': 'Test Patient', 'phone': '+20123', 'gender': 'M', 'doctor_id': 6}
r = s.post('http://localhost:3000/api/patient', json=p)
success = r.json().get('success')
print(f"[3] Add Patient: {r.status_code} - Success: {success}")
if success:
    pid = r.json()['patient']['id']
    print(f"    Patient ID: {pid}")
    r = s.delete(f'http://localhost:3000/api/patient/{pid}')
    print(f"[4] Delete Patient: {r.status_code} - Success: {r.json().get('success')}")
r = s.get('http://localhost:3000/api/patients')
total_after = r.json().get('total')
print(f"[5] Verify: Total after delete: {total_after} (was {total})")
print("✓ All tests completed!")
