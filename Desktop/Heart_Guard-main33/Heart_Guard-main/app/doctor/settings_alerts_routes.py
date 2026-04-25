# Settings and Alerts API Routes
# API endpoints for user settings and alerts management

from flask import Blueprint, request, session, jsonify
from app.models import db, UserSettings, Alert, User, Patient
from datetime import datetime
from sqlalchemy import desc

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
        'email_notifications': settings.email_notifications,
        'push_notifications': settings.push_notifications,
        'sms_notifications': settings.sms_notifications,
        'dark_mode': settings.dark_mode,
        'language': settings.language,
        'first_name': settings.first_name or '',
        'last_name': settings.last_name or '',
        'phone': settings.phone or '',
        'date_of_birth': settings.date_of_birth.isoformat() if settings.date_of_birth else None,
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
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.session.add(settings)
        
        # Update notification preferences
        if 'email_notifications' in data:
            settings.email_notifications = data.get('email_notifications') in [True, 'true', '1', 1]
        if 'push_notifications' in data:
            settings.push_notifications = data.get('push_notifications') in [True, 'true', '1', 1]
        if 'sms_notifications' in data:
            settings.sms_notifications = data.get('sms_notifications') in [True, 'true', '1', 1]
        
        # Update appearance settings
        if 'dark_mode' in data:
            settings.dark_mode = data.get('dark_mode') in [True, 'true', '1', 1]
        if 'language' in data:
            settings.language = data.get('language')
        
        # Update profile info
        if 'first_name' in data:
            settings.first_name = data.get('first_name')
        if 'last_name' in data:
            settings.last_name = data.get('last_name')
        if 'phone' in data:
            settings.phone = data.get('phone')
        if 'date_of_birth' in data:
            try:
                dob_str = data.get('date_of_birth')
                if dob_str:
                    settings.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                print(f"[UPDATE SETTINGS] Error parsing date: {e}")
                pass
        
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"[UPDATE SETTINGS] Settings updated successfully for user {user_id}")
        
        return {
            'success': True,
            'message': 'Settings updated successfully',
            'settings': {
                'email_notifications': settings.email_notifications,
                'push_notifications': settings.push_notifications,
                'sms_notifications': settings.sms_notifications,
                'dark_mode': settings.dark_mode,
                'language': settings.language,
                'first_name': settings.first_name,
                'last_name': settings.last_name,
                'phone': settings.phone,
                'date_of_birth': settings.date_of_birth.isoformat() if settings.date_of_birth else None
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
    is_read = request.args.get('is_read')  # 'true', 'false', or None for all
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    print(f"[GET ALERTS] User ID: {user_id}, is_read: {is_read}, limit: {limit}, offset: {offset}")
    
    alerts_query = Alert.query.filter_by(user_id=user_id)
    
    if is_read == 'true':
        alerts_query = alerts_query.filter_by(is_read=True)
    elif is_read == 'false':
        alerts_query = alerts_query.filter_by(is_read=False)
    
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
        'returned': len(alerts)
    }, 200


@settings_alerts_bp.route('/alerts/<int:alert_id>/read', methods=['PUT', 'POST'])
def mark_alert_read(alert_id):
    """Mark alert as read"""
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not authenticated'}, 401
    
    user_id = session['user_id']
    
    print(f"[MARK ALERT READ] User ID: {user_id}, Alert ID: {alert_id}")
    
    try:
        alert = Alert.query.get(alert_id)
        
        if not alert:
            print(f"[MARK ALERT READ] Alert {alert_id} not found")
            return {'success': False, 'message': 'Alert not found'}, 404
        
        if alert.user_id != user_id:
            print(f"[MARK ALERT READ] Access denied: alert belongs to user {alert.user_id}")
            return {'success': False, 'message': 'Access denied'}, 403
        
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
    
    print(f"[MARK ALL ALERTS READ] User ID: {user_id}")
    
    try:
        unread_count = Alert.query.filter_by(user_id=user_id, is_read=False).count()
        
        Alert.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
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
    
    print(f"[DELETE ALERT] User ID: {user_id}, Alert ID: {alert_id}")
    
    try:
        alert = Alert.query.get(alert_id)
        
        if not alert:
            print(f"[DELETE ALERT] Alert {alert_id} not found")
            return {'success': False, 'message': 'Alert not found'}, 404
        
        if alert.user_id != user_id:
            print(f"[DELETE ALERT] Access denied: alert belongs to user {alert.user_id}")
            return {'success': False, 'message': 'Access denied'}, 403
        
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
    
    unread_count = Alert.query.filter_by(user_id=user_id, is_read=False).count()
    total_count = Alert.query.filter_by(user_id=user_id).count()
    
    print(f"[ALERTS COUNT] User ID: {user_id}, Unread: {unread_count}, Total: {total_count}")
    
    return {
        'success': True,
        'unread': unread_count,
        'total': total_count
    }, 200


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
