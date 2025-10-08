import requests,os
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
VOICE_CALL_ENDPOINT = f"{API_BASE_URL}/api/gvoice"  # Updated to use /gvoice



ai_tasks= [

{'type': 'ai_call', 'phone': '713-261-7481', 'username': '1Church', 'ai_profile': {'name': 'Laurie', 'voice': 'Female - Professional', 'personality': "sdf"}},
{'type': 'ai_call', 'phone': '713-261-7481', 'username': '1Church', 'ai_profile': {'name': 'Laurie', 'voice': 'Female - Professional', 'personality': "sdf"}},
{'type': 'ai_call', 'phone': '713-261-7481', 'username': '1Church', 'ai_profile': {'name': 'Laurie', 'voice': 'Female - Professional', 'personality': "sdf"}},
{'type': 'ai_call', 'phone': '713-261-7481', 'username': '1Church', 'ai_profile': {'name': 'Laurie', 'voice': 'Female - Professional', 'personality': "sdf"}},
{'type': 'ai_call', 'phone': '713-261-7481', 'username': '1Church', 'ai_profile': {'name': 'Laurie', 'voice': 'Female - Professional', 'personality': "sdf"}},

]

response = requests.post(
                        VOICE_CALL_ENDPOINT,
                        json=ai_tasks,
                        timeout=11 * 4,
                        headers={'Content-Type': 'application/json'}
                    )