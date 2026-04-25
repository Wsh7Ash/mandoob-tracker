"""
API routes for Mandoob Tracker.

This module defines all API endpoints for monitoring
government services in KSA and Qatar.
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import logging

from models.database import Service, ServiceCheck, ServiceAlert, User, ServiceMetrics
from extensions import db, REQUEST_COUNT, REQUEST_DURATION, ACTIVE_CHECKS, SERVICE_STATUS

# Create API blueprint
api_bp = Blueprint('api', __name__)

@api_bp.before_request
def before_request():
    """Log request metrics."""
    REQUEST_COUNT.labels(method=request.method, endpoint=request.endpoint).inc()

@api_bp.after_request
def after_request(response):
    """Log request duration."""
    REQUEST_DURATION.observe(response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0)
    return response

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check Redis connection
        from extensions import redis_client
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': 'healthy',
                'redis': 'healthy'
            }
        })
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@api_bp.route('/services', methods=['GET'])
def get_services():
    """Get all monitored services."""
    try:
        # Query parameters
        country = request.args.get('country')
        category = request.args.get('category')
        is_active = request.args.get('is_active', type=bool)
        
        # Build query
        query = Service.query
        
        if country:
            query = query.filter(Service.country == country)
        if category:
            query = query.filter(Service.category == category)
        if is_active is not None:
            query = query.filter(Service.is_active == is_active)
        
        services = query.all()
        
        return jsonify({
            'services': [
                {
                    'id': str(service.id),
                    'name': service.name,
                    'country': service.country,
                    'category': service.category,
                    'url': service.url,
                    'description': service.description,
                    'is_active': service.is_active,
                    'is_critical': service.is_critical,
                    'check_interval': service.check_interval,
                    'created_at': service.created_at.isoformat(),
                    'updated_at': service.updated_at.isoformat()
                }
                for service in services
            ],
            'total': len(services)
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_services: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/services/<service_id>/checks', methods=['GET'])
def get_service_checks(service_id):
    """Get recent checks for a specific service."""
    try:
        # Query parameters
        limit = request.args.get('limit', 100, type=int)
        hours = request.args.get('hours', 24, type=int)
        
        # Calculate time range
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Query checks
        checks = ServiceCheck.query.filter(
            ServiceCheck.service_id == service_id,
            ServiceCheck.checked_at >= since
        ).order_by(ServiceCheck.checked_at.desc()).limit(limit).all()
        
        return jsonify({
            'service_id': service_id,
            'checks': [
                {
                    'id': str(check.id),
                    'status_code': check.status_code,
                    'response_time': check.response_time,
                    'is_available': check.is_available,
                    'error_message': check.error_message,
                    'ssl_valid': check.ssl_valid,
                    'ssl_expires': check.ssl_expires.isoformat() if check.ssl_expires else None,
                    'check_type': check.check_type,
                    'checked_at': check.checked_at.isoformat()
                }
                for check in checks
            ],
            'total': len(checks)
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_service_checks: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/services/<service_id>/status', methods=['GET'])
def get_service_status(service_id):
    """Get current status of a specific service."""
    try:
        # Get service and latest check
        service = Service.query.get(service_id)
        if not service:
            return jsonify({'error': 'Service not found'}), 404
        
        latest_check = ServiceCheck.query.filter(
            ServiceCheck.service_id == service_id
        ).order_by(ServiceCheck.checked_at.desc()).first()
        
        # Get active alerts
        active_alerts = ServiceAlert.query.filter(
            ServiceAlert.service_id == service_id,
            ServiceAlert.is_active == True
        ).all()
        
        # Calculate uptime (last 24 hours)
        since = datetime.utcnow() - timedelta(hours=24)
        checks_24h = ServiceCheck.query.filter(
            ServiceCheck.service_id == service_id,
            ServiceCheck.checked_at >= since
        ).all()
        
        uptime = 0
        if checks_24h:
            successful_checks = sum(1 for check in checks_24h if check.is_available)
            uptime = (successful_checks / len(checks_24h)) * 100
        
        return jsonify({
            'service': {
                'id': str(service.id),
                'name': service.name,
                'country': service.country,
                'category': service.category,
                'url': service.url,
                'is_critical': service.is_critical
            },
            'current_status': {
                'is_available': latest_check.is_available if latest_check else False,
                'status_code': latest_check.status_code if latest_check else None,
                'response_time': latest_check.response_time if latest_check else None,
                'ssl_valid': latest_check.ssl_valid if latest_check else None,
                'last_check': latest_check.checked_at.isoformat() if latest_check else None
            },
            'uptime_24h': round(uptime, 2),
            'active_alerts': [
                {
                    'id': str(alert.id),
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'started_at': alert.started_at.isoformat(),
                    'is_acknowledged': alert.is_acknowledged
                }
                for alert in active_alerts
            ]
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_service_status: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get all active alerts."""
    try:
        # Query parameters
        severity = request.args.get('severity')
        country = request.args.get('country')
        limit = request.args.get('limit', 50, type=int)
        
        # Build query
        query = ServiceAlert.query.filter(ServiceAlert.is_active == True)
        
        if severity:
            query = query.filter(ServiceAlert.severity == severity)
        if country:
            query = query.join(Service).filter(Service.country == country)
        
        alerts = query.order_by(ServiceAlert.started_at.desc()).limit(limit).all()
        
        return jsonify({
            'alerts': [
                {
                    'id': str(alert.id),
                    'service_id': str(alert.service_id),
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'started_at': alert.started_at.isoformat(),
                    'is_acknowledged': alert.is_acknowledged,
                    'acknowledged_by': alert.acknowledged_by,
                    'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    'metadata': alert.metadata
                }
                for alert in alerts
            ],
            'total': len(alerts)
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_alerts: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """Get system metrics."""
    try:
        # Query parameters
        period = request.args.get('period', '24h')  # 1h, 24h, 7d, 30d
        
        # Calculate time range
        if period == '1h':
            since = datetime.utcnow() - timedelta(hours=1)
        elif period == '24h':
            since = datetime.utcnow() - timedelta(hours=24)
        elif period == '7d':
            since = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            since = datetime.utcnow() - timedelta(days=30)
        else:
            since = datetime.utcnow() - timedelta(hours=24)
        
        # Get metrics for all services
        services = Service.query.filter(Service.is_active == True).all()
        service_metrics = []
        
        for service in services:
            # Get checks in period
            checks = ServiceCheck.query.filter(
                ServiceCheck.service_id == service.id,
                ServiceCheck.checked_at >= since
            ).all()
            
            if checks:
                successful_checks = sum(1 for check in checks if check.is_available)
                uptime = (successful_checks / len(checks)) * 100
                avg_response = sum(check.response_time or 0 for check in checks) / len(checks)
                
                service_metrics.append({
                    'service_id': str(service.id),
                    'service_name': service.name,
                    'country': service.country,
                    'category': service.category,
                    'uptime_percentage': round(uptime, 2),
                    'total_checks': len(checks),
                    'successful_checks': successful_checks,
                    'avg_response_time': round(avg_response, 2),
                    'min_response_time': min(check.response_time or 0 for check in checks),
                    'max_response_time': max(check.response_time or 0 for check in checks)
                })
        
        # Overall statistics
        total_services = len(services)
        total_checks = sum(metric['total_checks'] for metric in service_metrics)
        total_successful = sum(metric['successful_checks'] for metric in service_metrics)
        overall_uptime = (total_successful / total_checks * 100) if total_checks > 0 else 0
        
        return jsonify({
            'period': period,
            'from_date': since.isoformat(),
            'to_date': datetime.utcnow().isoformat(),
            'overall': {
                'total_services': total_services,
                'total_checks': total_checks,
                'overall_uptime': round(overall_uptime, 2),
                'avg_response_time': round(
                    sum(metric['avg_response_time'] for metric in service_metrics) / len(service_metrics) if service_metrics else 0, 2
                )
            },
            'services': service_metrics
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_metrics: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """Get overall system status."""
    try:
        # Get latest system status for each component
        from models.database import SystemStatus
        
        components = ['monitor', 'database', 'redis', 'api']
        system_status = {}
        
        for component in components:
            status = SystemStatus.query.filter(
                SystemStatus.component == component
            ).order_by(SystemStatus.last_check.desc()).first()
            
            if status:
                system_status[component] = {
                    'status': status.status,
                    'message': status.message,
                    'response_time': status.response_time,
                    'error_rate': status.error_rate,
                    'last_check': status.last_check.isoformat()
                }
        
        # Calculate overall status
        all_healthy = all(
            component_status['status'] == 'healthy' 
            for component_status in system_status.values()
        )
        
        overall_status = 'healthy' if all_healthy else 'degraded'
        
        return jsonify({
            'overall_status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': system_status
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_system_status: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/countries', methods=['GET'])
def get_countries():
    """Get list of monitored countries."""
    try:
        # Get unique countries from services
        countries = db.session.query(Service.country).distinct().all()
        
        return jsonify({
            'countries': [country[0] for country in countries],
            'total': len(countries)
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_countries: {e}")
        return jsonify({'error': 'Database error'}), 500

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get list of service categories."""
    try:
        # Get unique categories from services
        categories = db.session.query(Service.category).distinct().all()
        
        return jsonify({
            'categories': [category[0] for category in categories],
            'total': len(categories)
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_categories: {e}")
        return jsonify({'error': 'Database error'}), 500

# Error handlers
@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    current_app.logger.error(f"API internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@api_bp.errorhandler(400)
def api_bad_request(error):
    """Handle 400 errors."""
    return jsonify({'error': 'Bad request'}), 400
