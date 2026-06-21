from flask import Flask, g, request, session
from flask_babel import Babel, get_locale
from app.models import db

def get_locale():
    return session.get('lang', 'en')

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/ECGproject'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'ar']

    babel = Babel(app, locale_selector=get_locale)
    db.init_app(app)

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