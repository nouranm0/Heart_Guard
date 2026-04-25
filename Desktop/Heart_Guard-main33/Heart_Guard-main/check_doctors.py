#!/usr/bin/env python3
import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='root', database='ECGproject')
cursor = conn.cursor()
cursor.execute('SELECT id, username, email, role FROM users WHERE role="doctor"')
docs = cursor.fetchall()
print('Doctors remaining:')
for d in docs:
    print(f'  - ID: {d[0]}, Name: {d[1]}, Email: {d[2]}')
cursor.close()
conn.close()
