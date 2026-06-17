#!/usr/bin/env python3
"""
Test script to check database columns
"""

from app import create_app, db

def check_columns():
    app = create_app()
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('ecg_records')]
            print("Columns in ecg_records table:")
            for col in columns:
                print(f"  - {col}")
            
            if 'doctor_approved' in columns:
                print("✅ doctor_approved column exists")
            else:
                print("❌ doctor_approved column missing")
                
            if 'doctor_diagnosis' in columns:
                print("✅ doctor_diagnosis column exists")
            else:
                print("❌ doctor_diagnosis column missing")
                
            if 'approved_at' in columns:
                print("✅ approved_at column exists")
            else:
                print("❌ approved_at column missing")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    check_columns()