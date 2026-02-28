from flask import Flask, render_template ,  redirect, session, url_for, jsonify, request
from database.database import MySqlConnection
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
app = Flask(__name__)
app.secret_key = "9#kL2!xQz@81bP$7vR_stockgenius_2026"
db = MySqlConnection()


def login_required():
    return "user_id" in session

@app.route("/test")
def test():
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, "SELECT * FROM users LIMIT 5")
        return jsonify(rows)
    finally:
        db.close_connection(conn)

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/inventory")
def inventory():
    return render_template("inventory.html")

@app.route("/alerts")
def alerts():
    return render_template("alert.html")

@app.route("/logout")
def logout():
  
    return redirect(url_for("login"))

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.post("/api/signup")
def signup():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"message": "All fields required"}), 400

    conn = db.open_connection()
    try:
        # Check if email exists
        existing = db.run_query(
            conn,
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        if existing:
            return jsonify({"message": "Email already exists"}), 409

        # Hash password (VERY IMPORTANT)
        hashed_password = generate_password_hash(password)

        db.execute_update(
            conn,
            "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )

        return jsonify({"message": "Account created successfully"}), 201

    finally:
        db.close_connection(conn)

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    conn = db.open_connection()
    try:
        rows = db.run_query(
            conn,
            "SELECT id, full_name, email, password_hash FROM users WHERE email=%s LIMIT 1",
            (email,)
        )
        if not rows:
            return jsonify({"message": "Invalid email or password"}), 401

        user = rows[0]
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Invalid email or password"}), 401


        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]

        return jsonify({"message": "Login success"}), 200
    finally:
        db.close_connection(conn)
        
if __name__ == "__main__":
    app.run(debug=True)
