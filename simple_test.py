#!/usr/bin/env python3
"""
Simple test script for database setup
"""

print('Creating app...')
from app import create_app
app = create_app()
print('App created successfully')

print('Testing database...')
from app import db
with app.app_context():
    db.create_all()
    print('Database tables created')

    # Check tables
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'Available tables: {tables}')

    # Test models
    from app.models import Alert, UserSettings, User
    print('Models imported successfully')

print('✅ All tests passed!')