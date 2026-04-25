#!/usr/bin/env python3
"""
Create admin user directly without loading ML models
"""
import os
os.environ['SKIP_MODEL_LOADING'] = '1'  # Skip model loading if supported

import sys
sys.path.insert(0, '.')

# Bypass model loading by modifying the app creation
def create_app_no_models():
    import urllib.parse
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_babel import Babel
    
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', '')
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_db = os.environ.get('MYSQL_DATABASE', 'heartguard_db')
    encoded_password = urllib.parse.quote_plus(mysql_password)
    uri = f'mysql+pymysql://{mysql_user}:{encoded_password}@{mysql_host}/{mysql_db}' if mysql_password else f'mysql+pymysql://{mysql_user}@{mysql_host}/{mysql_db}'

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    app.config['SECRET_KEY'] = 'your-secret-key'
    
    db = SQLAlchemy(app)
    
    # Import models
    from app.models import User
    
    return app, db, User

try:
    app, db, User = create_app_no_models()
    
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@example.com').first()
        
        if admin:
            print("✅ Admin user already exists")
        else:
            print("Creating admin user...")
            from werkzeug.security import generate_password_hash
            
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
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
