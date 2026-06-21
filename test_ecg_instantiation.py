import sys
from app import create_app
from app.models import db, Patient, User, ECGRecord
from datetime import datetime

print("Initializing test app context...")
app = create_app()

with app.app_context():
    doctor = User.query.filter_by(role='doctor').first()
    if not doctor:
        doctor = User.query.first()
    
    patient = Patient.query.first()
    if not patient:
        print("Creating dummy patient...")
        patient = Patient(name="Test Patient", phone="+12345", gender="male", doctor_id=doctor.id if doctor else None)
        db.session.add(patient)
        db.session.commit()
    
    print("Testing ECGRecord model instantiation and DB save...")
    try:
        record = ECGRecord(
            patient_id=patient.id,
            doctor_id=doctor.id if doctor else None,
            file_name="test_ecg.csv",
            file_path="uploads/test_ecg.csv",
            file_type="csv",
            file_size=1024,
            validation_status="completed",
            top_diagnosis="Normal",
            top_confidence=0.95,
            full_results={"Normal": 0.95, "AF": 0.05},
            review_status="pending",
            doctor_report=None,
            reviewed_at=None,
            reviewed_by_id=None
        )
        db.session.add(record)
        db.session.commit()
        print("✅ ECGRecord instance successfully created and saved in Database!")
        
        # Clean up
        db.session.delete(record)
        db.session.commit()
        print("✅ Cleanup completed!")
        sys.exit(0)
    except Exception as e:
        print("❌ Test failed with exception:")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        sys.exit(1)
