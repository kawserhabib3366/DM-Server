#!/usr/bin/env python3
"""
Debug script for Campaign Dashboard login issues
Run this script to diagnose and fix common login problems
"""

import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash

def test_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    
    try:
        # Try to connect to the campaign database
        db_uri = 'mysql+pymysql://root:kawser@localhost/campaign_db'
        engine = create_engine(db_uri)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("💡 Check your MySQL server and credentials")
        return False

def check_users_table():
    """Check if users table exists and has data"""
    print("\n🔍 Checking users table...")
    
    try:
        db_uri = 'mysql+pymysql://root:kawser@localhost/campaign_db'
        engine = create_engine(db_uri)
        
        with engine.connect() as connection:
            # Check if users table exists
            result = connection.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = 'campaign_db' 
                AND table_name = 'users'
            """))
            
            table_exists = result.fetchone()[0] > 0
            
            if not table_exists:
                print("❌ Users table does not exist!")
                print("💡 Run the database schema SQL first")
                return False
            
            print("✅ Users table exists")
            
            # Check user count
            result = connection.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.fetchone()[0]
            print(f"ℹ️  Found {user_count} users in database")
            
            if user_count == 0:
                print("❌ No users found in database")
                return False
                
            # Check admin user specifically
            result = connection.execute(text("SELECT username, email, is_active FROM users WHERE username = 'admin'"))
            admin_user = result.fetchone()
            
            if admin_user:
                print(f"✅ Admin user found: {admin_user.username} ({admin_user.email})")
                print(f"   Active: {admin_user.is_active}")
                return True
            else:
                print("❌ Admin user not found")
                return False
                
    except Exception as e:
        print(f"❌ Error checking users table: {str(e)}")
        return False

def create_admin_user():
    """Create admin user with proper password hash"""
    print("\n🔧 Creating admin user...")
    
    try:
        db_uri = 'mysql+pymysql://root:kawser@localhost/campaign_db'
        engine = create_engine(db_uri)
        
        # Generate proper password hash
        password_hash = generate_password_hash('admin123')
        print(f"Generated password hash: {password_hash[:50]}...")
        
        with engine.connect() as connection:
            # Delete existing admin user if any
            connection.execute(text("DELETE FROM users WHERE username = 'admin'"))
            
            # Insert new admin user
            connection.execute(text("""
                INSERT INTO users (username, email, password_hash, first_name, last_name, role, is_active) 
                VALUES ('admin', 'admin@example.com', :password_hash, 'Admin', 'User', 'admin', 1)
            """), {"password_hash": password_hash})
            
            connection.commit()
            print("✅ Admin user created successfully!")
            
        # Test the password
        test_password_verification(password_hash)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        return False

def test_password_verification(password_hash):
    """Test password verification"""
    print("\n🔍 Testing password verification...")
    
    try:
        # Test correct password
        if check_password_hash(password_hash, 'admin123'):
            print("✅ Password verification works correctly")
            return True
        else:
            print("❌ Password verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing password: {str(e)}")
        return False

def test_flask_app():
    """Test Flask app startup"""
    print("\n🔍 Testing Flask application...")
    
    try:
        # Set environment variables
        os.environ.setdefault('SECRET_KEY', 'test-secret-key')
        
        # Try importing the app
        sys.path.insert(0, '.')
        
        print("✅ Flask app should start correctly")
        print("💡 Try running: python enhanced_campaign_dashboard.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error with Flask app: {str(e)}")
        return False

def fix_common_issues():
    """Fix common issues automatically"""
    print("\n🔧 Attempting to fix common issues...")
    
    # Create templates directory
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("✅ Created templates directory")
    
    # Create uploads directory
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        print("✅ Created uploads directory")
        
    if not os.path.exists('uploads/audio'):
        os.makedirs('uploads/audio')
        print("✅ Created uploads/audio directory")
    
    # Check for required files
    required_files = ['enhanced_campaign_dashboard.py', 'templates/login.html', 'templates/dashboard.html']
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Missing required file: {file_path}")
        else:
            print(f"✅ Found: {file_path}")

def main():
    """Main diagnostic function"""
    print("🚀 Campaign Dashboard Login Diagnostic Tool")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test 1: Database connection
    if not test_database_connection():
        all_tests_passed = False
        
    # Test 2: Users table
    if not check_users_table():
        print("\n🔧 Attempting to create admin user...")
        if not create_admin_user():
            all_tests_passed = False
    
    # Test 3: Flask app
    if not test_flask_app():
        all_tests_passed = False
    
    # Test 4: Fix common issues
    fix_common_issues()
    
    print("\n" + "=" * 50)
    
    if all_tests_passed:
        print("✅ All tests passed! Login should work now.")
        print("\n🚀 Next steps:")
        print("1. Run: python enhanced_campaign_dashboard.py")
        print("2. Go to: http://localhost:5000")
        print("3. Login with: admin / admin123")
    else:
        print("❌ Some issues found. Please fix them and try again.")
        print("\n💡 Common solutions:")
        print("1. Start MySQL server")
        print("2. Run the database schema SQL")
        print("3. Check MySQL credentials in .env file")
        print("4. Ensure all required files are present")

if __name__ == "__main__":
    main()