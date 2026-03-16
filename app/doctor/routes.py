# app/doctor/routes.py
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import db, User
from werkzeug.security import check_password_hash
import os
from .validation_service import validate_and_predict
from .echonext_service import echonext_predict

doctor_bp = Blueprint('doctor', __name__)
ECHONEXT_MODEL = "model/weights.pt"

# -----------------------------------------
# Splash page -> redirect to login
@doctor_bp.route('/')
def splash_redirect():
    return redirect(url_for('doctor.login'))

# -----------------------------------------
# Login page
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
            return redirect(url_for('doctor.intro'))
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
        flash('Admin access required.', 'error')
        return redirect(url_for('doctor.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'doctor')
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('doctor.add_user'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('doctor.add_user'))
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully.', 'success')
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
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))
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
# New assessment page
@doctor_bp.route('/new-assessment', methods=['GET', 'POST'])
def new_assessment():
    if 'user_id' not in session:
        return redirect(url_for('doctor.login'))

    validation_result = {}
    all_results = []
    top_diagnosis = None
    top_confidence = None

    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return render_template("new_assessment.html")

        ext = file.filename.rsplit(".", 1)[-1].lower()
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(file_path)

        try:
            if ext in ["csv", "pdf", "mat"]:
                validation_result = validate_and_predict(file_path) or {}
                if validation_result.get("prediction"):
                    all_results = [(k, v) for k, v in validation_result["prediction"].items()]
                    top_diagnosis = validation_result.get("top_diagnosis")
                    top_confidence = validation_result.get("top_confidence")

            elif ext == "xml":
                echonext_results = echonext_predict(file_path)
                if echonext_results and echonext_results.get("is_ecg"):
                    all_results = [(k, v) for k, v in echonext_results.get("prediction").items()]

            elif ext in ["jpg", "jpeg", "png", "pdf"]:
                validation_result = validate_and_predict(file_path) or {}
                if validation_result.get("prediction"):
                    all_results = [(k, v) for k, v in validation_result["prediction"].items()]
                    top_diagnosis = validation_result.get("top_diagnosis")
                    top_confidence = validation_result.get("top_confidence")

                echonext_results = echonext_predict(file_path)
                if echonext_results and echonext_results.get("is_ecg"):
                    for k, v in echonext_results.get("prediction").items():
                        all_results.append((f"{k}", v/10))

        except Exception as e:
            print(f"Error in new_assessment: {e}")
            import traceback
            traceback.print_exc()

    return render_template(
        "new_assessment.html",
        results=all_results,
        top_diagnosis=top_diagnosis,
        top_confidence=top_confidence,
        validation=validation_result
    )