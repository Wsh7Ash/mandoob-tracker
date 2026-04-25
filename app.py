"""
Flask web application for KSA/QA Mandoob Tracker

This is the main Flask application that provides web interface
for monitoring government service availability in KSA and Qatar.
"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(config_name='development'):
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///mandoob_tracker.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize extensions
    from .extensions import db, migrate, celery
    db.init_app(app)
    migrate.init_app(app, db)
    celery.init_app(app)
    
    # Register blueprints
    from .api import api_bp
    from .web import web_bp
    
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request'}, 400
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
