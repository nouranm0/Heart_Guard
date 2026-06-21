# app/doctor/api_routes.py
# API Routes for Doctors and Patients Management

from flask import Blueprint, request, session, jsonify
from app.models import db, User, Patient, ECGRecord, Alert, UserSettings
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')

# -----------------------------------------
# ADD DOCTOR ROUTE (Admin only)
@api_bp.route('/doctor', methods=['POST'])
def add_doctor():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    data = request.get_json() or request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already exists'}), 400
    
    try:
        doctor = User(username=username, email=email, role='doctor')
        doctor.set_password(password)
        db.session.add(doctor)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Doctor added successfully',
            'doctor': {
                'id': doctor.id,
                'username': doctor.username,
                'email': doctor.email
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# -----------------------------------------
# DELETE DOCTOR ROUTE (Admin only)
@api_bp.route('/doctor/<int:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    print(f"[API DELETE] Request received for doctor_id: {doctor_id}, Type: {type(doctor_id).__name__}")
    print(f"[API DELETE] Session keys: {list(session.keys()) if session else 'No session'}")
    
    if 'user_id' not in session:
        print("[API DELETE] ERROR: Not authenticated - user_id not in session")
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    print(f"[API DELETE] Current user: {user.username if user else 'Not found'}, Role: {user.role if user else 'N/A'}")
    
    if not user or user.role != 'admin':
        print("[API DELETE] ERROR: Admin access required")
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first()
    print(f"[API DELETE] Doctor lookup result: {doctor.username if doctor else 'NOT FOUND'}")
    
    if not doctor:
        print(f"[API DELETE] ERROR: Doctor with id {doctor_id} not found")
        return jsonify({'success': False, 'message': 'Doctor not found'}), 404
    
    try:
        print(f"[API DELETE] Deleting doctor: {doctor.username} (ID: {doctor.id})")
        
        # Delete all ECG records associated with patients of this doctor
        ecg_records = ECGRecord.query.filter(
            ECGRecord.patient_id.in_(
                db.session.query(Patient.id).filter_by(doctor_id=doctor_id)
            )
        ).all()
        print(f"[API DELETE] Found {len(ecg_records)} ECG records to delete")
        for ecg in ecg_records:
            db.session.delete(ecg)
        
        # Delete all patients of this doctor (cascade)
        patients = Patient.query.filter_by(doctor_id=doctor_id).all()
        print(f"[API DELETE] Found {len(patients)} patients to delete")
        for patient in patients:
            db.session.delete(patient)
        
        # Delete the doctor
        db.session.delete(doctor)
        db.session.commit()
        
        print(f"[API DELETE] SUCCESS: Doctor {doctor.username} (ID: {doctor.id}) deleted successfully")
        return jsonify({'success': True, 'message': 'Doctor deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"[API DELETE] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# -----------------------------------------
# DELETE PATIENT ROUTE (Admin/Doctor)
@api_bp.route('/patient/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    print(f"[DELETE PATIENT] Request to delete patient ID: {patient_id}")
    
    if 'user_id' not in session:
        print("[DELETE PATIENT] ERROR: Not authenticated")
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    patient = Patient.query.get(patient_id)
    
    if not patient:
        print(f"[DELETE PATIENT] ERROR: Patient {patient_id} not found")
        return {'success': False, 'message': 'Patient not found'}, 404
    
    # Check access: admin can delete any patient, doctor can only delete their own
    if user.role != 'admin' and patient.doctor_id != user.id:
        print(f"[DELETE PATIENT] ERROR: Access denied for user {user.id} trying to delete patient {patient_id}")
        return {'success': False, 'message': 'Access denied'}, 403
    
    try:
        patient_name = patient.name
        print(f"[DELETE PATIENT] Deleting patient: {patient_name} (ID: {patient_id})")
        
        # Delete all ECG records for this patient
        ecg_records = ECGRecord.query.filter_by(patient_id=patient_id).all()
        print(f"[DELETE PATIENT] Found {len(ecg_records)} ECG records to delete")
        for record in ecg_records:
            db.session.delete(record)
        
        # Delete all alerts for this patient
        alerts = Alert.query.filter_by(patient_id=patient_id).all()
        print(f"[DELETE PATIENT] Found {len(alerts)} alerts to delete")
        for alert in alerts:
            db.session.delete(alert)
        
        # Delete the patient
        db.session.delete(patient)
        db.session.commit()
        
        print(f"[DELETE PATIENT] SUCCESS: Patient {patient_name} (ID: {patient_id}) deleted successfully")
        return {'success': True, 'message': 'Patient deleted successfully'}, 200
    except Exception as e:
        db.session.rollback()
        print(f"[DELETE PATIENT] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Error: {str(e)}'}, 500

# -----------------------------------------
# GET DOCTORS LIST (API - Admin only)
@api_bp.route('/doctors')
def get_doctors():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return {'success': False, 'message': 'Admin access required'}, 403
    
    search_query = request.args.get('q', '').strip()
    
    doctors_query = User.query.filter_by(role='doctor')
    if search_query:
        doctors_query = doctors_query.filter(
            db.or_(
                User.username.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%")
            )
        )
    
    doctors = doctors_query.all()
    
    doctors_data = []
    for doctor in doctors:
        patient_count = Patient.query.filter_by(doctor_id=doctor.id).count()
        ecg_count = db.session.query(db.func.count(ECGRecord.id)).filter(
            ECGRecord.doctor_id == doctor.id
        ).scalar() or 0
        
        doctors_data.append({
            'id': doctor.id,
            'username': doctor.username,
            'email': doctor.email,
            'total_patients': patient_count,
            'total_assessments': ecg_count,
            'created_at': doctor.created_at.isoformat()
        })
    
    return {'success': True, 'doctors': doctors_data}, 200

# -----------------------------------------
# GET PATIENTS LIST (API - with doctor info and search)
@api_bp.route('/patients')
def get_patients():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return {'success': False, 'message': 'Admin access required'}, 403
    
    search_query = request.args.get('q', '').strip()
    doctor_id_str = request.args.get('doctor_id', '').strip()
    limit_str = request.args.get('limit', '100').strip()
    offset_str = request.args.get('offset', '0').strip()
    
    doctor_id = None
    try:
        if doctor_id_str:
            doctor_id = int(doctor_id_str)
        limit = int(limit_str) if limit_str else 100
        offset = int(offset_str) if offset_str else 0
    except (ValueError, TypeError):
        limit = 100
        offset = 0
    
    print(f"[GET PATIENTS] Search: '{search_query}', Doctor: {doctor_id}, Limit: {limit}, Offset: {offset}")
    
    patients_query = Patient.query
    
    if doctor_id:
        patients_query = patients_query.filter_by(doctor_id=doctor_id)
    
    if search_query:
        patients_query = patients_query.filter(
            db.or_(
                Patient.name.ilike(f"%{search_query}%"),
                Patient.phone.ilike(f"%{search_query}%")
            )
        )
    
    total_count = patients_query.count()
    patients = patients_query.limit(limit).offset(offset).all()
    
    patients_data = []
    for patient in patients:
        ecg_count = ECGRecord.query.filter_by(patient_id=patient.id).count()
        doctor_name = patient.doctor.username if patient.doctor else 'Not assigned'
        
        patients_data.append({
            'id': patient.id,
            'name': patient.name,
            'phone': patient.phone or '',
            'gender': patient.gender or '',
            'birthday': patient.birthday.isoformat() if patient.birthday else None,
            'doctor_id': patient.doctor_id,
            'doctor_name': doctor_name,
            'total_records': ecg_count,
            'created_at': patient.created_at.isoformat()
        })
    
    print(f"[GET PATIENTS] Found {len(patients)} patients out of {total_count} total")
    
    return {
        'success': True,
        'patients': patients_data,
        'total': total_count,
        'returned': len(patients)
    }, 200

# -----------------------------------------
# GET PATIENT DETAILS (API - with all records)
@api_bp.route('/patient/<int:patient_id>')
def get_patient_details(patient_id):
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    patient = Patient.query.get(patient_id)
    
    if not patient:
        return {'success': False, 'message': 'Patient not found'}, 404
    
    # Check access
    if user.role != 'admin' and patient.doctor_id != user.id:
        return {'success': False, 'message': 'Access denied'}, 403
    
    # Get all ECG records
    records = ECGRecord.query.filter_by(patient_id=patient_id).order_by(ECGRecord.created_at.desc()).all()
    
    records_data = []
    for record in records:
        records_data.append({
            'id': record.id,
            'file_name': record.file_name,
            'file_type': record.file_type,
            'top_diagnosis': record.top_diagnosis,
            'top_confidence': float(record.top_confidence) if record.top_confidence else None,
            'validation_status': record.validation_status,
            'created_at': record.created_at.isoformat()
        })
    
    patient_data = {
        'id': patient.id,
        'name': patient.name,
        'phone': patient.phone or '',
        'gender': patient.gender or '',
        'birthday': patient.birthday.isoformat() if patient.birthday else None,
        'doctor_id': patient.doctor_id,
        'doctor_name': patient.doctor.username if patient.doctor else 'Not assigned',
        'total_records': len(records),
        'records': records_data,
        'created_at': patient.created_at.isoformat()
    }
    
    return {'success': True, 'patient': patient_data}, 200

# -----------------------------------------
# ADD PATIENT ROUTE (Admin or Doctor)
@api_bp.route('/patient', methods=['POST'])
def add_patient():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    if not user or user.role not in ['admin', 'doctor']:
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json() or request.form
    name = data.get('name')
    phone = data.get('phone')
    gender = data.get('gender')
    birthday = data.get('birthday')
    doctor_id = None
    
    if isinstance(data, dict):
        try:
            doctor_id = int(data.get('doctor_id', 0)) if data.get('doctor_id') else None
        except (ValueError, TypeError):
            pass
    
    if not name:
        return {'success': False, 'message': 'Patient name is required'}, 400
    
    # If doctor is adding patient, default to themselves
    if user.role == 'doctor' and not doctor_id:
        doctor_id = user.id
    
    # If admin is adding patient, require doctor_id
    if user.role == 'admin' and not doctor_id:
        return {'success': False, 'message': 'Doctor ID is required for admin'}, 400
    
    # Verify doctor exists
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first()
    if not doctor:
        return {'success': False, 'message': 'Doctor not found'}, 404
    
    # Doctor can only add patients to themselves
    if user.role == 'doctor' and user.id != doctor_id:
        return {'success': False, 'message': 'Doctors can only add patients to themselves'}, 403
    
    try:
        patient = Patient(
            name=name,
            phone=phone,
            gender=gender,
            doctor_id=doctor_id
        )
        
        if birthday:
            from datetime import datetime
            try:
                patient.birthday = datetime.fromisoformat(birthday).date()
            except (ValueError, TypeError):
                pass
        
        db.session.add(patient)
        db.session.commit()
        
        print(f"[ADD PATIENT] New patient '{name}' added to doctor {doctor.username} (ID: {doctor_id})")
        
        return {
            'success': True,
            'message': 'Patient added successfully',
            'patient': {
                'id': patient.id,
                'name': patient.name,
                'phone': patient.phone or '',
                'gender': patient.gender or '',
                'doctor_id': patient.doctor_id,
                'doctor_name': doctor.username
            }
        }, 201
    except Exception as e:
        db.session.rollback()
        print(f"[ADD PATIENT] ERROR: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}, 500
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Error: {str(e)}'}, 500

# -----------------------------------------
# GET DASHBOARD STATS (API)
@api_bp.route('/dashboard/stats')
def get_dashboard_stats():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    
    if user.role == 'admin':
        # Admin dashboard stats
        total_doctors = db.session.query(db.func.count(User.id)).filter_by(role='doctor').scalar() or 0
        total_patients = db.session.query(db.func.count(Patient.id)).scalar() or 0
        total_ecg_records = db.session.query(db.func.count(ECGRecord.id)).scalar() or 0
        
        # Calculate risk levels
        patients = Patient.query.all()
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        
        for patient in patients:
            ecg_count = len(patient.ecg_records)
            if ecg_count >= 5:
                high_risk_count += 1
            elif ecg_count >= 2:
                medium_risk_count += 1
            else:
                low_risk_count += 1
        
        # Recent alerts
        recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
        alerts_data = [{
            'id': a.id,
            'title': a.title,
            'message': a.message,
            'alert_type': a.alert_type,
            'is_read': a.is_read,
            'created_at': a.created_at.isoformat()
        } for a in recent_alerts]
        
        return {
            'success': True,
            'stats': {
                'total_doctors': total_doctors,
                'total_patients': total_patients,
                'total_ecg_records': total_ecg_records,
                'high_risk_count': high_risk_count,
                'medium_risk_count': medium_risk_count,
                'low_risk_count': low_risk_count,
                'recent_alerts': alerts_data
            }
        }, 200
    else:
        # Doctor dashboard stats
        doctor_id = user.id
        patient_count = Patient.query.filter_by(doctor_id=doctor_id).count()
        ecg_count = db.session.query(db.func.count(ECGRecord.id)).filter(
            ECGRecord.doctor_id == doctor_id
        ).scalar() or 0
        
        return {
            'success': True,
            'stats': {
                'my_patients': patient_count,
                'my_assessments': ecg_count
            }
        }, 200

# -----------------------------------------
# GET ALERTS (API)
@api_bp.route('/alerts')
def get_alerts_api():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    alert_type = request.args.get('type', 'all')
    is_read = request.args.get('read', 'all')
    
    query = Alert.query
    
    # Filter by alert type
    if alert_type != 'all':
        query = query.filter_by(alert_type=alert_type)
    
    # Filter by read status
    if is_read == 'true':
        query = query.filter_by(is_read=True)
    elif is_read == 'false':
        query = query.filter_by(is_read=False)
    
    # Filter by access level
    if user.role != 'admin':
        patient_ids = [p.id for p in user.patients]
        query = query.filter(
            db.or_(Alert.user_id == user.id, Alert.patient_id.in_(patient_ids))
        )
    
    alerts = query.order_by(Alert.created_at.desc()).all()
    
    alerts_data = []
    for alert in alerts:
        alerts_data.append({
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'alert_type': alert.alert_type,
            'is_read': alert.is_read,
            'patient_id': alert.patient_id,
            'patient_name': alert.patient.name if alert.patient else None,
            'created_at': alert.created_at.isoformat(),
            'updated_at': alert.updated_at.isoformat() if alert.updated_at else None
        })
    
    return {'success': True, 'alerts': alerts_data}, 200

# -----------------------------------------
# UPDATE ALERT STATUS (API)
@api_bp.route('/alert/<int:alert_id>/status', methods=['PUT'])
def update_alert_status(alert_id):
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    alert = Alert.query.get(alert_id)
    
    if not alert:
        return {'success': False, 'message': 'Alert not found'}, 404
    
    # Check access
    if user.role != 'admin':
        patient_ids = [p.id for p in user.patients]
        if alert.patient_id not in patient_ids and alert.user_id != user.id:
            return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    is_read = data.get('is_read')
    
    if is_read is not None:
        alert.is_read = bool(is_read)
        alert.updated_at = datetime.utcnow()
        db.session.commit()
    
    return {'success': True, 'alert': {
        'id': alert.id,
        'is_read': alert.is_read
    }}, 200

# -----------------------------------------
# DELETE ALERT (API)
@api_bp.route('/alert/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    alert = Alert.query.get(alert_id)
    
    if not alert:
        return {'success': False, 'message': 'Alert not found'}, 404
    
    # Check access - only admin or alert owner can delete
    if user.role != 'admin' and alert.user_id != user.id:
        return {'success': False, 'message': 'Access denied'}, 403
    
    try:
        db.session.delete(alert)
        db.session.commit()
        return {'success': True, 'message': 'Alert deleted successfully'}, 200
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Error: {str(e)}'}, 500

# -----------------------------------------
# GET USER SETTINGS (API)
@api_bp.route('/user/settings')
def get_user_settings():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    settings = user.user_settings if hasattr(user, 'user_settings') else None
    
    if not settings:
        return {
            'success': True,
            'settings': {
                'theme': 'dark',
                'language': 'en',
                'notifications': {
                    'email': False,
                    'push': False,
                    'sms': False
                }
            }
        }, 200
    
    return {
        'success': True,
        'settings': {
            'first_name': settings.first_name or '',
            'last_name': settings.last_name or '',
            'phone': settings.phone or '',
            'date_of_birth': settings.date_of_birth.isoformat() if settings.date_of_birth else None,
            'theme': 'dark' if settings.dark_mode else 'light',
            'language': settings.language or 'en',
            'notifications': {
                'email': settings.email_notifications,
                'push': settings.push_notifications,
                'sms': settings.sms_notifications
            }
        }
    }, 200

# -----------------------------------------
# UPDATE USER SETTINGS (API)
@api_bp.route('/user/settings', methods=['PUT', 'POST'])
def update_user_settings():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    settings = user.user_settings if hasattr(user, 'user_settings') else None
    
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
    
    data = request.get_json() or request.form
    
    try:
        if data.get('first_name'):
            settings.first_name = data.get('first_name')
        if data.get('last_name'):
            settings.last_name = data.get('last_name')
        if data.get('phone'):
            settings.phone = data.get('phone')
        if data.get('date_of_birth'):
            settings.date_of_birth = datetime.fromisoformat(data.get('date_of_birth')).date()
        
        if 'notifications' in data:
            notifications = data.get('notifications', {})
            settings.email_notifications = notifications.get('email', False)
            settings.push_notifications = notifications.get('push', False)
            settings.sms_notifications = notifications.get('sms', False)
        
        if data.get('theme'):
            settings.dark_mode = data.get('theme') == 'dark'
        if data.get('language'):
            settings.language = data.get('language')
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Settings updated successfully',
            'settings': {
                'first_name': settings.first_name or '',
                'last_name': settings.last_name or '',
                'phone': settings.phone or '',
                'date_of_birth': settings.date_of_birth.isoformat() if settings.date_of_birth else None,
                'theme': 'dark' if settings.dark_mode else 'light',
                'language': settings.language or 'en',
                'notifications': {
                    'email': settings.email_notifications,
                    'push': settings.push_notifications,
                    'sms': settings.sms_notifications
                }
            }
        }, 200
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Error: {str(e)}'}, 500
