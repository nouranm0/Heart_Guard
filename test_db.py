#!/usr/bin/env python3
"""
Test script to verify the new Alert and UserSettings models work correctly
"""

from app import create_app, db
from app.models import Alert, UserSettings, User, Patient

def test_database_setup():
    """Test that the database tables are created and models work"""
    app = create_app()

    with app.app_context():
        # Test that tables exist
        try:
            # Check if tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            required_tables = ['alerts', 'user_settings', 'users', 'patients', 'ecg_records']
            missing_tables = [table for table in required_tables if table not in tables]

            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All required tables exist")

            # Test creating sample data
            # First, check if we have a test user
            test_user = User.query.filter_by(email='test@example.com').first()
            if not test_user:
                test_user = User(
                    name='Test Doctor',
                    email='test@example.com',
                    password='hashed_password',
                    role='doctor'
                )
                db.session.add(test_user)
                db.session.commit()
                print("✅ Created test user")

            # Test UserSettings
            settings = UserSettings.query.filter_by(user_id=test_user.id).first()
            if not settings:
                settings = UserSettings(
                    user_id=test_user.id,
                    email_notifications=True,
                    sms_notifications=False,
                    dark_mode=False,
                    language='en'
                )
                db.session.add(settings)
                db.session.commit()
                print("✅ Created user settings")

            # Test Alert creation
            alert = Alert(
                user_id=test_user.id,
                patient_id=None,  # System alert
                alert_type='info',
                title='Test Alert',
                message='This is a test alert to verify the system works',
                is_read=False
            )
            db.session.add(alert)
            db.session.commit()
            print("✅ Created test alert")

            # Test querying
            alerts = Alert.query.filter_by(user_id=test_user.id).all()
            settings = UserSettings.query.filter_by(user_id=test_user.id).first()

            print(f"✅ Found {len(alerts)} alerts for user")
            print(f"✅ User settings: email_notifications={settings.email_notifications}, dark_mode={settings.dark_mode}")

            print("\n🎉 All database tests passed!")
            return True

        except Exception as e:
            print(f"❌ Database test failed: {e}")
            return False

if __name__ == '__main__':
    test_database_setup()