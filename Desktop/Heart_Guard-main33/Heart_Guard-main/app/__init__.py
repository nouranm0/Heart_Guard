import os
import urllib.parse

from flask import Flask, g, request, session
from flask_babel import Babel
from app.models import db

def select_locale():
    return session.get('lang', 'en')


def get_database_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        return uri

    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'M2004#')
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_db = os.environ.get('MYSQL_DATABASE', 'ECGproject')
    encoded_password = urllib.parse.quote_plus(mysql_password)
    return f'mysql+pymysql://{mysql_user}:{encoded_password}@{mysql_host}/{mysql_db}'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'ar']

    babel = Babel(app, locale_selector=select_locale)
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