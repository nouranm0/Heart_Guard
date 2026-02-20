"""
HEARTGAURD Flask Application Factory
Initialize Flask app and register blueprints
"""

from flask import Flask


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Register doctor blueprint
    from app.doctor.routes import doctor_bp
    app.register_blueprint(doctor_bp)
    
    return app
