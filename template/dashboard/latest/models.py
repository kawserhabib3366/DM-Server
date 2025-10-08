
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy() # This will be initialized in app.py

class User(UserMixin, db.Model):
    """User model for admin authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default='admin')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Campaign(db.Model):
    """Campaign model for storing campaign information"""
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_group_ids = db.Column(db.JSON, nullable=False)  # ✅ list of group IDs instead of single int
    status = db.Column(db.String(50), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    launched_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Campaign content
    email_subject = db.Column(db.String(500))
    email_body = db.Column(db.Text)
    email_attachment_file = db.Column(db.String(500))  # Local file path
    email_attachment_url = db.Column(db.String(500))   # Web URL
    email_attachment_type = db.Column(db.String(10))   # 'file' or 'url'
    sms_message = db.Column(db.Text)
    voice_file_path = db.Column(db.String(500))
    ai_agent_profile = db.Column(db.JSON)
    social_config = db.Column(db.JSON)
    
    # Relationships
    user = db.relationship('User', backref='campaigns')
    email_logs = db.relationship('EmailLog', backref='campaign', lazy='dynamic')
    sms_logs = db.relationship('SMSLog', backref='campaign', lazy='dynamic')
    call_logs = db.relationship('CallLog', backref='campaign', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'client_group_ids': self.client_group_ids or [],  # ✅ always return list
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'launched_at': self.launched_at.isoformat() if self.launched_at else None,
            'created_by': self.created_by,
            'email_subject': self.email_subject,
            'email_body': self.email_body,
            'email_attachment_file': self.email_attachment_file,
            'email_attachment_url': self.email_attachment_url,
            'email_attachment_type': self.email_attachment_type,
            'sms_message': self.sms_message,
            'voice_file_path': self.voice_file_path,
            'ai_agent_profile': self.ai_agent_profile,
            'social_config': self.social_config
        }


class EmailLog(db.Model):
    """Log of sent emails"""
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    client_id = db.Column(db.Integer)
    client_name = db.Column(db.String(200))
    client_email = db.Column(db.String(255))
    subject = db.Column(db.String(500))
    body = db.Column(db.Text)
    attachment = db.Column(db.String(500))  # File path or URL
    attachment_type = db.Column(db.String(10))  # 'file' or 'url'
    status = db.Column(db.String(50))  # sent, failed, bounced, opened, clicked
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    api_response = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'client_id': self.client_id,
            'client_name': self.client_name,
            'client_email': self.client_email,
            'subject': self.subject,
            'body': self.body,
            'attachment': self.attachment,
            'attachment_type': self.attachment_type,
            'status': self.status,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'api_response': self.api_response
        }

class SMSLog(db.Model):
    """Log of sent SMS messages"""
    __tablename__ = 'sms_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    client_id = db.Column(db.Integer)
    client_name = db.Column(db.String(200))
    client_phone = db.Column(db.String(20))
    message = db.Column(db.Text)
    status = db.Column(db.String(50))  # sent, failed, delivered, failed_delivery
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    api_response = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'client_id': self.client_id,
            'client_name': self.client_name,
            'client_phone': self.client_phone,
            'message': self.message,
            'status': self.status,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'api_response': self.api_response
        }

class CallLog(db.Model):
    """Log of voice calls and AI agent interactions"""
    __tablename__ = 'call_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    client_id = db.Column(db.Integer)
    client_name = db.Column(db.String(200))
    client_phone = db.Column(db.String(20))
    call_type = db.Column(db.String(50))  # voice_message, ai_call
    agent_name = db.Column(db.String(100))
    conversation = db.Column(db.JSON)  # Store full conversation data
    status = db.Column(db.String(50))  # connected, failed, busy, no_answer, completed
    duration = db.Column(db.Integer)  # call duration in seconds
    error_message = db.Column(db.Text)
    called_at = db.Column(db.DateTime, default=datetime.utcnow)
    api_response = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'client_id': self.client_id,
            'client_name': self.client_name,
            'client_phone': self.client_phone,
            'call_type': self.call_type,
            'agent_name': self.agent_name,
            'conversation': self.conversation,
            'status': self.status,
            'duration': self.duration,
            'error_message': self.error_message,
            'called_at': self.called_at.isoformat() if self.called_at else None,
            'api_response': self.api_response
        }


