"""
Web routes for Mandoob Tracker.

This module defines all web interface routes for the
government service monitoring dashboard.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging

from models.database import Service, ServiceCheck, ServiceAlert, User, ServiceMetrics
from extensions import db

# Create web blueprint
web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Home page with dashboard overview."""
    try:
        # Get system statistics
        total_services = Service.query.filter(Service.is_active == True).count()
        total_checks_today = ServiceCheck.query.filter(
            ServiceCheck.checked_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Get active alerts
        active_alerts = ServiceAlert.query.filter(
            ServiceAlert.is_active == True
        ).count()
        
        # Get recent checks
        recent_checks = ServiceCheck.query.order_by(
            ServiceCheck.checked_at.desc()
        ).limit(10).all()
        
        # Get service status by country
        ksa_services = Service.query.filter(
            Service.country == 'KSA',
            Service.is_active == True
        ).count()
        
        qa_services = Service.query.filter(
            Service.country == 'QA',
            Service.is_active == True
        ).count()
        
        return render_template('index.html', {
            'total_services': total_services,
            'total_checks_today': total_checks_today,
            'active_alerts': active_alerts,
            'recent_checks': recent_checks,
            'ksa_services': ksa_services,
            'qa_services': qa_services
        })
    except Exception as e:
        logging.error(f"Error in index route: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('error.html')

@web_bp.route('/services')
def services():
    """Services listing page."""
    try:
        # Get query parameters
        country = request.args.get('country', '')
        category = request.args.get('category', '')
        
        # Build query
        query = Service.query.filter(Service.is_active == True)
        
        if country:
            query = query.filter(Service.country == country)
        if category:
            query = query.filter(Service.category == category)
        
        services = query.order_by(Service.country, Service.category, Service.name).all()
        
        # Get unique countries and categories for filters
        countries = db.session.query(Service.country).distinct().all()
        categories = db.session.query(Service.category).distinct().all()
        
        return render_template('services.html', {
            'services': services,
            'countries': [c[0] for c in countries],
            'categories': [c[0] for c in categories],
            'selected_country': country,
            'selected_category': category
        })
    except Exception as e:
        logging.error(f"Error in services route: {e}")
        flash('Error loading services', 'error')
        return render_template('error.html')

@web_bp.route('/services/<service_id>')
def service_detail(service_id):
    """Service detail page."""
    try:
        # Get service
        service = Service.query.get(service_id)
        if not service:
            flash('Service not found', 'error')
            return redirect(url_for('web.services'))
        
        # Get recent checks
        recent_checks = ServiceCheck.query.filter(
            ServiceCheck.service_id == service_id
        ).order_by(ServiceCheck.checked_at.desc()).limit(50).all()
        
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
        
        return render_template('service_detail.html', {
            'service': service,
            'recent_checks': recent_checks,
            'active_alerts': active_alerts,
            'uptime_24h': round(uptime, 2)
        })
    except Exception as e:
        logging.error(f"Error in service_detail route: {e}")
        flash('Error loading service details', 'error')
        return render_template('error.html')

@web_bp.route('/alerts')
def alerts():
    """Alerts listing page."""
    try:
        # Get query parameters
        severity = request.args.get('severity', '')
        country = request.args.get('country', '')
        
        # Build query
        query = ServiceAlert.query.filter(ServiceAlert.is_active == True)
        
        if severity:
            query = query.filter(ServiceAlert.severity == severity)
        if country:
            query = query.join(Service).filter(Service.country == country)
        
        alerts = query.order_by(ServiceAlert.started_at.desc()).all()
        
        return render_template('alerts.html', {
            'alerts': alerts,
            'selected_severity': severity,
            'selected_country': country
        })
    except Exception as e:
        logging.error(f"Error in alerts route: {e}")
        flash('Error loading alerts', 'error')
        return render_template('error.html')

@web_bp.route('/metrics')
def metrics():
    """Metrics dashboard page."""
    try:
        # Get query parameters
        period = request.args.get('period', '24h')
        
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
                    'service': service,
                    'uptime_percentage': round(uptime, 2),
                    'total_checks': len(checks),
                    'successful_checks': successful_checks,
                    'avg_response_time': round(avg_response, 2)
                })
        
        # Overall statistics
        total_services = len(services)
        total_checks = sum(metric['total_checks'] for metric in service_metrics)
        total_successful = sum(metric['successful_checks'] for metric in service_metrics)
        overall_uptime = (total_successful / total_checks * 100) if total_checks > 0 else 0
        
        return render_template('metrics.html', {
            'period': period,
            'service_metrics': service_metrics,
            'total_services': total_services,
            'total_checks': total_checks,
            'overall_uptime': round(overall_uptime, 2),
            'avg_response_time': round(
                sum(metric['avg_response_time'] for metric in service_metrics) / len(service_metrics) if service_metrics else 0, 2
            )
        })
    except Exception as e:
        logging.error(f"Error in metrics route: {e}")
        flash('Error loading metrics', 'error')
        return render_template('error.html')

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('login.html')
            
            # Find user
            user = User.query.filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if user and check_password_hash(password, user.password_hash):
                login_user(user)
                flash('Login successful', 'success')
                return redirect(url_for('web.index'))
            else:
                flash('Invalid username or password', 'error')
                
        except Exception as e:
            logging.error(f"Error in login: {e}")
            flash('Login error', 'error')
    
    return render_template('login.html')

@web_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            full_name = request.form.get('full_name', '')
            organization = request.form.get('organization', '')
            
            # Validation
            if not all([username, email, password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html')
            
            # Check if user exists
            existing_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                flash('Username or email already exists', 'error')
                return render_template('register.html')
            
            # Create new user
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                full_name=full_name,
                organization=organization
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('web.login'))
            
        except Exception as e:
            logging.error(f"Error in register: {e}")
            db.session.rollback()
            flash('Registration error', 'error')
    
    return render_template('register.html')

@web_bp.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('web.index'))

@web_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    try:
        return render_template('profile.html', {
            'user': current_user
        })
    except Exception as e:
        logging.error(f"Error in profile route: {e}")
        flash('Error loading profile', 'error')
        return render_template('error.html')

@web_bp.route('/api-status')
def api_status():
    """API status page for developers."""
    try:
        # Get system health
        from extensions import redis_client
        
        # Check Redis
        redis_status = 'healthy'
        try:
            redis_client.ping()
        except:
            redis_status = 'unhealthy'
        
        # Check database
        db_status = 'healthy'
        try:
            db.session.execute('SELECT 1')
        except:
            db_status = 'unhealthy'
        
        return render_template('api_status.html', {
            'api_version': '1.0.0',
            'status': 'healthy' if redis_status == 'healthy' and db_status == 'healthy' else 'degraded',
            'components': {
                'database': db_status,
                'redis': redis_status
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logging.error(f"Error in api_status route: {e}")
        flash('Error loading API status', 'error')
        return render_template('error.html')

@web_bp.route('/docs')
def documentation():
    """API documentation page."""
    return render_template('docs.html')

# Error handlers
@web_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@web_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    logging.error(f"Internal error: {error}")
    return render_template('500.html'), 500
