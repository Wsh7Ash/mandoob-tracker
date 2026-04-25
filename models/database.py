"""
Database models for Mandoob Tracker.

This module defines all database models for monitoring
government services in KSA and Qatar.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class Service(Base):
    """Government service information."""
    __tablename__ = 'services'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    country = Column(String(10), nullable=False)  # KSA, QA
    category = Column(String(50), nullable=False)  # immigration, traffic, health, etc.
    url = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Service configuration
    check_interval = Column(Integer, default=300)  # seconds
    timeout = Column(Integer, default=30)  # seconds
    retry_count = Column(Integer, default=3)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_critical = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    checks = relationship("ServiceCheck", back_populates="service", cascade="all, delete-orphan")
    alerts = relationship("ServiceAlert", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Service {self.name} ({self.country})>"


class ServiceCheck(Base):
    """Individual service check results."""
    __tablename__ = 'service_checks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    
    # Check results
    status_code = Column(Integer)
    response_time = Column(Float)  # milliseconds
    is_available = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # SSL/TLS information
    ssl_valid = Column(Boolean, nullable=True)
    ssl_expires = Column(DateTime, nullable=True)
    ssl_issuer = Column(String(200), nullable=True)
    
    # Content verification
    content_matches = Column(Boolean, nullable=True)
    content_hash = Column(String(64), nullable=True)
    
    # Check configuration
    check_type = Column(String(20), default='http')  # http, ping, tcp
    user_agent = Column(String(500), default='Mandoob-Tracker/1.0')
    
    # Timestamps
    checked_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service = relationship("Service", back_populates="checks")
    
    def __repr__(self):
        return f"<ServiceCheck {self.service.name}: {self.status_code}>"


class ServiceAlert(Base):
    """Service alerts and notifications."""
    __tablename__ = 'service_alerts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    
    # Alert information
    alert_type = Column(String(20), nullable=False)  # downtime, ssl_error, content_change
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Alert timing
    started_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Additional data
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service = relationship("Service", back_populates="alerts")
    
    def __repr__(self):
        return f"<ServiceAlert {self.title} ({self.severity})>"


class User(Base):
    """Application users."""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # User information
    full_name = Column(String(200))
    organization = Column(String(200))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Preferences
    notification_email = Column(Boolean, default=True)
    notification_sms = Column(Boolean, default=False)
    timezone = Column(String(50), default='Asia/Riyadh')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    def __repr__(self):
        return f"<User {self.username}>"


class UserSubscription(Base):
    """User service subscriptions."""
    __tablename__ = 'user_subscriptions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    
    # Subscription preferences
    alert_types = Column(JSON, default=['downtime', 'ssl_error'])  # Array of alert types
    min_severity = Column(String(20), default='medium')  # Minimum severity to notify
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    service = relationship("Service")
    
    def __repr__(self):
        return f"<UserSubscription {self.user.username} -> {self.service.name}>"


class ServiceMetrics(Base):
    """Aggregated service metrics."""
    __tablename__ = 'service_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(10), nullable=False)  # hour, day, week, month
    
    # Metrics
    total_checks = Column(Integer, default=0)
    successful_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    uptime_percentage = Column(Float, default=0.0)
    avg_response_time = Column(Float, default=0.0)
    min_response_time = Column(Float)
    max_response_time = Column(Float)
    
    # Additional metrics
    ssl_errors = Column(Integer, default=0)
    timeout_errors = Column(Integer, default=0)
    connection_errors = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service = relationship("Service")
    
    def __repr__(self):
        return f"<ServiceMetrics {self.service.name} {self.period_type}>"


class SystemStatus(Base):
    """Overall system health status."""
    __tablename__ = 'system_status'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Component information
    component = Column(String(50), nullable=False)  # monitor, database, redis, api
    status = Column(String(20), nullable=False)  # healthy, degraded, unhealthy, offline
    
    # Status details
    message = Column(String(500))
    details = Column(JSON, default=dict)
    
    # Performance metrics
    response_time = Column(Float)  # milliseconds
    error_rate = Column(Float, default=0.0)  # percentage
    cpu_usage = Column(Float, default=0.0)  # percentage
    memory_usage = Column(Float, default=0.0)  # percentage
    
    # Timestamps
    last_check = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemStatus {self.component}: {self.status}>"


class MaintenanceWindow(Base):
    """Scheduled maintenance windows."""
    __tablename__ = 'maintenance_windows'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    
    # Maintenance information
    title = Column(String(200), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Impact
    impact_level = Column(String(20), nullable=False)  # low, medium, high, critical
    affected_services = Column(JSON, default=list)  # Array of service names
    
    # Status
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service = relationship("Service")
    
    def __repr__(self):
        return f"<MaintenanceWindow {self.title}>"


class ApiKey(Base):
    """API keys for external access."""
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # API key information
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(10), nullable=False)  # First 10 chars for display
    
    # Permissions and limits
    permissions = Column(JSON, default=['read'])  # Array of permissions
    rate_limit = Column(Integer, default=1000)  # requests per hour
    allowed_ips = Column(JSON, default=list)  # Array of allowed IP addresses
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    last_used = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<ApiKey {self.name}>"
