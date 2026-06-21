# Settings and Alerts API Routes
# API endpoints for user settings and alerts management

import json
import time

from flask import Blueprint, request, session, jsonify, Response, stream_with_context
from app.models import db, UserSettings, Alert, User, Patient
from app.validation_utils import normalize_email, validate_email, validate_password_strength
from datetime import datetime
from sqlalchemy import desc, or_, select, func


def _accessible_alert_query(user):
    query = Alert.query
    if user and user.role != 'admin':
        patient_ids = [patient.id for patient in user.patients]
        query = query.filter(or_(Alert.user_id == user.id, Alert.patient_id.in_(patient_ids)))
    return query

# Create blueprint
settings_alerts_bp = Blueprint('settings_alerts', __name__, url_prefix='/api')

# ==============================================
# SETTINGS ENDPOINTS
# ==============================================

@settings_alerts_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get user settings"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    print(f"[GET SETTINGS] User ID: {user_id}")

    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'message': 'User not found'}, 404
    
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    
    if not settings:
        # Create default settings if not exist
        print(f"[GET SETTINGS] Creating default settings for user {user_id}")
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)
        db.session.commit()
    
    settings_data = {
        'id': settings.id,
        'user_id': settings.user_id,
        'email': user.email,
        'dark_mode': settings.dark_mode,
        'language': settings.language,
        'first_name': settings.first_name or '',
        'last_name': settings.last_name or '',
        'created_at': settings.created_at.isoformat(),
        'updated_at': settings.updated_at.isoformat()
    }
    
    print(f"[GET SETTINGS] Returning settings: {settings_data}")
    return {'success': True, 'settings': settings_data}, 200


@settings_alerts_bp.route('/settings', methods=['PUT', 'POST'])
def update_settings():
    """Update user settings"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    data = request.get_json() or request.form
    
    print(f"[UPDATE SETTINGS] User ID: {user_id}, Data: {data}")
    
    try:
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.session.add(settings)

        if not user:
            return {'success': False, 'message': 'User not found'}, 404

        email = normalize_email(data.get('email')) if data.get('email') is not None else None
        current_password = data.get('current_password') or ''
        new_password = data.get('new_password') or ''
        confirm_password = data.get('confirm_password') or ''
        if email:
            if not validate_email(email):
                return {'success': False, 'message': 'Please enter a valid email address'}, 400

            existing_user = User.query.filter(db.func.lower(User.email) == email, User.id != user_id).first()
            if existing_user:
                return {'success': False, 'message': 'Email already exists'}, 400

            user.email = email

        if current_password or new_password or confirm_password:
            if not current_password or not new_password or not confirm_password:
                return {'success': False, 'message': 'Please complete the password change fields'}, 400
            if not user.check_password(current_password):
                return {'success': False, 'message': 'Current password is incorrect'}, 400
            if new_password != confirm_password:
                return {'success': False, 'message': 'New password and confirmation do not match'}, 400

            password_ok, password_message = validate_password_strength(new_password)
            if not password_ok:
                return {'success': False, 'message': password_message}, 400

            user.set_password(new_password)
        
        # Update appearance settings
        if 'dark_mode' in data:
            settings.dark_mode = data.get('dark_mode') in [True, 'true', '1', 1]
        if 'language' in data:
            language = data.get('language')
            if language not in ['en', 'ar']:
                language = 'en'
            settings.language = language
            session['lang'] = language
        
        # Update profile info
        if 'first_name' in data:
            settings.first_name = data.get('first_name')
        if 'last_name' in data:
            settings.last_name = data.get('last_name')
        
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"[UPDATE SETTINGS] Settings updated successfully for user {user_id}")
        
        return {
            'success': True,
            'message': 'Settings updated successfully',
            'settings': {
                'dark_mode': settings.dark_mode,
                'language': settings.language,
                'email': user.email,
                'first_name': settings.first_name,
                'last_name': settings.last_name,
            }
        }, 200
    
    except Exception as e:
        db.session.rollback()
        print(f"[UPDATE SETTINGS] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Error: {str(e)}'}, 500


# ==============================================
# ALERTS ENDPOINTS
# ==============================================

@settings_alerts_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get alerts for current user"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'message': 'User not found'}, 404
    is_read = request.args.get('is_read')  # 'true', 'false', or None for all
    alert_type = request.args.get('type', 'all').lower()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    print(f"[GET ALERTS] User ID: {user_id}, is_read: {is_read}, type: {alert_type}, limit: {limit}, offset: {offset}")
    
    alerts_query = _accessible_alert_query(user)
    
    if is_read == 'true':
        alerts_query = alerts_query.filter_by(is_read=True)
    elif is_read == 'false':
        alerts_query = alerts_query.filter_by(is_read=False)

    type_counts = {
        'all': alerts_query.count(),
        'critical': alerts_query.filter_by(alert_type='critical').count(),
        'warning': alerts_query.filter_by(alert_type='warning').count(),
        'info': alerts_query.filter_by(alert_type='info').count(),
    }

    if alert_type in ('critical', 'warning', 'info'):
        alerts_query = alerts_query.filter_by(alert_type=alert_type)
    
    total_count = alerts_query.count()
    alerts = alerts_query.order_by(desc(Alert.created_at)).limit(limit).offset(offset).all()
    
    alerts_data = []
    for alert in alerts:
        patient_name = alert.patient.name if alert.patient else 'Unknown'
        alerts_data.append({
            'id': alert.id,
            'user_id': alert.user_id,
            'patient_id': alert.patient_id,
            'patient_name': patient_name,
            'alert_type': alert.alert_type,
            'title': alert.title,
            'message': alert.message,
            'is_read': alert.is_read,
            'created_at': alert.created_at.isoformat()
        })
    
    print(f"[GET ALERTS] Found {len(alerts)} alerts (total: {total_count})")
    
    return {
        'success': True,
        'alerts': alerts_data,
        'total': total_count,
        'returned': len(alerts),
        'type_counts': type_counts,
    }, 200


@settings_alerts_bp.route('/alerts/<int:alert_id>/read', methods=['PUT', 'POST'])
def mark_alert_read(alert_id):
    """Mark alert as read"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    print(f"[MARK ALERT READ] User ID: {user_id}, Alert ID: {alert_id}")
    
    try:
        alert = _accessible_alert_query(user).filter_by(id=alert_id).first() if user else None
        
        if not alert:
            print(f"[MARK ALERT READ] Alert {alert_id} not found")
            return {'success': False, 'message': 'Alert not found'}, 404
        
        alert.is_read = True
        db.session.commit()
        
        print(f"[MARK ALERT READ] Alert {alert_id} marked as read")
        
        return {'success': True, 'message': 'Alert marked as read'}, 200
    
    except Exception as e:
        db.session.rollback()
        print(f"[MARK ALERT READ] ERROR: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}, 500


@settings_alerts_bp.route('/alerts/read-all', methods=['PUT', 'POST'])
def mark_all_alerts_read():
    """Mark all alerts as read"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    print(f"[MARK ALL ALERTS READ] User ID: {user_id}")
    
    try:
        alerts_query = _accessible_alert_query(user) if user else Alert.query.filter_by(user_id=user_id)
        unread_count = alerts_query.filter_by(is_read=False).count()
        
        alerts_query.filter_by(is_read=False).update({'is_read': True})
        db.session.commit()
        
        print(f"[MARK ALL ALERTS READ] Marked {unread_count} alerts as read")
        
        return {
            'success': True,
            'message': f'Marked {unread_count} alerts as read',
            'count': unread_count
        }, 200
    
    except Exception as e:
        db.session.rollback()
        print(f"[MARK ALL ALERTS READ] ERROR: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}, 500


@settings_alerts_bp.route('/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Delete an alert"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    print(f"[DELETE ALERT] User ID: {user_id}, Alert ID: {alert_id}")
    
    try:
        alert = _accessible_alert_query(user).filter_by(id=alert_id).first() if user else None
        
        if not alert:
            print(f"[DELETE ALERT] Alert {alert_id} not found")
            return {'success': False, 'message': 'Alert not found'}, 404
        
        db.session.delete(alert)
        db.session.commit()
        
        print(f"[DELETE ALERT] Alert {alert_id} deleted successfully")
        
        return {'success': True, 'message': 'Alert deleted successfully'}, 200
    
    except Exception as e:
        db.session.rollback()
        print(f"[DELETE ALERT] ERROR: {str(e)}")
        return {'success': False, 'message': f'Error: {str(e)}'}, 500


@settings_alerts_bp.route('/alerts/count', methods=['GET'])
def get_alerts_count():
    """Get count of unread alerts"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    alert_query = _accessible_alert_query(user) if user else Alert.query.filter_by(user_id=user_id)

    unread_count = alert_query.filter_by(is_read=False).count()
    total_count = alert_query.count()
    
    print(f"[ALERTS COUNT] User ID: {user_id}, Unread: {unread_count}, Total: {total_count}")
    
    return {
        'success': True,
        'unread': unread_count,
        'total': total_count
    }, 200


@settings_alerts_bp.route('/alerts/stream', methods=['GET'])
def stream_alerts():
    """Stream unread alert count updates for the active user."""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401

    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'message': 'User not found'}, 404

    @stream_with_context
    def event_stream():
        last_snapshot = None

        while True:
            try:
                with db.engine.connect() as connection:
                    current_role = connection.execute(
                        select(User.role).where(User.id == user_id)
                    ).scalar_one_or_none()

                    if current_role is None:
                        break

                    alert_filter = Alert.user_id == user_id
                    if current_role != 'admin':
                        patient_ids = [
                            row[0]
                            for row in connection.execute(
                                select(Patient.id).where(Patient.doctor_id == user_id)
                            ).all()
                        ]
                        if patient_ids:
                            alert_filter = or_(Alert.user_id == user_id, Alert.patient_id.in_(patient_ids))

                    unread_count = connection.execute(
                        select(func.count()).select_from(Alert).where(alert_filter, Alert.is_read.is_(False))
                    ).scalar_one()
                    total_count = connection.execute(
                        select(func.count()).select_from(Alert).where(alert_filter)
                    ).scalar_one()
                    latest_alert = connection.execute(
                        select(Alert.id, Alert.created_at)
                        .where(alert_filter)
                        .order_by(desc(Alert.created_at))
                        .limit(1)
                    ).first()

                latest_marker = latest_alert.created_at.isoformat() if latest_alert and latest_alert.created_at else ''
                snapshot = (unread_count, total_count, latest_marker)

                if snapshot != last_snapshot:
                    payload = {
                        'unread': unread_count,
                        'total': total_count,
                        'latest_alert_id': latest_alert.id if latest_alert else None,
                        'latest_alert_created_at': latest_marker,
                    }
                    yield f"event: alert-update\ndata: {json.dumps(payload)}\n\n"
                    last_snapshot = snapshot

            except Exception:
                break

            time.sleep(5)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ==============================================
# ADMIN: CREATE ALERT FOR DOCTOR/USER
# ==============================================

@settings_alerts_bp.route('/alerts/create', methods=['POST'])
def create_alert():
    """Create a new alert (Admin/Doctor only)"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user = User.query.get(session['user_id'])
    if user.role not in ['admin', 'doctor']:
        return {'success': False, 'message': 'Access denied'}, 403
    
    try:
        data = request.get_json() or request.form
        
        target_user_id = data.get('target_user_id')
        if target_user_id:
            target_user_id = int(target_user_id)
        
        patient_id = data.get('patient_id')
        if patient_id:
            patient_id = int(patient_id)
        alert_type = data.get('alert_type', 'info')  # critical, warning, info
        title = data.get('title')
        message = data.get('message')
        
        print(f"[CREATE ALERT] From: {session['user_id']}, Target: {target_user_id}, Type: {alert_type}")
        
        if not target_user_id or not title or not message:
            return {'success': False, 'message': 'Missing required fields'}, 400
        
        if alert_type not in ['critical', 'warning', 'info']:
            alert_type = 'info'
        
        # Verify target user exists
        target_user = User.query.get(target_user_id)
        if not target_user:
            return {'success': False, 'message': 'Target user not found'}, 404
        
        alert = Alert(
            user_id=target_user_id,
            patient_id=patient_id,
            alert_type=alert_type,
            title=title,
            message=message
        )
        
        db.session.add(alert)
        db.session.commit()
        
        print(f"[CREATE ALERT] Alert created successfully (ID: {alert.id})")
        
        return {
            'success': True,
            'message': 'Alert created successfully',
            'alert': {
                'id': alert.id,
                'user_id': alert.user_id,
                'patient_id': alert.patient_id,
                'alert_type': alert.alert_type,
                'title': alert.title,
                'message': alert.message,
                'is_read': alert.is_read,
                'created_at': alert.created_at.isoformat()
            }
        }, 201
    
    except Exception as e:
        db.session.rollback()
        print(f"[CREATE ALERT] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Error: {str(e)}'}, 500
