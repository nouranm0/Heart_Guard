"""
HEARTGAURD - AI Heart Monitoring Platform
Main entry point to run the Flask application
"""

from app import create_app

if __name__ == '__main__':
    app = create_app()
    # Test database connection and print users
    # with app.app_context():
    #     from app.models import db, User
    #     from sqlalchemy import text
    #     try:
    #         db.session.execute(text('SELECT 1'))
    #         print("Database connection successful.")
    #         users = User.query.all()
    #         print("User table rows:")
    #         for user in users:
    #             print(f"ID:{user.id}, Username:{user.username}, Email:{user.email}, Role:{user.role}, Active:{user.is_active}, Password Hash: {user.password_hash}")
    #     except Exception as e:
    #         print(f"Database connection failed: {e}")
    app.run(debug=True, host='0.0.0.0', port=3000)

