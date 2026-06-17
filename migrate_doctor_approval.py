#!/usr/bin/env python3
"""
Migration script to add doctor approval fields to ECGRecord table
"""

from app import create_app, db
import pymysql

def add_doctor_approval_columns():
    """Add doctor_approved, doctor_diagnosis, doctor_note and approved_at columns to ecg_records table"""
    app = create_app()

    with app.app_context():
        try:
            # Use raw SQL to add columns
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            # Check existing columns
            cursor.execute("DESCRIBE ecg_records")
            columns = [row[0] for row in cursor.fetchall()]
            
            print(f"Existing columns: {columns}")
            
            if 'doctor_approved' not in columns:
                cursor.execute("ALTER TABLE ecg_records ADD COLUMN doctor_approved BOOLEAN DEFAULT FALSE")
                print("Added doctor_approved column")
            
            if 'doctor_diagnosis' not in columns:
                cursor.execute("ALTER TABLE ecg_records ADD COLUMN doctor_diagnosis TEXT")
                print("Added doctor_diagnosis column")
            
            if 'doctor_note' not in columns:
                cursor.execute("ALTER TABLE ecg_records ADD COLUMN doctor_note TEXT")
                print("Added doctor_note column")
            
            if 'approved_at' not in columns:
                cursor.execute("ALTER TABLE ecg_records ADD COLUMN approved_at DATETIME")
                print("Added approved_at column")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("✅ Migration completed successfully")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_doctor_approval_columns()