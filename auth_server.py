"""Flask web server for user registration and authentication."""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS

from tools.database import DatabaseClient
from tools.jwt_auth import hash_password, verify_password, create_jwt_token

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION")
CORS(app)

db = DatabaseClient()


@app.route("/")
def index():
    """Home page with links to register/login."""
    return render_template("index.html")


@app.route("/register", methods=["GET"])
def register_page():
    """Registration page."""
    return render_template("register.html")


@app.route("/api/register", methods=["POST"])
def register():
    """Handle user registration."""
    data = request.json
    email = data.get("email")
    password = data.get("password")
    quendoo_api_key = data.get("quendoo_api_key")
    email_api_key = data.get("email_api_key")

    if not email or not password or not quendoo_api_key:
        return jsonify({"error": "Email, password, and Quendoo API key are required"}), 400

    # Check if user already exists
    existing_user = db.get_user_by_email(email)
    if existing_user:
        return jsonify({"error": "User with this email already exists"}), 409

    # Create user
    password_hash = hash_password(password)
    user_id = db.create_user(email, password_hash, quendoo_api_key, email_api_key)

    # Generate JWT token
    token = create_jwt_token(user_id, email)

    return jsonify({
        "message": "Registration successful",
        "token": token,
        "user_id": user_id,
        "email": email
    }), 201


@app.route("/login", methods=["GET"])
def login_page():
    """Login page."""
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def login():
    """Handle user login."""
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Get user
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # Verify password
    if not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    # Generate JWT token
    token = create_jwt_token(user["id"], user["email"])

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user_id": user["id"],
        "email": user["email"]
    }), 200


@app.route("/dashboard")
def dashboard():
    """User dashboard showing API keys."""
    return render_template("dashboard.html")


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Get user profile (requires Authorization header with JWT token)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid authorization header"}), 401

    token = auth_header.replace("Bearer ", "")
    from tools.jwt_auth import decode_jwt_token
    payload = decode_jwt_token(token)

    if not payload:
        return jsonify({"error": "Invalid or expired token"}), 401

    user_id = payload.get("user_id")
    user = db.get_user_by_id(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": user["id"],
        "email": user["email"],
        "has_quendoo_api_key": bool(user["quendoo_api_key"]),
        "has_email_api_key": bool(user.get("email_api_key"))
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("AUTH_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
