-- Create main database
CREATE DATABASE IF NOT EXISTS campaign_db;
USE campaign_db;

-- Users table for authentication
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
);

-- Enhanced campaigns table
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
);

-- Email logs table
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
);

-- SMS logs table
CREATE TABLE IF NOT EXISTS sms_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id INT NOT NULL,
    client_id INT,
    client_name VARCHAR(200),
    client_phone VARCHAR(20),
    message TEXT,
    status VARCHAR(50),
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_response JSON,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

-- Call logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id INT NOT NULL,
    client_id INT,
    client_name VARCHAR(200),
    client_phone VARCHAR(20),
    call_type VARCHAR(50),
    agent_name VARCHAR(100),
    conversation JSON,
    status VARCHAR(50),
    duration INT,
    error_message TEXT,
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_response JSON,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, first_name, last_name, role) 
VALUES ('admin', 'admin@example.com', 'pbkdf2:sha256:600000$YOUR_HASH', 'Admin', 'User', 'admin')
ON DUPLICATE KEY UPDATE username=username;











-- Create clients database (if not exists)
CREATE DATABASE IF NOT EXISTS clients_db;
USE clients_db;

-- Clients table
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
);

-- Sample data
INSERT INTO clients (first_name, last_name, email, phone, group_id, group_name) VALUES
('John', 'Doe', 'john.doe@example.com', '+1234567890', 1, 'VIP Customers'),
('Jane', 'Smith', 'jane.smith@example.com', '+0987654321', 1, 'VIP Customers'),
('Bob', 'Johnson', 'bob.johnson@example.com', '+1122334455', 2, 'Regular Customers'),
('Alice', 'Brown', 'alice.brown@example.com', '+5566778899', 2, 'Regular Customers'),
('Charlie', 'Wilson', 'charlie.wilson@example.com', '+9988776655', 3, 'Prospects')
ON DUPLICATE KEY UPDATE first_name=VALUES(first_name);











USE campaign_db;

ALTER TABLE campaigns 
    ADD COLUMN email_attachment_file VARCHAR(500),
    ADD COLUMN email_attachment_url VARCHAR(500),
    ADD COLUMN email_attachment_type VARCHAR(10);



