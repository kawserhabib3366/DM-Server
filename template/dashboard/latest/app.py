
import os
from flask import Flask, render_template, redirect, url_for, jsonify, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash

from config import Config
from models import db, User
from database import mysql_conn
from auth import auth_bp
from campaigns import campaigns_bp
from analytics import analytics_bp
from utils import upload_audio_file


# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize SQLAlchemy
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access the dashboard."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure upload directories exist
with app.app_context():
    Config.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(campaigns_bp)
app.register_blueprint(analytics_bp)

# ============================================================================
# Utility Functions
# ============================================================================

@app.route("/api/upload-audio", methods=["POST"])
def upload_audio():
    return upload_audio_file()


# ============================================================================
# Protected Routes
# ============================================================================

@app.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("dashboard.html")
    else:
        return redirect(url_for("auth.login"))


@app.route("/api/test-connection")
def test_connection():
    """Test database connection and API connectivity"""
    test_results = {}
    
    # Test database connection
    conn = mysql_conn.get_connection()
    if conn:
        conn.close()
        test_results["database"] = {"status": "success", "message": "Database connection successful"}
    else:
        test_results["database"] = {"status": "failed", "message": "Database connection failed"}
    
    # Test your API endpoints
    try:
        test_response = requests.get(f"{app.config["API_BASE_URL"]}/", timeout=5)
        test_results["api_server"] = {"status": "success", "message": f"API server reachable at {app.config["API_BASE_URL"]}"}
    except requests.exceptions.RequestException as e:
        test_results["api_server"] = {"status": "failed", "message": f"API server unreachable: {str(e)}"}
    
    all_success = all(result["status"] == "success" for result in test_results.values())
    
    return jsonify({
        "success": all_success,
        "tests": test_results
    })


@app.route("/uploads/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(os.path.join(app.root_path, app.config["UPLOAD_FOLDER"], "audio"), filename, mimetype="audio/mpeg")


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


def create_default_admin():
    """Create default admin user if none exists"""
    with app.app_context():
        if not User.query.filter_by(username="admin").first():
            admin_user = User(
                username="admin",
                email="admin@example.com",
                first_name="Admin",
                last_name="User",
                role="admin"
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created: admin/admin123")

# ============================================================================
# Main Application Entry Point
# ============================================================================

if __name__ == "__main__":
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_admin()
    
    print(f"Enhanced Campaign Dashboard starting...")
    print(f"Using API base URL: {app.config["API_BASE_URL"]}")
    print(f"Voice Call Endpoint: {app.config["VOICE_CALL_ENDPOINT"]}")
    print(f"Send Email Endpoint: {app.config["SEND_EMAIL_ENDPOINT"]}")
    print(f"Default admin login: admin/admin123")
    
    # Run the Flask application
    app.run(debug=True, host="0.0.0.0", port=5000)


