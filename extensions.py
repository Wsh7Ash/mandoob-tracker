"""
Flask extensions initialization for Mandoob Tracker.

This module initializes and configures all Flask extensions
used throughout the application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery
import redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

# Database
db = SQLAlchemy()
migrate = Migrate()

# Celery for background tasks
def make_celery(app):
    """Create Celery instance with Flask app context."""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Riyadh',
        enable_utc=True,
        beat_schedule={
            'check-services': {
                'task': 'mandoob_tracker.monitor.check_all_services',
                'schedule': 300.0,  # Every 5 minutes
            },
            'cleanup-old-data': {
                'task': 'mandoob_tracker.monitor.cleanup_old_data',
                'schedule': 3600.0,  # Every hour
            },
        }
    )
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Redis connection
redis_client = None

def init_redis(app):
    """Initialize Redis client."""
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'])
    return redis_client

# Prometheus metrics
REQUEST_COUNT = Counter('mandoob_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('mandoob_request_duration_seconds', 'Request duration')
ACTIVE_CHECKS = Gauge('mandoob_active_checks', 'Number of active service checks')
SERVICE_STATUS = Gauge('mandoob_service_status', 'Service status', ['service', 'country'])

def start_metrics_server(port=8000):
    """Start Prometheus metrics server."""
    try:
        start_http_server(port)
        logging.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logging.error(f"Failed to start metrics server: {e}")

# Logging configuration
def setup_logging(app):
    """Setup application logging."""
    if not app.debug:
        # Production logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Create logs directory
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Setup file handler
        file_handler = RotatingFileHandler(
            'logs/mandoob_tracker.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        # Setup error handler
        error_handler = RotatingFileHandler(
            'logs/mandoob_tracker_errors.log',
            maxBytes=10240000,
            backupCount=10
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        error_handler.setLevel(logging.ERROR)
        
        app.logger.addHandler(file_handler)
        app.logger.addHandler(error_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Mandoob Tracker startup')
