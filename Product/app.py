from flask import Flask, render_template ,  redirect,  url_for, jsonify
from database.database import MySqlConnection

app = Flask(__name__)
db = MySqlConnection()

@app.route("/test")
def test():
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, "SELECT * FROM products LIMIT 5")
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

if __name__ == "__main__":
    app.run(debug=True)
