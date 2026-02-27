from flask import Flask, render_template ,  redirect,  url_for, jsonify
from database.database import MySqlConnection
from werkzeug.security import generate_password_hash
app = Flask(__name__)
db = MySqlConnection()

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
if __name__ == "__main__":
    app.run(debug=True)
