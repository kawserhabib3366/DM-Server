
import os
from datetime import datetime
from flask import jsonify, request, current_app
from werkzeug.utils import secure_filename

def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

def upload_audio_file():
    """Handle audio file uploads"""
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided"}), 400
    
    file = request.files["audio"]
    
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], "audio", filename)
        file.save(filepath)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "filepath": filepath
        })
    
    return jsonify({"success": False, "error": "Invalid file type"}), 400


