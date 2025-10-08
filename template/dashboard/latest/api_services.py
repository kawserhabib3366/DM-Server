
import requests
import json
from typing import List, Dict, Any
from models import EmailLog, SMSLog, CallLog, db
from config import Config

class AIAgentAPI:
    """
    Interface to connect with your existing APIs and log all interactions
    """
    
    def __init__(self):
        self.timeout = 30  # Request timeout in seconds
        self.VOICE_CALL_ENDPOINT = Config.VOICE_CALL_ENDPOINT
        self.SEND_EMAIL_ENDPOINT = Config.SEND_EMAIL_ENDPOINT
    
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
                    print(email_data)
                    # Make request to your email API
                    response = requests.post(
                        self.SEND_EMAIL_ENDPOINT,
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
                    'message': message
                }
                
                sms_tasks.append(sms_task)
                client_logs[client_phone] = {'log': sms_log, 'client': client}
            
            if not sms_tasks:
                db.session.commit()
                return results
            
            try:
                # Make batch request to your /gvoice API
                response = requests.post(
                    self.VOICE_CALL_ENDPOINT,
                    json=sms_tasks,  # Send list of tasks
                    timeout=self.timeout,
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
                
                voice_tasks.append(voice_task)
                client_logs[client_phone] = {'log': call_log, 'client': client}
            
            if not voice_tasks:
                db.session.commit()
                return results
            
            try:
                # Make batch request to your /gvoice API
                response = requests.post(
                    self.VOICE_CALL_ENDPOINT,
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
                    self.VOICE_CALL_ENDPOINT,
                    json=ai_tasks,  # Send list of tasks
                    timeout=self.timeout * 4,  # Increased timeout for AI calls
                    headers={'Content-Type': 'application/json'}
                )
                
                
                
                if response.status_code == 200:
                    api_response = response.json() if response.content else {}

                    
                    
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
                'error': f'AI interactive call campaign error: {str(e)}',
                'success': 0,
                'failed': len(client_list),
                'details': []
            }



