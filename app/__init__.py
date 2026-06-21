from flask import Flask, g, request, session
from flask_babel import Babel, get_locale
from app.models import db
from sqlalchemy import inspect, text

def get_locale():
    return session.get('lang', 'en')


def _ensure_ecg_review_schema():
    inspector = inspect(db.engine)
    try:
        ecg_columns = {column['name'] for column in inspector.get_columns('ecg_records')}
    except Exception:
        return

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
        db.session.execute(text(statement))

    if alter_statements:
        db.session.commit()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/ECGproject'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 60,
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'ar']

    babel = Babel(app, locale_selector=get_locale)
    db.init_app(app)

    with app.app_context():
        _ensure_ecg_review_schema()

    @app.context_processor
    def inject_navigation_targets():
        role = session.get('role')
        home_url = '/doctor-dashboard'
        return {
            'home_url': home_url,
            'is_admin_user': role == 'admin',
        }

    from app.doctor.routes import doctor_bp
    from app.doctor.api_routes import api_bp
    from app.doctor.settings_alerts_routes import settings_alerts_bp
    app.register_blueprint(doctor_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_alerts_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            db.session.execute('SELECT 1')
            print("Database connection successful.")
            users = db.session.query(db.Model.metadata.tables['users']).all()
            print("User table rows:")
            for user in users:
                print(user)
        except Exception as e:
            print(f"Database connection failed: {e}")