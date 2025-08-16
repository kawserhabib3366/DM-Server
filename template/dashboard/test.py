#!/usr/bin/env python3
"""
Test script for new Campaign Dashboard features
Run this to verify email attachments and batch API calls work correctly
"""

import requests
import json
import os
from typing import List, Dict

# Configuration
DASHBOARD_BASE = "http://localhost:5000"
API_BASE = "http://localhost:8000"  # Your API server
USERNAME = "admin"
PASSWORD = "admin123"

class CampaignDashboardTester:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False
        
    def login(self) -> bool:
        """Login to dashboard"""
        print("🔐 Testing login...")
        
        try:
            response = self.session.post(f"{DASHBOARD_BASE}/login", json={
                "username": USERNAME,
                "password": PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Login successful")
                    self.logged_in = True
                    return True
                    
            print("❌ Login failed")
            return False
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_attachment_upload(self) -> bool:
        """Test file attachment upload"""
        print("\n📎 Testing attachment upload...")
        
        if not self.logged_in:
            print("❌ Must login first")
            return False
        
        # Create a test file
        test_file_content = "This is a test document for email attachment testing."
        test_file_name = "test_attachment.txt"
        
        try:
            with open(test_file_name, 'w') as f:
                f.write(test_file_content)
            
            # Upload the file
            with open(test_file_name, 'rb') as f:
                files = {'attachment': (test_file_name, f, 'text/plain')}
                response = self.session.post(f"{DASHBOARD_BASE}/api/upload-attachment", files=files)
            
            # Clean up
            os.remove(test_file_name)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ File upload successful: {data.get('filename')}")
                    return True
                    
            print(f"❌ File upload failed: {response.text}")
            return False
            
        except Exception as e:
            print(f"❌ File upload error: {e}")
            return False
    
    def test_batch_gvoice_api(self) -> bool:
        """Test batch /gvoice API endpoint"""
        print("\n📞 Testing batch /gvoice API...")
        
        # Test data for batch API call
        test_tasks = [
            {
                "type": "sms",
                "phone": "+1234567890",
                "username": "Test User 1",
                "msg": "Test SMS message 1"
            },
            {
                "type": "sms", 
                "phone": "+0987654321",
                "username": "Test User 2",
                "msg": "Test SMS message 2"
            },
            {
                "type": "ai_call",
                "phone": "+1122334455",
                "username": "Test User 3",
                "msg": "AI Agent: TestBot\nPersonality: Friendly\nScript: Hello, this is a test call"
            }
        ]
        
        try:
            response = requests.post(
                f"{API_BASE}/gvoice",
                json=test_tasks,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Batch API call successful")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Batch API call failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to API server at {API_BASE}")
            print(f"   Make sure your API server is running on {API_BASE}")
            return False
        except Exception as e:
            print(f"❌ Batch API error: {e}")
            return False
    
    def test_email_api_with_attachment(self) -> bool:
        """Test email API with attachment support"""
        print("\n📧 Testing email API with attachment...")
        
        test_email_data = {
            "receiver_email": "test@example.com",
            "subject": "Test Email with Attachment",
            "html_body": "<html><body><h1>Test Email</h1><p>This is a test email with attachment support.</p></body></html>",
            "attachment": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/api/send_email",
                json=test_email_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Email API with attachment successful")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Email API failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to API server at {API_BASE}")
            print(f"   Make sure your API server is running on {API_BASE}")
            return False
        except Exception as e:
            print(f"❌ Email API error: {e}")
            return False
    
    def test_dashboard_connectivity(self) -> bool:
        """Test dashboard server connectivity"""
        print("\n🌐 Testing dashboard connectivity...")
        
        try:
            response = requests.get(f"{DASHBOARD_BASE}/api/test-connection", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Dashboard server reachable")
                
                if data.get('success'):
                    print("✅ All dashboard systems operational")
                    return True
                else:
                    print("⚠️  Dashboard has some issues:")
                    for test_name, test_result in data.get('tests', {}).items():
                        status = "✅" if test_result['status'] == 'success' else "❌"
                        print(f"   {status} {test_name}: {test_result['message']}")
                    return False
            else:
                print(f"❌ Dashboard server returned HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to dashboard at {DASHBOARD_BASE}")
            print(f"   Make sure the dashboard is running: python enhanced_campaign_dashboard.py")
            return False
        except Exception as e:
            print(f"❌ Dashboard connectivity error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Campaign Dashboard Feature Tests")
        print("=" * 50)
        
        tests = [
            ("Dashboard Connectivity", self.test_dashboard_connectivity),
            ("Login System", self.login),
            ("Attachment Upload", self.test_attachment_upload),
            ("Batch /gvoice API", self.test_batch_gvoice_api),
            ("Email API with Attachment", self.test_email_api_with_attachment)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                results[test_name] = False
        
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✅ PASSED" if passed_test else "❌ FAILED"
            print(f"{status} | {test_name}")
            if passed_test:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Your new features are working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            print("\n💡 Common solutions:")
            print("   - Start the dashboard: python enhanced_campaign_dashboard.py")
            print("   - Start your API server on the correct port")
            print("   - Check database connection")
            print("   - Verify file permissions for uploads/")
        
        return passed == total

def main():
    """Main test function"""
    tester = CampaignDashboardTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 Next steps:")
        print("1. Open http://localhost:5000")
        print("2. Login with admin/admin123") 
        print("3. Try creating a campaign with attachments")
        print("4. Monitor the batch API calls in your server logs")
        
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())