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

        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        ecg_columns = {column['name'] for column in inspector.get_columns('ecg_records')}
        alter_statements = []

        if 'review_status' not in ecg_columns:
            alter_statements.append("ALTER TABLE ecg_records ADD COLUMN review_status VARCHAR(20) DEFAULT 'pending'")
        if 'doctor_report' not in ecg_columns:
            alter_statements.append("ALTER TABLE ecg_records ADD COLUMN doctor_report TEXT")
        if 'reviewed_at' not in ecg_columns:
            alter_statements.append("ALTER TABLE ecg_records ADD COLUMN reviewed_at DATETIME")
        if 'reviewed_by_id' not in ecg_columns:
            alter_statements.append("ALTER TABLE ecg_records ADD COLUMN reviewed_by_id INTEGER NULL")

        for statement in alter_statements:
            print(f"Applying schema update: {statement}")
            db.session.execute(text(statement))
        if alter_statements:
            db.session.commit()

        print(" Database tables created/updated successfully!")
        
        # Check what tables exist
        tables = inspector.get_table_names()
        print(f"\nTables in database: {', '.join(tables)}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
