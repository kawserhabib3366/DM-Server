
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db
from datetime import datetime

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            error_msg = "Username and password are required"
            if request.is_json:
                return jsonify({"success": False, "error": error_msg}), 400
            flash(error_msg)
            return render_template("login.html"), 400
        
        try:
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                print(f"User {username} logged in successfully")  # Debug log
                
                if request.is_json:
                    return jsonify({"success": True, "user": user.to_dict()})
                return redirect(url_for("index"))
            else:
                error_msg = "Invalid username or password"
                print(f"Login failed for user: {username}")  # Debug log
                if request.is_json:
                    return jsonify({"success": False, "error": error_msg}), 401
                flash(error_msg)
                return render_template("login.html"), 401
                
        except Exception as e:
            error_msg = "Login system error. Please try again."
            print(f"Login error: {str(e)}")  # Debug log
            if request.is_json:
                return jsonify({"success": False, "error": error_msg}), 500
            flash(error_msg)
            return render_template("login.html"), 500
    
    # GET request - show login form
    return render_template("login.html")

@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({"success": True, "message": "Logged out successfully"}))
    return redirect(url_for("auth.login"))

@auth_bp.route("/api/profile", methods=["GET", "PUT"])
@login_required
def profile():
    if request.method == "PUT":
        data = request.get_json()
        
        if "first_name" in data:
            current_user.first_name = data["first_name"]
        if "last_name" in data:
            current_user.last_name = data["last_name"]
        if "email" in data:
            current_user.email = data["email"]
        
        # Handle password change
        if "new_password" in data and data["new_password"]:
            if not data.get("current_password"):
                return jsonify({"success": False, "error": "Current password required"}), 400
            
            if not current_user.check_password(data["current_password"]):
                return jsonify({"success": False, "error": "Current password is incorrect"}), 400
            
            current_user.set_password(data["new_password"])
        
        try:
            db.session.commit()
            return jsonify({"success": True, "user": current_user.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({"success": True, "user": current_user.to_dict()})


