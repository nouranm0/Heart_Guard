#!/usr/bin/env python
"""
Debug login and check users in database
"""
import sys
sys.path.insert(0, 'c:\\Users\\AND\\Downloads\\Heart_Guard-main')

from app import create_app
from app.models import db, User

app = create_app()

with app.app_context():
    # Check all users
    print("All users in database:")
    users = User.query.all()
    for user in users:
        print(f"  - ID: {user.id}, Username: {user.username}, Email: {user.email}, Role: {user.role}")
    
    if not users:
        print("  (No users found)")
    
    # Try to find admin user
    admin_user = User.query.filter_by(email='admin@example.com').first()
    if admin_user:
        print(f"\nAdmin user found: {admin_user.username}")
        # Check password
        from werkzeug.security import check_password_hash
        password_correct = check_password_hash(admin_user.password_hash, 'admin123')
        print(f"Password 'admin123' is correct: {password_correct}")
    else:
        print("\nAdmin user NOT found with email admin@example.com")
        print("Creating admin user...")
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
