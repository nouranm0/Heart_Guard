# app/doctor/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from flask_babel import get_locale, Babel
from app.models import db, User, Patient, ECGRecord, Alert, UserSettings
from werkzeug.security import check_password_hash
import os
from .validation_service import validate_and_predict
from .echonext_service import echonext_predict
from datetime import datetime

doctor_bp = Blueprint('doctor', __name__)
ECHONEXT_MODEL = "model/weights.pt"

@doctor_bp.url_defaults
def add_language_code(endpoint, values):
    values.setdefault('lang_code', g.get('lang_code', 'en'))

@doctor_bp.url_value_preprocessor
def pull_lang_code(endpoint, values):
    g.lang_code = values.pop('lang_code', 'en')

@doctor_bp.before_request
def before_request():
    g.lang_code = request.args.get('lang', session.get('lang', 'en'))
    session['lang'] = g.lang_code

# -----------------------------------------
# Splash page -> render splash screen
@doctor_bp.route('/')
def splash_redirect():
    return redirect(url_for('doctor.splash'))

@doctor_bp.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('doctor.dashboard'))
@doctor_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('doctor.dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('doctor.login'))

    return render_template('login.html')


# -----------------------------------------
# Old splash page (محتفظة بيها زي ما هي)

# Admin-only user creation route
@doctor_bp.route('/add-user', methods=['GET', 'POST'])
def add_user():
    # Only allow if logged in as admin
    if 'user_id' not in session or session.get('role') != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {'success': False, 'message': 'Admin access required.'}, 403
        flash('Admin access required.', 'error')
        return redirect(url_for('doctor.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'doctor')
        
        # Validation
        if not username or not email or not password:
            error_msg = 'All fields are required.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))
        
        if User.query.filter_by(email=email).first():
            error_msg = 'Email already exists. Please use a different email.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))
        
        try:
            user = User(username=username, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            success_msg = f'{role.capitalize()} created successfully!'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': True, 'message': success_msg}, 200
            
            flash(success_msg, 'success')
            return redirect(url_for('doctor.add_user'))
        
        except Exception as e:
            db.session.rollback()
            error_msg = 'An error occurred while creating the user. Please try again.'
            print(f'Error creating user: {e}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 500
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))
    
    return render_template('add_user.html')

    # Person profile route
@doctor_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

# Logout route
@doctor_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('doctor.login'))

@doctor_bp.route('/splash')
def splash():
    return render_template('splash.html')

# -----------------------------------------
# Intro page
@doctor_bp.route('/intro')
def intro():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return render_template('intro.html', user=user)

# -----------------------------------------
# Model page
@doctor_bp.route('/model')
def model_page():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    return render_template('model.html')

# -----------------------------------------
# Doctor Dashboard - View Patients (Admin sees all, Doctor sees own patients only, Admin can view specific doctor's patients)
@doctor_bp.route('/doctor-dashboard')
def doctor_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    # Check if admin is viewing a specific doctor's patients
    view_doctor_id = request.args.get('doctor_id', type=int)
    viewed_doctor = None
    if view_doctor_id and user.role == 'admin':
        viewed_doctor = User.query.filter_by(id=view_doctor_id, role='doctor').first()
        if not viewed_doctor:
            flash('Doctor not found.', 'error')
            return redirect(url_for('doctor.doctor_dashboard'))

    # Search query (for patients/doctors)
    query = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', 'all').lower()
    if risk_filter not in ('all', 'low', 'medium', 'high'):
        risk_filter = 'all'

    # Admin can see all doctors, Doctor can only see their own patients
    if user.role == 'admin' and not view_doctor_id:
        doctors_query = User.query.filter_by(role='doctor')
        if query:
            doctors_query = doctors_query.filter(
                db.or_(
                    User.username.ilike(f"%{query}%"),
                    User.email.ilike(f"%{query}%")
                )
            )
        doctors = doctors_query.all()

        patients = Patient.query.all()  # Need all patients for counting per doctor
        return render_template(
            'doctor_dashboard.html',
            user=user,
            doctors=doctors,
            patients=patients,
            is_admin=True,
            current_date=datetime.utcnow().date(),
            query=query,
            risk_filter=risk_filter
        )
    else:
        # If admin viewing specific doctor, or doctor viewing own
        target_doctor_id = view_doctor_id if view_doctor_id else user_id
        patients_query = Patient.query.filter_by(doctor_id=target_doctor_id)
        if query:
            patients_query = patients_query.filter(
                db.or_(
                    Patient.name.ilike(f"%{query}%"),
                    Patient.phone.ilike(f"%{query}%")
                )
            )

        patients = patients_query.all()

        # Assign risk level based on number of assessments (or other metric)
        for p in patients:
            assessment_count = len(p.ecg_records)
            if assessment_count >= 5:
                p.risk = 'high'
            elif assessment_count >= 2:
                p.risk = 'medium'
            else:
                p.risk = 'low'

        if risk_filter in ('low', 'medium', 'high'):
            patients = [p for p in patients if p.risk == risk_filter]

        return render_template(
            'doctor_dashboard.html',
            user=user,
            patients=patients,
            doctor=user,
            viewed_doctor=viewed_doctor,
            is_admin=user.role == 'admin' and not view_doctor_id,
            is_viewing_doctor=bool(view_doctor_id),
            current_date=datetime.utcnow().date(),
            query=query,
            risk_filter=risk_filter
        )

# -----------------------------------------
# All Patients (Admin only)
@doctor_bp.route('/all-patients')
def all_patients():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('doctor.doctor_dashboard'))
    
    # Search and filter
    query = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', 'all').lower()
    sort_by = request.args.get('sort', 'recent').lower()
    
    if risk_filter not in ('all', 'low', 'medium', 'high'):
        risk_filter = 'all'
    if sort_by not in ('recent', 'oldest', 'name', 'doctor'):
        sort_by = 'recent'
    
    # Base query
    patients_query = Patient.query
    
    # Apply search filter
    if query:
        patients_query = patients_query.filter(
            db.or_(
                Patient.name.ilike(f"%{query}%"),
                Patient.phone.ilike(f"%{query}%")
            )
        )
    
    patients = patients_query.all()
    
    # Assign risk levels
    for p in patients:
        assessment_count = len(p.ecg_records)
        if assessment_count >= 5:
            p.risk = 'high'
        elif assessment_count >= 2:
            p.risk = 'medium'
        else:
            p.risk = 'low'
    
    # Apply risk filter
    if risk_filter in ('low', 'medium', 'high'):
        patients = [p for p in patients if p.risk == risk_filter]
    
    # Apply sorting
    if sort_by == 'name':
        patients.sort(key=lambda p: p.name)
    elif sort_by == 'doctor':
        patients.sort(key=lambda p: p.doctor.username if p.doctor else '')
    elif sort_by == 'oldest':
        patients.sort(key=lambda p: p.created_at)
    else:  # 'recent'
        patients.sort(key=lambda p: p.created_at, reverse=True)
    
    return render_template(
        'all_patients.html',
        user=user,
        patients=patients,
        query=query,
        risk_filter=risk_filter,
        sort_by=sort_by,
        current_date=datetime.utcnow().date()
    )

# -----------------------------------------
@doctor_bp.route('/doctor/<int:doctor_id>/patients')
def doctor_patients(doctor_id):
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('doctor.doctor_dashboard'))

    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Invalid doctor selected.', 'error')
        return redirect(url_for('doctor.doctor_dashboard'))

    patients = Patient.query.filter_by(doctor_id=doctor_id).all()

    return render_template(
        'doctor_patients.html',
        user=user,
        doctor=doctor,
        patients=patients,
        current_date=datetime.utcnow().date()
    )
# -----------------------------------------
# Add Patient (Doctor only)
@doctor_bp.route('/add-patient', methods=['GET', 'POST'])
def add_patient():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    
    # Only doctors can add patients
    if session.get('role') != 'doctor':
        flash('Only doctors can add patients.', 'error')
        return redirect(url_for('doctor.intro'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        birthday = request.form.get('birthday')
        
        if not name:
            flash('Patient name is required.', 'error')
            return redirect(url_for('doctor.add_patient'))
        
        patient = Patient(
            name=name,
            phone=phone,
            gender=gender,
            birthday=birthday if birthday else None,
            doctor_id=session['user_id']
        )
        db.session.add(patient)
        db.session.commit()
        flash('Patient added successfully!', 'success')
        return redirect(url_for('doctor.add_patient'))
    
    return render_template('add_patient.html')

# -----------------------------------------
# New assessment page
@doctor_bp.route('/new-assessment', methods=['GET', 'POST'])
def new_assessment():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    
    # Block admins from creating assessments
    if session.get('role') == 'admin':
        flash('Admins cannot create assessments. Only doctors can assess patients.', 'error')
        return redirect(url_for('doctor.intro'))
    
    user_id = session['user_id']
    patients = Patient.query.filter_by(doctor_id=user_id).all()

    # Get patient from query param if provided
    selected_patient_id = request.args.get('patient')
    selected_patient = None
    if selected_patient_id:
        selected_patient = Patient.query.filter_by(id=selected_patient_id, doctor_id=user_id).first()
        if not selected_patient:
            flash('Patient not found or access denied.', 'error')
            return redirect(url_for('doctor.new_assessment'))

    validation_result = {}
    all_results = []
    top_diagnosis = None
    top_confidence = None

    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if request.method == "POST":
        patient_id = request.form.get('patient_id')
        if not patient_id:
            flash('Please select a patient first.', 'error')
            return redirect(url_for('doctor.new_assessment'))
        
        # Verify the patient belongs to this doctor
        patient = Patient.query.filter_by(id=patient_id, doctor_id=user_id).first()
        if not patient:
            flash('Patient not found or access denied.', 'error')
            return redirect(url_for('doctor.new_assessment'))

        file = request.files.get("file")
        if not file or file.filename == "":
            flash('Please select a file to upload.', 'error')
            return redirect(url_for('doctor.new_assessment'))

        ext = file.filename.rsplit(".", 1)[-1].lower()
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(file_path)

        try:
            validation_result = {}
            all_results = []
            top_diagnosis = None
            top_confidence = None
            full_results = {}
            processing_error = None

            if ext in ["csv", "pdf", "mat"]:
                try:
                    validation_result = validate_and_predict(file_path) or {}
                except Exception as ve:
                    processing_error = f"Validation service error: {str(ve)}"
                    validation_result = {}
                prediction = validation_result.get("prediction") or {}
                if prediction:
                    all_results = [(k, v) for k, v in prediction.items()]
                    top_diagnosis = validation_result.get("top_diagnosis")
                    top_confidence = validation_result.get("top_confidence")
                    full_results = prediction
                elif not validation_result.get("is_valid", False):
                    processing_error = f"File validation failed: {', '.join(validation_result.get('reasons', ['Unknown validation error']))}"

            elif ext == "xml":
                try:
                    echonext_results = echonext_predict(file_path)
                except Exception as ee:
                    processing_error = f"EchoNext service error: {str(ee)}"
                    echonext_results = {}
                if echonext_results and echonext_results.get("is_ecg"):
                    prediction = echonext_results.get("prediction") or {}
                    if prediction:
                        all_results = [(k, v) for k, v in prediction.items()]
                        top_diagnosis = echonext_results.get("top_diagnosis")
                        top_confidence = echonext_results.get("top_confidence", 0)
                        full_results = prediction
                    else:
                        processing_error = "XML file detected as ECG but no analysis results generated"
                else:
                    processing_error = "XML file does not contain valid ECG waveform data or is not in a supported format"

            elif ext in ["jpg", "jpeg", "png"]:
                # Try validation service first
                try:
                    validation_result = validate_and_predict(file_path) or {}
                except Exception as ve:
                    validation_result = {}
                prediction = validation_result.get("prediction") or {}
                if prediction:
                    all_results = [(k, v) for k, v in prediction.items()]
                    top_diagnosis = validation_result.get("top_diagnosis")
                    top_confidence = validation_result.get("top_confidence")
                    full_results = prediction

                # Also try EchoNext for images
                try:
                    echonext_results = echonext_predict(file_path)
                except Exception as ee:
                    echonext_results = {}
                if echonext_results and echonext_results.get("is_ecg"):
                    prediction = echonext_results.get("prediction") or {}
                    for k, v in prediction.items():
                        all_results.append((f"{k}", v/10))
                    if not full_results:
                        full_results.update(prediction)
                        top_diagnosis = echonext_results.get("top_diagnosis")
                        top_confidence = echonext_results.get("top_confidence", 0)

                if not all_results:
                    processing_error = "Image file was not recognized as a valid ECG or could not be analyzed"

            else:
                processing_error = f"Unsupported file format: .{ext}. Supported formats: csv, xml, mat, pdf, jpg, jpeg, png"

            # Save assessment to database only if we have results
            if all_results and not processing_error:
                ecg_record = ECGRecord(
                    patient_id=int(patient_id),
                    doctor_id=user_id,
                    file_name=file.filename,
                    file_path=file_path,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    validation_status="completed" if validation_result else "processed",
                    top_diagnosis=top_diagnosis,
                    top_confidence=top_confidence,
                    full_results=full_results
                )
                db.session.add(ecg_record)
                db.session.commit()

                # Create alert for the assessment completion
                patient = Patient.query.get(int(patient_id))
                alert_title = f"New ECG Assessment Completed for {patient.name}"
                try:
                    confidence_str = f"{top_confidence:.1%}" if top_confidence is not None and isinstance(top_confidence, (int, float)) else 'N/A'
                    alert_message = f"Diagnosis: {top_diagnosis or 'Analysis completed'} (Confidence: {confidence_str})"
                except Exception:
                    alert_message = f"Diagnosis: {top_diagnosis or 'Analysis completed'} (Confidence: N/A)"
                
                alert_type = 'critical' if top_confidence and isinstance(top_confidence, (int, float)) and top_confidence > 0.8 else 'warning' if top_confidence and isinstance(top_confidence, (int, float)) and top_confidence > 0.5 else 'info'
                
                create_alert(user_id, int(patient_id), alert_type, alert_title, alert_message)

                # Redirect to assessment results page
                return redirect(url_for('doctor.view_assessment', assessment_id=ecg_record.id))
            elif processing_error:
                flash(f'Assessment failed: {processing_error}', 'error')
                db.session.rollback()
            else:
                flash('Assessment processed but no results were generated. The file may not contain valid ECG data.', 'warning')
                db.session.rollback()

        except Exception as e:
            print(f"Error in new_assessment: {e}")
            import traceback
            traceback.print_exc()
            flash(f'An unexpected error occurred during assessment: {str(e)}. Please check the file format and try again.', 'error')
            db.session.rollback()

        return redirect(url_for('doctor.new_assessment'))

    return render_template(
        "new_assessment.html",
        results=all_results,
        top_diagnosis=top_diagnosis,
        top_confidence=top_confidence,
        validation=validation_result,
        patients=patients,
        selected_patient=selected_patient
    )

# -----------------------------------------
# View Patient Details (Doctor/Admin)
@doctor_bp.route('/patient/<int:patient_id>')
def view_patient_details(patient_id):
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    
    user = User.query.get(session['user_id'])
    patient = Patient.query.get_or_404(patient_id)
    
    # Verify access: doctor can only view their own patients, admin can view all
    if user.role != 'admin' and patient.doctor_id != user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.doctor_dashboard'))
    
    # Get all assessments for this patient
    assessments = ECGRecord.query.filter_by(patient_id=patient_id).order_by(ECGRecord.created_at.desc()).all()
    
    return render_template('patient_details.html', patient=patient, assessments=assessments, user=user, current_date=datetime.utcnow().date())

# -----------------------------------------
# View Assessment Results
@doctor_bp.route('/assessment/<int:assessment_id>')
def view_assessment(assessment_id):
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
    
    user = User.query.get(session['user_id'])
    assessment = ECGRecord.query.get_or_404(assessment_id)
    patient = Patient.query.get(assessment.patient_id)
    
    # Verify access
    if user.role != 'admin' and assessment.doctor_id != user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.doctor_dashboard'))
    
    return render_template('assessment_results.html', assessment=assessment, patient=patient, user=user)

# -----------------------------------------  
# Dashboard redirect (for sidebar navigation)
@doctor_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    patient_id = request.args.get('patient_id', type=int)
    patient = None

    if patient_id:
        patient = Patient.query.get(patient_id)
        if not patient or (user.role != 'admin' and patient.doctor_id != user_id):
            flash('Patient not found or access denied.', 'error')
            return redirect(url_for('doctor.doctor_dashboard'))
    else:
        if user.role == 'doctor':
            patient = Patient.query.filter_by(doctor_id=user_id).order_by(Patient.created_at.desc()).first()
        else:
            patient = Patient.query.order_by(Patient.created_at.desc()).first()

    if not patient:
        flash('No patient data available yet. Please add a patient first.', 'info')
        return redirect(url_for('doctor.doctor_dashboard'))

    latest_assessment = ECGRecord.query.filter_by(patient_id=patient.id).order_by(ECGRecord.created_at.desc()).first()
    heart_rate = None
    blood_pressure = None
    temperature = None
    breathing_rate = None

    if latest_assessment and latest_assessment.full_results:
        results = latest_assessment.full_results or {}
        heart_rate = results.get('heart_rate') or results.get('HR') or results.get('hr')
        blood_pressure = results.get('blood_pressure') or results.get('BP') or results.get('blood_pressure_mm')
        temperature = results.get('temperature') or results.get('temp') or results.get('body_temperature')
        breathing_rate = results.get('breathing_rate') or results.get('respiration_rate') or results.get('resp_rate')

    return render_template(
        'dashboard.html',
        patient=patient,
        latest_assessment=latest_assessment,
        heart_rate=heart_rate,
        blood_pressure=blood_pressure,
        temperature=temperature,
        breathing_rate=breathing_rate,
        user=user,
        current_date=datetime.utcnow().date()
    )

# -----------------------------------------
# Helper function to create alerts
def create_alert(user_id, patient_id, alert_type, title, message):
    alert = Alert(
        user_id=user_id,
        patient_id=patient_id,
        alert_type=alert_type,
        title=title,
        message=message
    )
    db.session.add(alert)
    db.session.commit()
    return alert

# -----------------------------------------
# Alerts page
@doctor_bp.route('/alerts')
def alerts():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user = User.query.get(session['user_id'])

    if user.role == 'admin':
        alerts_list = Alert.query.order_by(Alert.created_at.desc()).all()
    else:
        patient_ids = [p.id for p in user.patients]
        alerts_list = Alert.query.filter(
            db.or_(Alert.user_id == user.id, Alert.patient_id.in_(patient_ids))
        ).order_by(Alert.created_at.desc()).all()

    return render_template('alerts.html', user=user, alerts=alerts_list)

# -----------------------------------------
# Mark alert as read
@doctor_bp.route('/alert/<int:alert_id>/read', methods=['POST'])
def mark_alert_read(alert_id):
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401

    user = User.query.get(session['user_id'])
    alert = Alert.query.get_or_404(alert_id)

    if user.role != 'admin' and alert.user_id != user.id:
        patient_ids = [p.id for p in user.patients]
        if alert.patient_id not in patient_ids:
            return {'success': False, 'message': 'Permission denied'}, 403

    alert.is_read = True
    db.session.commit()
    return {'success': True}

# -----------------------------------------
# Dismiss alert
@doctor_bp.route('/alert/<int:alert_id>/dismiss', methods=['POST'])
def dismiss_alert(alert_id):
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401

    user = User.query.get(session['user_id'])
    alert = Alert.query.get_or_404(alert_id)

    if user.role != 'admin' and alert.user_id != user.id:
        patient_ids = [p.id for p in user.patients]
        if alert.patient_id not in patient_ids:
            return {'success': False, 'message': 'Permission denied'}, 403

    db.session.delete(alert)
    db.session.commit()
    return {'success': True}

# -----------------------------------------
# Settings page
@doctor_bp.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user = User.query.get(session['user_id'])
    user_settings = UserSettings.query.filter_by(user_id=user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=user.id)
        db.session.add(user_settings)
        db.session.commit()

    return render_template('settings.html', user=user, settings=user_settings)

# -----------------------------------------
# Update settings
@doctor_bp.route('/settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user = User.query.get(session['user_id'])
    user_settings = UserSettings.query.filter_by(user_id=user.id).first()

    if not user_settings:
        user_settings = UserSettings(user_id=user.id)
        db.session.add(user_settings)

    user_settings.first_name = request.form.get('first_name', '')
    user_settings.last_name = request.form.get('last_name', '')
    user_settings.phone = request.form.get('phone', '')
    if request.form.get('date_of_birth'):
        user_settings.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()

    user_settings.email_notifications = 'email_notifications' in request.form
    user_settings.push_notifications = 'push_notifications' in request.form
    user_settings.sms_notifications = 'sms_notifications' in request.form

    user_settings.dark_mode = 'dark_mode' in request.form
    user_settings.language = request.form.get('language', 'en')

    db.session.commit()
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('doctor.settings'))
