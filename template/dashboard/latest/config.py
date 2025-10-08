
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost/campaign_db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    VOICE_CALL_ENDPOINT = f"{API_BASE_URL}/api/gvoice"
    SEND_EMAIL_ENDPOINT = f"{API_BASE_URL}/api/send_email"
    ALLOWED_EXTENSIONS = {"mp3", "wav", "mp4", "mpeg", "pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "zip", "xlsx", "csv"}

    # Ensure upload directories exist
    @staticmethod
    def init_app(app):
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "audio"), exist_ok=True)
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "attachments"), exist_ok=True)


