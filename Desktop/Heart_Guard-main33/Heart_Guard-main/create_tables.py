#!/usr/bin/env python3
"""
Create all database tables
"""
import sys
sys.path.insert(0, '.')

try:
    print("Initializing app and creating tables...")
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()
        print("✅ Database tables created/updated successfully!")
        
        # Check what tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\nTables in database: {', '.join(tables)}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
