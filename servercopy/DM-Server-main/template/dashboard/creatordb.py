import os
import mysql.connector
from mysql.connector import Error

class MySQLConnection:
    def __init__(self, db_name=None):
        self.config = {
            'host': os.getenv('MYSQL_HOST', '88.99.150.24'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'dm_admin_user'),
            'password': os.getenv('MYSQL_PASSWORD', '96_B)2}2TKD+ef|')
        }
        if db_name:
            self.config['database'] = db_name
        self.connection = None
    
    def get_connection(self):
        if self.connection and self.connection.is_connected():
            return self.connection
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                print(f"✅ Connected to MySQL: {self.config.get('database', 'No DB')}")
                return self.connection
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
            return None

# Step 1: Connect without DB and create both databases if not exist
root_conn = MySQLConnection().get_connection()
if root_conn:
    root_cursor = root_conn.cursor()
    root_cursor.execute("CREATE DATABASE IF NOT EXISTS dm_database")
    root_cursor.execute("CREATE DATABASE IF NOT EXISTS clients_db")
    root_cursor.close()
    root_conn.close()

# Step 2: Connect to dm_database and create main tables
db = MySQLConnection('dm_database')
conn = db.get_connection()

if conn:
    cursor = conn.cursor()
    sql_statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            role VARCHAR(20) DEFAULT 'admin',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            client_group_id INT,
            status VARCHAR(50) DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            launched_at TIMESTAMP NULL,
            created_by INT,
            email_subject VARCHAR(500),
            email_body TEXT,
            sms_message TEXT,
            voice_file_path VARCHAR(500),
            ai_agent_profile JSON,
            social_config JSON,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS email_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            campaign_id INT NOT NULL,
            client_id INT,
            client_name VARCHAR(200),
            client_email VARCHAR(255),
            subject VARCHAR(500),
            body TEXT,
            status VARCHAR(50),
            error_message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_response JSON,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
        )
        """
        # Add sms_logs and call_logs here similarly
    ]
    try:
        for stmt in sql_statements:
            cursor.execute(stmt)
        conn.commit()
        print("✅ All tables created in dm_database!")
    except Error as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        cursor.close()
        conn.close()

# Step 3: Connect to clients_db and create clients table
client_db = MySQLConnection('clients_db').get_connection()
if client_db:
    client_cursor = client_db.cursor()
    try:
        client_cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100),
            last_name VARCHAR(100), 
            email VARCHAR(255),
            phone VARCHAR(20),
            group_id INT,
            group_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_group (group_id),
            INDEX idx_email (email),
            INDEX idx_phone (phone)
        )
        """)
        client_db.commit()
        print("✅ Clients table created in clients_db!")
    except Error as e:
        print(f"❌ Error creating clients table: {e}")
    finally:
        client_cursor.close()
        client_db.close()
