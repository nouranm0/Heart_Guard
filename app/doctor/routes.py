"""
HEARTGAURD Doctor Routes
Handles all doctor dashboard and navigation routes
"""

from flask import Blueprint, render_template

doctor_bp = Blueprint('doctor', __name__)


@doctor_bp.route('/')
def splash():
    """Splash screen - auto redirects to intro"""
    return render_template('splash.html')


@doctor_bp.route('/intro')
def intro():
    """Introduction page - project overview"""
    return render_template('intro.html')


@doctor_bp.route('/patient-dashboard')
def patient_dashboard():
    """Patient monitoring dashboard - Initial patient view"""
    patient_data = {
        'name': 'Ahmed Hassan',
        'age': 45,
        'gender': 'Male',
        'heart_rate': 72,
        'systolic': 120,
        'diastolic': 80,
        'temperature': 98.6,
        'respiration': 16,
        'risk_level': 'low',
        'ecg_status': 'normal',
        'last_assessment': '2 hours ago'
    }
    return render_template('patient_dashboard.html', patient=patient_data)


@doctor_bp.route('/dashboard')
def dashboard():
    """Patient monitoring dashboard"""
    patient_data = {
        'name': 'Ahmed Hassan',
        'age': 45,
        'gender': 'Male',
        'heart_rate': 72,
        'systolic': 120,
        'diastolic': 80,
        'temperature': 98.6,
        'respiration': 16,
        'risk_level': 'low',
        'ecg_status': 'normal',
        'last_assessment': '2 hours ago'
    }
    return render_template('dashboard.html', patient=patient_data)


@doctor_bp.route('/doctor-dashboard')
def doctor_dashboard():
    """Main doctor dashboard - Doctor's view"""
    patient_data = {
        'name': 'Dr. Ahmed Hassan',
        'patients_monitored': 12,
        'high_risk_alerts': 2,
        'current_patient': {
            'id': 'P-2401-001',
            'name': 'Fatima Al-Mansoori',
            'age': 58,
            'gender': 'Female',
            'heart_rate': 78,
            'systolic': 128,
            'diastolic': 82,
            'respiration': 18,
            'temperature': 37.2,
            'risk_level': 'medium',
            'ecg_status': 'normal',
            'last_update': '2:34 PM'
        }
    }
    return render_template('doctor_dashboard.html', patient_data=patient_data)


@doctor_bp.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')


@doctor_bp.route('/alerts')
def alerts():
    """Health alerts and notifications"""
    alerts_data = [
        {
            'id': 1,
            'type': 'critical',
            'title': 'High Heart Rate Detected',
            'message': 'Your heart rate reached 145 bpm at 14:32. Consider resting.',
            'timestamp': '2 hours ago'
        },
        {
            'id': 2,
            'type': 'warning',
            'title': 'Irregular Heart Rhythm Detected',
            'message': 'Possible arrhythmia pattern detected in ECG reading.',
            'timestamp': '5 hours ago'
        },
        {
            'id': 3,
            'type': 'info',
            'title': 'Daily Check-In Reminder',
            'message': 'Don\'t forget to complete your daily health check-in today.',
            'timestamp': '12 hours ago'
        }
    ]
    return render_template('alerts.html', alerts=alerts_data)


@doctor_bp.route('/new-assessment')
def new_assessment():
    """New heart assessment page"""
    return render_template('new_assessment.html')
