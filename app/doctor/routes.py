# app/doctor/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from app.models import db, User, Patient, ECGRecord, Alert, UserSettings, PasswordResetToken, EmailOutbox
from app.validation_utils import (
    normalize_email,
    normalize_phone,
    normalize_username,
    validate_email,
    validate_password_strength,
    validate_phone,
)
import os
import hashlib
import secrets
from .echonext_service import echonext_predict
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

doctor_bp = Blueprint('doctor', __name__)
ECHONEXT_MODEL = "model/weights.pt"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

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


def _alert_query_for_user(user):
    query = Alert.query
    if user.role != 'admin':
        patient_ids = [p.id for p in user.patients]
        query = query.filter(db.or_(Alert.user_id == user.id, Alert.patient_id.in_(patient_ids)))
    return query


def _unread_alert_count_for_user(user):
    return _alert_query_for_user(user).filter_by(is_read=False).count()


@doctor_bp.context_processor
def inject_unread_alert_count():
    if 'user_id' in session:
        try:
            user = User.query.get(session['user_id'])
            if user:
                return {'unread_alert_count': _unread_alert_count_for_user(user)}
        except Exception:
            pass
    return {'unread_alert_count': 0}



def _hash_reset_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _create_password_reset_token(user, expires_in_hours=1):
    raw_token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_reset_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
    )
    db.session.add(reset_token)
    db.session.commit()
    return raw_token


def _queue_password_reset_email(user, reset_url):
    email_outbox = EmailOutbox(
        user_id=user.id,
        recipient_email=user.email,
        subject='HEARTGUARD password reset',
        body=(
            f'Hello {user.username},\n\n'
            f'Use this password reset link: {reset_url}\n\n'
            'This link expires in 1 hour. If you did not request a reset, ignore this message.'
        ),
        related_type='password_reset',
        status='queued'
    )
    db.session.add(email_outbox)
    db.session.commit()
    return email_outbox


def _get_password_reset_token(raw_token):
    if not raw_token:
        return None

    token_hash = _hash_reset_token(raw_token)
    reset_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    if not reset_token:
        return None

    if reset_token.used_at is not None or reset_token.expires_at <= datetime.utcnow():
        return None

    return reset_token


def _classify_patient_risk(assessment_count, latest_diagnosis, latest_confidence):
    diagnosis = (latest_diagnosis or '').strip().upper()

    diagnosis_risk_map = {
        'AF': 'high',
        'LBBB': 'high',
        'RBBB': 'medium',
        '1DAVB': 'medium',
        'ST': 'medium',
        'SB': 'low',
    }

    if diagnosis in diagnosis_risk_map:
        return diagnosis_risk_map[diagnosis]

    if latest_confidence is not None:
        if latest_confidence >= 0.8:
            return 'high'
        if latest_confidence >= 0.5:
            return 'medium'
        return 'low'

    if assessment_count >= 5:
        return 'high'
    if assessment_count >= 2:
        return 'medium'
    return 'low'


def _risk_to_alert_type(risk):
    if risk == 'high':
        return 'critical'
    if risk == 'medium':
        return 'warning'
    return 'info'


def _prepare_patient_overview(patients):
    patient_ids = [patient.id for patient in patients]
    assessment_counts = {}
    latest_records_by_patient = {}

    if patient_ids:
        assessment_counts = dict(
            db.session.query(
                ECGRecord.patient_id,
                db.func.count(ECGRecord.id)
            )
            .filter(ECGRecord.patient_id.in_(patient_ids))
            .group_by(ECGRecord.patient_id)
            .all()
        )

        latest_records = (
            ECGRecord.query
            .filter(ECGRecord.patient_id.in_(patient_ids))
            .order_by(ECGRecord.patient_id, ECGRecord.created_at.desc(), ECGRecord.id.desc())
            .all()
        )

        for record in latest_records:
            if record.patient_id not in latest_records_by_patient:
                latest_records_by_patient[record.patient_id] = record

    stats = {
        'total_assessments': 0,
        'high_risk_count': 0,
        'medium_risk_count': 0,
        'low_risk_count': 0,
    }

    for patient in patients:
        record = latest_records_by_patient.get(patient.id)
        assessment_count = assessment_counts.get(patient.id, 0)
        latest_confidence = float(record.top_confidence) if record and record.top_confidence is not None else None
        risk = _classify_patient_risk(assessment_count, record.top_diagnosis if record else None, latest_confidence)

        patient.assessment_count = assessment_count
        patient.latest_assessment = record
        patient.latest_diagnosis = record.top_diagnosis if record else None
        patient.latest_confidence = latest_confidence
        patient.latest_validation_status = record.validation_status if record else None
        patient.latest_file_type = record.file_type if record else None
        patient.last_assessed_at = record.created_at if record else None
        patient.risk = risk

        stats['total_assessments'] += assessment_count
        stats[f'{risk}_risk_count'] += 1

    return patients, stats

# -----------------------------------------
# Splash page -> render splash screen
@doctor_bp.route('/')
def splash_redirect():
    return redirect(url_for('doctor.splash'))

@doctor_bp.route('/set_language/<lang>')
def set_language(lang):
    if lang not in ('en', 'ar'):
        lang = 'en'
    session['lang'] = lang
    return redirect(request.referrer or url_for('doctor.doctor_dashboard'))
@doctor_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = normalize_email(request.form.get('email'))
        password = request.form.get('password')

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return redirect(url_for('doctor.login'))

        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('doctor.login'))

        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user and user.is_active and user.role in ('admin', 'doctor') and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('doctor.doctor_dashboard'))
        else:
            if user and not user.is_active:
                flash('This account is inactive. Please contact an administrator.', 'error')
                return redirect(url_for('doctor.login'))
            flash('Invalid email or password', 'error')
            return redirect(url_for('doctor.login'))

    return render_template('login.html')


@doctor_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = normalize_email(request.form.get('email'))

        if not email:
            flash('Please enter your email address.', 'error')
            return redirect(url_for('doctor.forgot_password'))

        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('doctor.forgot_password'))

        user = User.query.filter(db.func.lower(User.email) == email, User.role.in_(['admin', 'doctor'])).first()
        if not user or not user.is_active:
            flash('No active admin or doctor account matches that email.', 'error')
            return redirect(url_for('doctor.forgot_password'))

        raw_token = _create_password_reset_token(user)
        reset_url = url_for('doctor.reset_password', token=raw_token, _external=False)
        email_outbox = _queue_password_reset_email(user, reset_url)

        return render_template(
            'forgot_password.html',
            email=email,
            reset_url=reset_url,
            user=user,
            email_outbox=email_outbox
        )

    return render_template('forgot_password.html')


@doctor_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = _get_password_reset_token(token)
    if not reset_token:
        flash('This reset link is invalid or expired.', 'error')
        return redirect(url_for('doctor.forgot_password'))

    user = reset_token.user

    if request.method == 'POST':
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if not new_password or not confirm_password:
            flash('Please complete both password fields.', 'error')
            return render_template('reset_password.html', token=token, user=user)

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'error')
            return render_template('reset_password.html', token=token, user=user)

        password_ok, password_message = validate_password_strength(new_password)
        if not password_ok:
            flash(password_message, 'error')
            return render_template('reset_password.html', token=token, user=user)

        user.set_password(new_password)
        reset_token.used_at = datetime.utcnow()
        db.session.commit()

        flash('Password updated successfully. Please log in again.', 'success')
        return redirect(url_for('doctor.login'))

    return render_template('reset_password.html', token=token, user=user)


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
        username = normalize_username(request.form.get('username'))
        email = normalize_email(request.form.get('email'))
        password = request.form.get('password')
        role = request.form.get('role', 'doctor')
        phone = normalize_phone(request.form.get('phone'))
        
        # Validation
        if not username or not email or not password:
            error_msg = 'All required fields must be completed.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))
        
        if not validate_email(email):
            error_msg = 'Please enter a valid email address.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))

        password_ok, password_message = validate_password_strength(password)
        if not password_ok:
            error_msg = password_message
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))

        if phone and not validate_phone(phone):
            error_msg = 'Please enter a valid phone number.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))

        if role not in ('admin', 'doctor'):
            error_msg = 'Invalid role selected.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))

        if User.query.filter(db.func.lower(User.email) == email).first():
            error_msg = 'Email already exists. Please use a different email.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(url_for('doctor.add_user'))
        
        try:
            user = User(username=username, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if phone:
                user_settings = UserSettings.query.filter_by(user_id=user.id).first()
                if not user_settings:
                    user_settings = UserSettings(user_id=user.id)
                    db.session.add(user_settings)
                user_settings.phone = phone

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
# Doctor Dashboard - View Patients (Admin can inspect a specific doctor; doctors see their own patients)
@doctor_bp.route('/doctor-dashboard')
def doctor_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    user = User.query.get(session['user_id'])
    view_doctor_id = request.args.get('doctor_id', type=int)
    query = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', 'all').lower()

    if risk_filter not in ('all', 'low', 'medium', 'high'):
        risk_filter = 'all'

    if user.role == 'admin' and not view_doctor_id:
        doctors_query = User.query.filter_by(role='doctor')
        if query:
            doctors_query = doctors_query.filter(
                db.or_(
                    User.username.ilike(f"{query}%"),
                    User.email.ilike(f"{query}%")
                )
            )

        doctors = doctors_query.all()
        for doctor in doctors:
            doctor.patient_count = Patient.query.filter_by(doctor_id=doctor.id).count()
            doctor.ecg_count = db.session.query(db.func.count(ECGRecord.id)).filter(
                ECGRecord.doctor_id == doctor.id
            ).scalar() or 0

        return render_template(
            'doctors_list.html',
            user=user,
            doctors=doctors,
            is_admin=True,
            current_date=datetime.utcnow().date(),
            query=query,
            home_url=url_for('doctor.doctor_dashboard')
        )

    viewed_doctor = None
    target_doctor = user
    if user.role == 'admin' and view_doctor_id:
        viewed_doctor = User.query.filter_by(id=view_doctor_id, role='doctor').first()
        if not viewed_doctor:
            flash('Doctor not found.', 'error')
            return redirect(url_for('doctor.doctor_dashboard'))
        target_doctor = viewed_doctor

    patients_query = Patient.query.filter_by(doctor_id=target_doctor.id)
    if query:
        patients_query = patients_query.filter(
            db.or_(
                Patient.name.ilike(f"{query}%"),
                Patient.phone.ilike(f"{query}%")
            )
        )

    patients, stats = _prepare_patient_overview(patients_query.order_by(Patient.created_at.desc()).all())
    filtered_patients = patients
    if risk_filter in ('low', 'medium', 'high'):
        filtered_patients = [patient for patient in patients if patient.risk == risk_filter]

    unread_alert_count = _unread_alert_count_for_user(user)
    recent_alerts = _alert_query_for_user(user).order_by(Alert.created_at.desc()).limit(4).all()

    return render_template(
        'doctor_dashboard.html',
        user=user,
        doctor=target_doctor,
        viewed_doctor=viewed_doctor,
        patients=filtered_patients,
        total_patients_count=len(patients),
        visible_patients_count=len(filtered_patients),
        total_assessments=stats['total_assessments'],
        high_risk_count=stats['high_risk_count'],
        medium_risk_count=stats['medium_risk_count'],
        low_risk_count=stats['low_risk_count'],
        unread_alert_count=unread_alert_count,
        recent_alerts=recent_alerts,
        current_date=datetime.utcnow().date(),
        query=query,
        risk_filter=risk_filter,
        is_admin_view=user.role == 'admin' and bool(view_doctor_id),
        is_viewing_doctor=bool(view_doctor_id),
        home_url=url_for('doctor.doctor_dashboard', doctor_id=view_doctor_id) if view_doctor_id else url_for('doctor.doctor_dashboard')
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
    
    patients, overview_stats = _prepare_patient_overview(patients_query.order_by(Patient.created_at.desc()).all())
    
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

    risk_counts = {
        'total': len(patients),
        'high': sum(1 for patient in patients if patient.risk == 'high'),
        'medium': sum(1 for patient in patients if patient.risk == 'medium'),
        'low': sum(1 for patient in patients if patient.risk == 'low'),
    }

    is_ajax_request = request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax_request:
        return render_template(
            'all_patients_results.html',
            user=user,
            patients=patients,
            query=query,
            risk_filter=risk_filter,
            sort_by=sort_by,
            current_date=datetime.utcnow().date(),
            risk_counts=risk_counts,
        )
    
    return render_template(
        'all_patients.html',
        user=user,
        patients=patients,
        doctors=User.query.filter_by(role='doctor').all(),
        query=query,
        risk_filter=risk_filter,
        sort_by=sort_by,
        total_assessments=overview_stats['total_assessments'],
        current_date=datetime.utcnow().date(),
        risk_counts=risk_counts,
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

    doctor = User.query.filter_by(id=doctor_id, role='doctor').first()
    if not doctor:
        flash('Invalid doctor selected.', 'error')
        return redirect(url_for('doctor.doctor_dashboard'))

    return redirect(url_for('doctor.doctor_dashboard', doctor_id=doctor.id))
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
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        birthday = request.form.get('birthday')
        
        if not name:
            flash('Patient name is required.', 'error')
            return redirect(url_for('doctor.add_patient'))
        
        try:
            from datetime import datetime
            patient = Patient(
                name=name,
                phone=phone,
                gender=gender,
                birthday=datetime.fromisoformat(birthday).date() if birthday else None,
                doctor_id=session['user_id']
            )
            db.session.add(patient)
            db.session.commit()
            print(f"[ADD PATIENT] Patient '{name}' added by doctor {user.username} (ID: {user.id})")
            flash('تم إضافة المريض بنجاح ✓', 'success')
            return redirect(url_for('doctor.add_patient'))
        except Exception as e:
            db.session.rollback()
            print(f"[ADD PATIENT] ERROR: {str(e)}")
            flash(f'حدث خطأ: {str(e)}', 'error')
            return redirect(url_for('doctor.add_patient'))
    
    return render_template('add_patient.html', user=user)

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

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if request.method == "POST":
        from .validation_service import validate_and_predict

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

        safe_filename = secure_filename(file.filename or 'ecg_upload')
        if not safe_filename or '.' not in safe_filename:
            flash('Please upload a file with a valid name and extension.', 'error')
            return redirect(url_for('doctor.new_assessment'))

        ext = safe_filename.rsplit('.', 1)[-1].lower()
        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{safe_filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
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
                    file_name=safe_filename,
                    file_path=file_path,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    validation_status="completed" if validation_result else "processed",
                    top_diagnosis=top_diagnosis,
                    top_confidence=top_confidence,
                    full_results=full_results,
                    review_status='pending'
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
                
                alert_risk = _classify_patient_risk(1, top_diagnosis, top_confidence)
                alert_type = _risk_to_alert_type(alert_risk)
                
                create_alert(user_id, int(patient_id), alert_type, alert_title, alert_message)

                # Redirect to doctor review page before publishing results
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
        user=User.query.get(user_id),
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
    latest_assessment = assessments[0] if assessments else None

    # Calculate patient risk and additional stats for the template
    assessment_count = len(assessments)
    latest_diagnosis = latest_assessment.top_diagnosis if latest_assessment else None
    latest_confidence = float(latest_assessment.top_confidence) if latest_assessment and latest_assessment.top_confidence is not None else None
    
    patient.risk = _classify_patient_risk(assessment_count, latest_diagnosis, latest_confidence)
    patient.assessment_count = assessment_count
    patient.latest_assessment = latest_assessment
    patient.latest_diagnosis = latest_diagnosis
    patient.latest_confidence = latest_confidence
    patient.last_assessed_at = latest_assessment.created_at if latest_assessment else None

    unread_alert_count = _unread_alert_count_for_user(user)

    return render_template(
        'patient_details.html',
        patient=patient,
        assessments=assessments,
        latest_assessment=latest_assessment,
        user=user,
        unread_alert_count=unread_alert_count,
        current_date=datetime.utcnow().date()
    )



# -----------------------------------------
# View Assessment Results
@doctor_bp.route('/assessment/<int:assessment_id>', methods=['GET', 'POST'])
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

    if request.method == 'POST':
        if user.role == 'admin' or assessment.doctor_id != user.id:
            flash('Access denied.', 'error')
            return redirect(url_for('doctor.view_assessment', assessment_id=assessment.id))

        review_action = (request.form.get('review_action') or '').lower()
        doctor_report = (request.form.get('doctor_report') or '').strip()

        if review_action not in ('approved', 'rejected'):
            flash('Please choose whether to approve or reject the assessment.', 'error')
            return redirect(url_for('doctor.view_assessment', assessment_id=assessment.id))

        if review_action == 'rejected' and not doctor_report:
            flash('Please write a report before submitting a rejection.', 'error')
            return redirect(url_for('doctor.view_assessment', assessment_id=assessment.id))

        assessment.review_status = review_action
        if doctor_report:
            assessment.doctor_report = doctor_report
        assessment.reviewed_at = datetime.utcnow()
        assessment.reviewed_by_id = user.id
        assessment.validation_status = 'reviewed'
        db.session.commit()

        flash('Assessment review saved successfully.', 'success')
        return redirect(url_for('doctor.view_assessment', assessment_id=assessment.id))
    
    return render_template('assessment_results.html', assessment=assessment, patient=patient, user=user)

# -----------------------------------------  
# Dashboard redirect (for sidebar navigation)
@doctor_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    return redirect(url_for('doctor.doctor_dashboard'))

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
    alerts_list = []
    unread_alert_count = 0
    
    try:
        alerts_list = _alert_query_for_user(user).order_by(Alert.created_at.desc()).all()
        unread_alert_count = _unread_alert_count_for_user(user)
    except:
        alerts_list = []

    return render_template('alerts.html', user=user, alerts=alerts_list, unread_alert_count=unread_alert_count)

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
    if not user:
        session.clear()
        return redirect(url_for('doctor.login'))

    user_settings = UserSettings.query.filter_by(user_id=user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=user.id)
        db.session.add(user_settings)
        db.session.commit()

    unread_alert_count = _unread_alert_count_for_user(user)

    return render_template(
        'settings.html',
        user=user,
        settings=user_settings,
        unread_alert_count=unread_alert_count
    )

