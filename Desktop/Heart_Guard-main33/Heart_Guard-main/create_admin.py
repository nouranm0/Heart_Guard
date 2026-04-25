#!/usr/bin/env python3
"""
Create admin user using the proper app context
"""
import sys
sys.path.insert(0, '.')

try:
    print("Initializing app...")
    from app import create_app, db
    from app.models import User
    
    app = create_app()
    
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@example.com').first()
        
        if admin:
            print("✅ Admin user already exists with email: admin@example.com")
        else:
            print("Creating admin user...")
            
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created successfully!")
            print(f"   Email: admin@example.com")
            print(f"   Password: admin123")
            print(f"   Role: admin")
        
        # List all users
        print("\nAll users in database:")
        users = User.query.all()
        for user in users:
            print(f"  - {user.username} ({user.email}) - Role: {user.role}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
