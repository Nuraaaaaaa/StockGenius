from flask import Flask, render_template ,  redirect,  url_for

app = Flask(__name__)

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
