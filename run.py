"""
HEARTGAURD - AI Heart Monitoring Platform
Main entry point to run the Flask application
"""

from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
