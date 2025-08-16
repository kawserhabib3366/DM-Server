import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/campaign_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the dashboard.'

# Your API Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
VOICE_CALL_ENDPOINT = f"{API_BASE_URL}/api/gvoice"  # Updated to use /gvoice
SEND_EMAIL_ENDPOINT = f"{API_BASE_URL}/api/send_email"

# Allowed file extensions for attachments
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mp4', 'mpeg', 'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'zip', 'xlsx', 'csv'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'attachments'), exist_ok=True)  # New attachment folder

# ============================================================================
# Database Models
# ============================================================================

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Campaign(db.Model):
    """Campaign model for storing campaign information"""
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_group_id = db.Column(db.Integer)
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
            'client_group_id': self.client_group_id,
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

# ============================================================================
# Enhanced AI Agent Interface with Data Logging
# ============================================================================

class AIAgentAPI:
    """
    Interface to connect with your existing APIs and log all interactions
    """
    
    def __init__(self):
        self.timeout = 30  # Request timeout in seconds
    
    def send_email(self, client_list: List[Dict], subject: str, body: str, campaign_id: int, attachment: str = None, attachment_type: str = None) -> Dict:
        """Send emails with optional attachments and log all interactions"""
        try:
            results = {
                'success': 0,
                'failed': 0,
                'details': []
            }
            
            for client in client_list:
                client_email = client.get('email')
                client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                
                email_log = EmailLog(
                    campaign_id=campaign_id,
                    client_id=client.get('id'),
                    client_name=client_name,
                    client_email=client_email,
                    subject=subject,
                    body=body,
                    attachment=attachment,
                    attachment_type=attachment_type
                )
                
                if not client_email:
                    email_log.status = 'failed'
                    email_log.error_message = 'No email address'
                    db.session.add(email_log)
                    
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client.get('id'),
                        'email': 'N/A',
                        'status': 'failed',
                        'error': 'No email address'
                    })
                    continue
                
                try:
                    # Prepare email data for your API
                    email_data = {
                        'receiver_email': client_email,
                        'subject': subject,
                        'html_body': body,
                        'attachment': attachment  # Can be file path or URL
                    }
                    
                    # Make request to your email API
                    response = requests.post(
                        SEND_EMAIL_ENDPOINT,
                        json=email_data,
                        timeout=self.timeout,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    # Log the API response
                    email_log.api_response = response.json() if response.content else {}
                    
                    if response.status_code == 200:
                        email_log.status = 'sent'
                        results['success'] += 1
                        results['details'].append({
                            'client_id': client.get('id'),
                            'email': client_email,
                            'status': 'sent',
                            'attachment': attachment,
                            'response': email_log.api_response
                        })
                    else:
                        email_log.status = 'failed'
                        email_log.error_message = f'HTTP {response.status_code}: {response.text}'
                        results['failed'] += 1
                        results['details'].append({
                            'client_id': client.get('id'),
                            'email': client_email,
                            'status': 'failed',
                            'error': email_log.error_message
                        })
                
                except requests.exceptions.RequestException as e:
                    email_log.status = 'failed'
                    email_log.error_message = f'Request error: {str(e)}'
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client.get('id'),
                        'email': client_email,
                        'status': 'failed',
                        'error': email_log.error_message
                    })
                
                db.session.add(email_log)
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            return {
                'error': f'Email campaign error: {str(e)}',
                'success': 0,
                'failed': len(client_list),
                'details': []
            }
    
    def send_sms(self, client_list: List[Dict], message: str, campaign_id: int) -> Dict:
        """Send SMS and log all interactions using batch /gvoice endpoint"""
        try:
            results = {
                'success': 0,
                'failed': 0,
                'details': []
            }
            
            # Prepare batch SMS requests
            sms_tasks = []
            client_logs = {}
            
            for client in client_list:
                client_phone = client.get('phone')
                client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                client_id = client.get('id')
                
                sms_log = SMSLog(
                    campaign_id=campaign_id,
                    client_id=client_id,
                    client_name=client_name,
                    client_phone=client_phone,
                    message=message
                )
                
                if not client_phone:
                    sms_log.status = 'failed'
                    sms_log.error_message = 'No phone number'
                    db.session.add(sms_log)
                    
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client_id,
                        'phone': 'N/A',
                        'status': 'failed',
                        'error': 'No phone number'
                    })
                    continue
                
                # Prepare SMS task for batch request
                sms_task = {
                    'type': 'sms',
                    'phone': client_phone,
                    'username': client_name or f"Client {client_id or 'Unknown'}",
                    'msg': message
                }
                
                sms_tasks.append(sms_task)
                client_logs[client_phone] = {'log': sms_log, 'client': client}
            
            if not sms_tasks:
                db.session.commit()
                return results
            
            try:
                # Make batch request to your /gvoice API
                response = requests.post(
                    VOICE_CALL_ENDPOINT,
                    json=sms_tasks,  # Send list of tasks
                    timeout=self.timeout * 2,  # Increased timeout for batch requests
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    api_response = response.json() if response.content else {}
                    
                    # Process batch response
                    if isinstance(api_response, list):
                        # Response is a list matching the request order
                        for i, task_result in enumerate(api_response):
                            if i < len(sms_tasks):
                                phone = sms_tasks[i]['phone']
                                if phone in client_logs:
                                    log_data = client_logs[phone]
                                    sms_log = log_data['log']
                                    client = log_data['client']
                                    
                                    sms_log.api_response = task_result
                                    
                                    if task_result.get('success', False):
                                        sms_log.status = 'sent'
                                        results['success'] += 1
                                        results['details'].append({
                                            'client_id': client.get('id'),
                                            'phone': phone,
                                            'status': 'sent',
                                            'response': task_result
                                        })
                                    else:
                                        sms_log.status = 'failed'
                                        sms_log.error_message = task_result.get('error', 'Unknown error')
                                        results['failed'] += 1
                                        results['details'].append({
                                            'client_id': client.get('id'),
                                            'phone': phone,
                                            'status': 'failed',
                                            'error': sms_log.error_message
                                        })
                    else:
                        # Single response object, assume all succeeded
                        for phone, log_data in client_logs.items():
                            sms_log = log_data['log']
                            client = log_data['client']
                            
                            sms_log.api_response = api_response
                            sms_log.status = 'sent'
                            results['success'] += 1
                            results['details'].append({
                                'client_id': client.get('id'),
                                'phone': phone,
                                'status': 'sent',
                                'response': api_response
                            })
                else:
                    # Batch request failed, mark all as failed
                    error_msg = f'HTTP {response.status_code}: {response.text}'
                    for phone, log_data in client_logs.items():
                        sms_log = log_data['log']
                        client = log_data['client']
                        
                        sms_log.status = 'failed'
                        sms_log.error_message = error_msg
                        results['failed'] += 1
                        results['details'].append({
                            'client_id': client.get('id'),
                            'phone': phone,
                            'status': 'failed',
                            'error': error_msg
                        })
                
                # Add all logs to session
                for phone, log_data in client_logs.items():
                    db.session.add(log_data['log'])
                
            except requests.exceptions.RequestException as e:
                # Network error, mark all as failed
                error_msg = f'Request error: {str(e)}'
                for phone, log_data in client_logs.items():
                    sms_log = log_data['log']
                    client = log_data['client']
                    
                    sms_log.status = 'failed'
                    sms_log.error_message = error_msg
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client.get('id'),
                        'phone': phone,
                        'status': 'failed',
                        'error': error_msg
                    })
                    db.session.add(sms_log)
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            return {
                'error': f'SMS campaign error: {str(e)}',
                'success': 0,
                'failed': len(client_list),
                'details': []
            }
    
    def leave_voice_message(self, client_list: List[Dict], audio_file_path: str, campaign_id: int) -> Dict:
   
        """Leave voice messages using batch /gvoice endpoint"""
        try:
            results = {
                'success': 0,
                'failed': 0,
                'details': []
            }
            
            # Prepare batch voice message requests
            voice_tasks = []
            client_logs = {}
            
            for client in client_list:
                client_phone = client.get('phone')
                client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                client_id = client.get('id')
                
                call_log = CallLog(
                    campaign_id=campaign_id,
                    client_id=client_id,
                    client_name=client_name,
                    client_phone=client_phone,
                    call_type='voice_message'
                )
                
                if not client_phone:
                    call_log.status = 'failed'
                    call_log.error_message = 'No phone number'
                    db.session.add(call_log)
                    
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client_id,
                        'phone': 'N/A',
                        'status': 'failed',
                        'error': 'No phone number'
                    })
                    continue
                
                # Prepare voice message task for batch request
                voice_task = {
                    'type': 'voice_message',
                    'phone': client_phone,
                    'username': client_name or f"Client {client_id or 'Unknown'}",
                    'voicemsg_path': audio_file_path
                }
                print(voice_tasks)
                
                voice_tasks.append(voice_task)
                client_logs[client_phone] = {'log': call_log, 'client': client}
            
            if not voice_tasks:
                db.session.commit()
                return results
            
            try:
                # Make batch request to your /gvoice API
                print(voice_tasks)
                response = requests.post(
                    VOICE_CALL_ENDPOINT,
                    json=voice_tasks,  # Send list of tasks
                    timeout=self.timeout * 3,  # Increased timeout for voice calls
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    api_response = response.json() if response.content else {}
                    
                    # Process batch response
                    if isinstance(api_response, list):
                        # Response is a list matching the request order
                        for i, task_result in enumerate(api_response):
                            if i < len(voice_tasks):
                                phone = voice_tasks[i]['phone']
                                if phone in client_logs:
                                    log_data = client_logs[phone]
                                    call_log = log_data['log']
                                    client = log_data['client']
                                    
                                    call_log.api_response = task_result
                                    
                                    # Extract duration if available
                                    if task_result.get('duration'):
                                        call_log.duration = task_result['duration']
                                    
                                    if task_result.get('success', False):
                                        call_log.status = 'connected'
                                        results['success'] += 1
                                        results['details'].append({
                                            'client_id': client.get('id'),
                                            'phone': phone,
                                            'status': 'called',
                                            'response': task_result
                                        })
                                    else:
                                        call_log.status = 'failed'
                                        call_log.error_message = task_result.get('error', 'Unknown error')
                                        results['failed'] += 1
                                        results['details'].append({
                                            'client_id': client.get('id'),
                                            'phone': phone,
                                            'status': 'failed',
                                            'error': call_log.error_message
                                        })
                    else:
                        # Single response object, assume all succeeded
                        for phone, log_data in client_logs.items():
                            call_log = log_data['log']
                            client = log_data['client']
                            
                            call_log.api_response = api_response
                            call_log.status = 'connected'
                            results['success'] += 1
                            results['details'].append({
                                'client_id': client.get('id'),
                                'phone': phone,
                                'status': 'called',
                                'response': api_response
                            })
                else:
                    # Batch request failed, mark all as failed
                    error_msg = f'HTTP {response.status_code}: {response.text}'
                    for phone, log_data in client_logs.items():
                        call_log = log_data['log']
                        client = log_data['client']
                        
                        call_log.status = 'failed'
                        call_log.error_message = error_msg
                        results['failed'] += 1
                        results['details'].append({
                            'client_id': client.get('id'),
                            'phone': phone,
                            'status': 'failed',
                            'error': error_msg
                        })
                
                # Add all logs to session
                for phone, log_data in client_logs.items():
                    db.session.add(log_data['log'])
                
            except requests.exceptions.RequestException as e:
                # Network error, mark all as failed
                error_msg = f'Request error: {str(e)}'
                for phone, log_data in client_logs.items():
                    call_log = log_data['log']
                    client = log_data['client']
                    
                    call_log.status = 'failed'
                    call_log.error_message = error_msg
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client.get('id'),
                        'phone': phone,
                        'status': 'failed',
                        'error': error_msg
                    })
                    db.session.add(call_log)
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            return {
                'error': f'Voice message campaign error: {str(e)}',
                'success': 0,
                'failed': len(client_list),
                'details': []
            }
    
    def interactive_call(self, client_list: List[Dict], agent_profile: Dict, campaign_id: int) -> Dict:
        """Make AI agent calls using batch /gvoice endpoint and log conversations"""
        try:
            results = {
                'success': 0,
                'failed': 0,
                'details': []
            }
            
            agent_script = agent_profile.get('script', '')
            agent_name = agent_profile.get('name', 'AI Agent')
            agent_personality = agent_profile.get('personality', '')
            agent_voice = agent_profile.get('voice', '')


            agent_message = f"AI Agent: {agent_name}\nPersonality: {agent_personality}\nScript: {agent_script}"
            
            # Prepare batch AI call requests
            ai_tasks = []
            client_logs = {}
            
            for client in client_list:
                client_phone = client.get('phone')
                client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                client_id = client.get('id')
                
                call_log = CallLog(
                    campaign_id=campaign_id,
                    client_id=client_id,
                    client_name=client_name,
                    client_phone=client_phone,
                    call_type='ai_call',
                    agent_name=agent_name
                )
                
                if not client_phone:
                    call_log.status = 'failed'
                    call_log.error_message = 'No phone number'
                    db.session.add(call_log)
                    
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client_id,
                        'phone': 'N/A',
                        'status': 'failed',
                        'error': 'No phone number'
                    })
                    continue
                
                # Prepare AI call task for batch request
                ai_task = {
                    'type': 'ai_call',
                    'phone': client_phone,
                    'username': client_name or f"Client {client_id or 'Unknown'}",
                    'ai_profile':agent_profile
        
                }
                
                ai_tasks.append(ai_task)
                client_logs[client_phone] = {'log': call_log, 'client': client}
            
            if not ai_tasks:
                db.session.commit()
                return results
            
            try:
                # Make batch request to your /gvoice API
                response = requests.post(
                    VOICE_CALL_ENDPOINT,
                    json=ai_tasks,  # Send list of tasks
                    timeout=self.timeout * 4,  # Increased timeout for AI calls
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    api_response = response.json() if response.content else {}

                    print(api_response)
                    
                    # Process batch response
                    if isinstance(api_response, list):
                        # Response is a list matching the request order
                        for i, task_result in enumerate(api_response):
                            if i < len(ai_tasks):
                                phone = ai_tasks[i]['phone']
                                if phone in client_logs:
                                    log_data = client_logs[phone]
                                    call_log = log_data['log']
                                    client = log_data['client']
                                    
                                    call_log.api_response = task_result
                                    
                                    # Extract conversation data from API response
                                    if task_result.get('conversation'):
                                        call_log.conversation = task_result['conversation']
                                    
                                    # Extract duration if available
                                    if task_result.get('duration'):
                                        call_log.duration = task_result['duration']
                                    
                                    if task_result.get('success', False):
                                        call_log.status = 'connected'
                                        results['success'] += 1
                                        results['details'].append({
                                            'client_id': client.get('id'),
                                            'phone': phone,
                                            'agent': agent_name,
                                            'status': 'connected',
                                            'response': task_result
                                        })
                                    else:
                                        call_log.status = 'failed'
                                        call_log.error_message = task_result.get('error', 'Unknown error')
                                        results['failed'] += 1
                                        results['details'].append({
                                            'client_id': client.get('id'),
                                            'phone': phone,
                                            'agent': agent_name,
                                            'status': 'failed',
                                            'error': call_log.error_message
                                        })
                    else:
                        # Single response object, assume all succeeded
                        for phone, log_data in client_logs.items():
                            call_log = log_data['log']
                            client = log_data['client']
                            
                            call_log.api_response = api_response
                            call_log.status = 'connected'
                            
                            # Extract conversation if available
                            if api_response.get('conversation'):
                                call_log.conversation = api_response['conversation']
                            
                            results['success'] += 1
                            results['details'].append({
                                'client_id': client.get('id'),
                                'phone': phone,
                                'agent': agent_name,
                                'status': 'connected',
                                'response': api_response
                            })
                else:
                    # Batch request failed, mark all as failed
                    error_msg = f'HTTP {response.status_code}: {response.text}'
                    for phone, log_data in client_logs.items():
                        call_log = log_data['log']
                        client = log_data['client']
                        
                        call_log.status = 'failed'
                        call_log.error_message = error_msg
                        results['failed'] += 1
                        results['details'].append({
                            'client_id': client.get('id'),
                            'phone': phone,
                            'agent': agent_name,
                            'status': 'failed',
                            'error': error_msg
                        })
                
                # Add all logs to session
                for phone, log_data in client_logs.items():
                    db.session.add(log_data['log'])
                
            except requests.exceptions.RequestException as e:
                # Network error, mark all as failed
                error_msg = f'Request error: {str(e)}'
                for phone, log_data in client_logs.items():
                    call_log = log_data['log']
                    client = log_data['client']
                    
                    call_log.status = 'failed'
                    call_log.error_message = error_msg
                    results['failed'] += 1
                    results['details'].append({
                        'client_id': client.get('id'),
                        'phone': phone,
                        'agent': agent_name,
                        'status': 'failed',
                        'error': error_msg
                    })
                    db.session.add(call_log)
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            return {
                'error': f'AI call campaign error: {str(e)}',
                'success': 0,
                'failed': len(client_list),
                'details': []
            }

# Initialize AI Agent
ai_agent = AIAgentAPI()

# ============================================================================
# MySQL Database Connection (unchanged)
# ============================================================================

class MySQLConnection:
    """Handle MySQL database connections for client data"""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'database': os.getenv('MYSQL_DATABASE', 'clients_db'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', '')
        }
    
    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def get_client_groups(self):
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT DISTINCT 
                    group_id, 
                    group_name, 
                    COUNT(*) as client_count 
                FROM clients 
                GROUP BY group_id, group_name
                ORDER BY group_name
            """
            cursor.execute(query)
            groups = cursor.fetchall()
            return groups
        except Error as e:
            print(f"Error fetching groups: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_clients_by_group(self, group_id: int):
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    id, 
                    first_name, 
                    last_name, 
                    email, 
                    phone, 
                    group_id 
                FROM clients 
                WHERE group_id = %s
            """
            cursor.execute(query, (group_id,))
            clients = cursor.fetchall()
            return clients
        except Error as e:
            print(f"Error fetching clients: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

mysql_conn = MySQLConnection()

# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Handle both form data and JSON
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            error_msg = 'Username and password are required'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg)
            return render_template('login.html'), 400
        
        try:
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                print(f"User {username} logged in successfully")  # Debug log
                
                if request.is_json:
                    return jsonify({'success': True, 'user': user.to_dict()})
                return redirect(url_for('index'))
            else:
                error_msg = 'Invalid username or password'
                print(f"Login failed for user: {username}")  # Debug log
                if request.is_json:
                    return jsonify({'success': False, 'error': error_msg}), 401
                flash(error_msg)
                return render_template('login.html'), 401
                
        except Exception as e:
            error_msg = 'Login system error. Please try again.'
            print(f"Login error: {str(e)}")  # Debug log
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 500
            flash(error_msg)
            return render_template('login.html'), 500
    
    # GET request - show login form
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    return redirect(url_for('login'))

@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def profile():
    if request.method == 'PUT':
        data = request.get_json()
        
        if 'first_name' in data:
            current_user.first_name = data['first_name']
        if 'last_name' in data:
            current_user.last_name = data['last_name']
        if 'email' in data:
            current_user.email = data['email']
        
        # Handle password change
        if 'new_password' in data and data['new_password']:
            if not data.get('current_password'):
                return jsonify({'success': False, 'error': 'Current password required'}), 400
            
            if not current_user.check_password(data['current_password']):
                return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
            
            current_user.set_password(data['new_password'])
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'user': current_user.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': True, 'user': current_user.to_dict()})

# ============================================================================
# Protected Routes
# ============================================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))

@app.route('/api/client-groups')
@login_required
def get_client_groups():
    groups = mysql_conn.get_client_groups()
    return jsonify({'success': True, 'groups': groups})

@app.route('/api/clients/<int:group_id>')
@login_required
def get_clients(group_id):
    clients = mysql_conn.get_clients_by_group(group_id)
    return jsonify({'success': True, 'clients': clients, 'count': len(clients)})

@app.route('/api/campaigns', methods=['GET'])
@login_required
def get_campaigns():
    campaigns = Campaign.query.filter_by(created_by=current_user.id).order_by(Campaign.created_at.desc()).all()
    return jsonify({
        'success': True,
        'campaigns': [c.to_dict() for c in campaigns]
    })

@app.route('/api/campaigns', methods=['POST'])
@login_required
def create_campaign():
    data = request.json
    
    campaign = Campaign(
        name=data.get('name'),
        description=data.get('description'),
        client_group_id=data.get('client_group_id'),
        email_subject=data.get('email_subject'),
        email_body=data.get('email_body'),
        email_attachment_file=data.get('email_attachment_file'),
        email_attachment_url=data.get('email_attachment_url'),
        email_attachment_type=data.get('email_attachment_type'),
        sms_message=data.get('sms_message'),
        voice_file_path=data.get('voice_file_path'),
        ai_agent_profile=data.get('ai_agent_profile'),
        social_config=data.get('social_config'),
        status='draft',
        created_by=current_user.id
    )
    
    db.session.add(campaign)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'campaign': campaign.to_dict()
    })

@app.route('/api/launch-campaign', methods=['POST'])
@login_required
def launch_campaign():
    """Launch campaign with enhanced logging"""
    data = request.json
    campaign_id = data.get('campaign_id')
    
    campaign = Campaign.query.filter_by(id=campaign_id, created_by=current_user.id).first()
    if not campaign:
        return jsonify({'success': False, 'error': 'Campaign not found'}), 404
    
    clients = mysql_conn.get_clients_by_group(campaign.client_group_id)
    
    if not clients:
        return jsonify({
            'success': False,
            'error': 'No clients found in the selected group'
        }), 400
    
    results = {
        'campaign_id': campaign_id,
        'total_clients': len(clients),
        'actions': {}
    }
    
    # Execute Email Campaign with logging
    if campaign.email_subject and campaign.email_body:
        print(f"Sending emails to {len(clients)} clients...")
        email_results = ai_agent.send_email(
            clients, 
            campaign.email_subject, 
            campaign.email_body,
            campaign_id
        )
        results['actions']['email'] = email_results
        print(f"Email results: {email_results['success']} success, {email_results['failed']} failed")
    
    # Execute SMS Campaign with logging
    if campaign.sms_message:
        print(f"Sending SMS to {len(clients)} clients...")
        sms_results = ai_agent.send_sms(
            clients, 
            campaign.sms_message,
            campaign_id
        )
        results['actions']['sms'] = sms_results
        print(f"SMS results: {sms_results['success']} success, {sms_results['failed']} failed")
    
    # Execute Voice Campaign with logging
    if campaign.voice_file_path:
        print(f"Making voice calls to {len(clients)} clients...")
        voice_results = ai_agent.leave_voice_message(
            clients, 
            campaign.voice_file_path,
            campaign_id
        )
        results['actions']['voice'] = voice_results
        print(f"Voice results: {voice_results['success']} success, {voice_results['failed']} failed")

    
    # Execute AI Agent Calls with logging
    if campaign.ai_agent_profile:
        print(f"Making AI agent calls to {len(clients)} clients...")
        ai_call_results = ai_agent.interactive_call(
            clients, 
            campaign.ai_agent_profile,
            campaign_id
        )
        results['actions']['ai_calls'] = ai_call_results
        print(f"AI call results: {ai_call_results['success']} success, {ai_call_results['failed']} failed")
    
    # Update campaign status
    campaign.status = 'launched'
    campaign.launched_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'results': results
    })

# ============================================================================
# Analytics and Reporting Routes
# ============================================================================

@app.route('/api/analytics/dashboard')
@login_required
def get_dashboard_analytics():
    """Get dashboard analytics data"""
    try:
        # Date ranges
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Total counts for current user's campaigns
        user_campaign_ids = [c.id for c in Campaign.query.filter_by(created_by=current_user.id).all()]
        
        analytics = {
            'totals': {
                'campaigns': len(user_campaign_ids),
                'emails_sent': EmailLog.query.filter(
                    EmailLog.campaign_id.in_(user_campaign_ids),
                    EmailLog.status == 'sent'
                ).count(),
                'sms_sent': SMSLog.query.filter(
                    SMSLog.campaign_id.in_(user_campaign_ids),
                    SMSLog.status == 'sent'
                ).count(),
                'calls_made': CallLog.query.filter(
                    CallLog.campaign_id.in_(user_campaign_ids),
                    CallLog.status == 'connected'
                ).count()
            },
            'recent': {
                'campaigns_this_week': Campaign.query.filter(
                    Campaign.created_by == current_user.id,
                    Campaign.created_at >= week_ago
                ).count(),
                'emails_this_week': EmailLog.query.filter(
                    EmailLog.campaign_id.in_(user_campaign_ids),
                    EmailLog.sent_at >= week_ago,
                    EmailLog.status == 'sent'
                ).count(),
                'sms_this_week': SMSLog.query.filter(
                    SMSLog.campaign_id.in_(user_campaign_ids),
                    SMSLog.sent_at >= week_ago,
                    SMSLog.status == 'sent'
                ).count(),
                'calls_this_week': CallLog.query.filter(
                    CallLog.campaign_id.in_(user_campaign_ids),
                    CallLog.called_at >= week_ago,
                    CallLog.status == 'connected'
                ).count()
            },
            'success_rates': {
                'email_success_rate': 0,
                'sms_success_rate': 0,
                'call_success_rate': 0
            }
        }
        
        # Calculate success rates
        if user_campaign_ids:
            total_emails = EmailLog.query.filter(EmailLog.campaign_id.in_(user_campaign_ids)).count()
            if total_emails > 0:
                analytics['success_rates']['email_success_rate'] = round(
                    (analytics['totals']['emails_sent'] / total_emails) * 100, 1
                )
            
            total_sms = SMSLog.query.filter(SMSLog.campaign_id.in_(user_campaign_ids)).count()
            if total_sms > 0:
                analytics['success_rates']['sms_success_rate'] = round(
                    (analytics['totals']['sms_sent'] / total_sms) * 100, 1
                )
            
            total_calls = CallLog.query.filter(CallLog.campaign_id.in_(user_campaign_ids)).count()
            if total_calls > 0:
                analytics['success_rates']['call_success_rate'] = round(
                    (analytics['totals']['calls_made'] / total_calls) * 100, 1
                )
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/campaign-performance')
@login_required
def get_campaign_performance():
    """Get performance data for all user campaigns"""
    try:
        campaigns = Campaign.query.filter_by(created_by=current_user.id).all()
        performance_data = []
        
        for campaign in campaigns:
            # Get counts for this campaign
            emails_sent = EmailLog.query.filter_by(campaign_id=campaign.id, status='sent').count()
            emails_failed = EmailLog.query.filter_by(campaign_id=campaign.id, status='failed').count()
            
            sms_sent = SMSLog.query.filter_by(campaign_id=campaign.id, status='sent').count()
            sms_failed = SMSLog.query.filter_by(campaign_id=campaign.id, status='failed').count()
            
            calls_connected = CallLog.query.filter_by(campaign_id=campaign.id, status='connected').count()
            calls_failed = CallLog.query.filter_by(campaign_id=campaign.id, status='failed').count()
            
            performance_data.append({
                'campaign_id': campaign.id,
                'campaign_name': campaign.name,
                'status': campaign.status,
                'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
                'launched_at': campaign.launched_at.isoformat() if campaign.launched_at else None,
                'metrics': {
                    'email': {'sent': emails_sent, 'failed': emails_failed},
                    'sms': {'sent': sms_sent, 'failed': sms_failed},
                    'calls': {'connected': calls_connected, 'failed': calls_failed}
                }
            })
        
        return jsonify({
            'success': True,
            'campaigns': performance_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/campaign/<int:campaign_id>/logs')
@login_required
def get_campaign_logs(campaign_id):
    """Get detailed logs for a specific campaign"""
    try:
        # Verify campaign belongs to user
        campaign = Campaign.query.filter_by(id=campaign_id, created_by=current_user.id).first()
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Get all logs for this campaign
        email_logs = [log.to_dict() for log in EmailLog.query.filter_by(campaign_id=campaign_id).order_by(EmailLog.sent_at.desc()).all()]
        sms_logs = [log.to_dict() for log in SMSLog.query.filter_by(campaign_id=campaign_id).order_by(SMSLog.sent_at.desc()).all()]
        call_logs = [log.to_dict() for log in CallLog.query.filter_by(campaign_id=campaign_id).order_by(CallLog.called_at.desc()).all()]
        
        return jsonify({
            'success': True,
            'campaign': campaign.to_dict(),
            'logs': {
                'emails': email_logs,
                'sms': sms_logs,
                'calls': call_logs
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/conversation/<int:call_log_id>')
@login_required
def get_conversation(call_log_id):
    """Get detailed conversation data for a specific call"""
    try:
        # Get call log and verify it belongs to user's campaign
        call_log = CallLog.query.join(Campaign).filter(
            CallLog.id == call_log_id,
            Campaign.created_by == current_user.id
        ).first()
        
        if not call_log:
            return jsonify({'success': False, 'error': 'Call log not found'}), 404
        
        return jsonify({
            'success': True,
            'call_log': call_log.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Utility Functions
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_default_admin():
    """Create default admin user if none exists"""
    try:
        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # This will hash the password
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Default admin user created successfully!")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Please change the password after first login.")
        else:
            print("ℹ️  Admin user already exists")
            
        # Verify the admin user exists and can authenticate
        test_user = User.query.filter_by(username='admin').first()
        if test_user:
            if test_user.check_password('admin123'):
                print("✅ Admin user authentication test: PASSED")
            else:
                print("❌ Admin user authentication test: FAILED")
                print("   Creating new admin user...")
                # Delete the broken user and create a new one
                db.session.delete(test_user)
                db.session.commit()
                create_default_admin()  # Recursive call to recreate
        else:
            print("❌ No admin user found after creation")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.session.rollback()

# ============================================================================
# File Upload and Other Routes
# ============================================================================

@app.route('/api/upload-attachment', methods=['POST'])
@login_required
def upload_attachment():
    """Handle email attachment file uploads"""
    if 'attachment' not in request.files:
        return jsonify({'success': False, 'error': 'No attachment file provided'}), 400
    
    file = request.files['attachment']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'attachments', filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'original_name': file.filename
        })
    
    return jsonify({'success': False, 'error': 'Invalid file type'}), 400

@app.route('/api/upload-audio', methods=['POST'])
@login_required
def upload_audio():
    """Handle audio file uploads"""
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath
        })
    
    return jsonify({'success': False, 'error': 'Invalid file type'}), 400

@app.route('/api/test-connection')
@login_required
def test_connection():
    """Test database connection and API connectivity"""
    test_results = {}
    
    # Test database connection
    conn = mysql_conn.get_connection()
    if conn:
        conn.close()
        test_results['database'] = {'status': 'success', 'message': 'Database connection successful'}
    else:
        test_results['database'] = {'status': 'failed', 'message': 'Database connection failed'}
    
    # Test your API endpoints
    try:
        test_response = requests.get(f"{API_BASE_URL}/", timeout=5)
        test_results['api_server'] = {'status': 'success', 'message': f'API server reachable at {API_BASE_URL}'}
    except requests.exceptions.RequestException as e:
        test_results['api_server'] = {'status': 'failed', 'message': f'API server unreachable: {str(e)}'}
    
    all_success = all(result['status'] == 'success' for result in test_results.values())
    
    return jsonify({
        'success': all_success,
        'tests': test_results
    })


UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'audio')

@app.route('/uploads/audio/<path:filename>')

def serve_audio(filename):
    return send_from_directory(os.path.join(app.root_path, 'uploads', 'audio'), filename, mimetype='audio/mpeg')




# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# Main Application Entry Point
# ============================================================================

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_admin()
    
    print(f"Enhanced Campaign Dashboard starting...")
    print(f"Using API base URL: {API_BASE_URL}")
    print(f"Voice Call Endpoint: {VOICE_CALL_ENDPOINT}")
    print(f"Send Email Endpoint: {SEND_EMAIL_ENDPOINT}")
    print(f"Default admin login: admin/admin123")
    
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)