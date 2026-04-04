from flask import Flask, render_template ,  redirect, session, url_for, jsonify, request
from database.database import MySqlConnection
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from functools import wraps
import subprocess
import sys
import os
    
app = Flask(__name__)
app.secret_key = "9#kL2!xQz@81bP$7vR_stockgenius_2026"
db = MySqlConnection()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


""" 
@app.route("/test")
def test():
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, "SELECT * FROM users LIMIT 5")
        return jsonify(rows)
    finally:
        db.close_connection(conn) """

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", active_page="dashboard", user_name=session.get("user_name"),
        user_role=session.get("role"))

@app.route("/inventory")
@login_required
def inventory():
    page = request.args.get("page", 1, type=int)
    per_page = 8
    offset = (page - 1) * per_page

    product_images = {
        "Chairs": url_for("static", filename="images/chairs.jfif"),
        "Tables": "https://images.unsplash.com/photo-1503602642458-232111445657",
        "Bookcases": url_for("static", filename="images/bookcases.avif"),
        "Phones": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9",
        "Machines": url_for("static", filename="images/machines.avif"),
        "Storage": url_for("static", filename="images/storage.avif"),
        "Binders": "https://images.unsplash.com/photo-1586281380117-5a60ae2050cc",
        "Accessories": url_for("static", filename="images/accessories.avif"),
        "Supplies":url_for("static", filename="images/supplies.avif"),
        "Copiers": url_for("static", filename="images/copiers.avif"),
        "Appliances": url_for("static", filename="images/appliances.avif"),
        "Art": "https://images.unsplash.com/photo-1513364776144-60967b0f800f",
        "Paper": "https://images.unsplash.com/photo-1455390582262-044cdead277a",
        "Labels": "https://images.unsplash.com/photo-1586075010923-2dd4570fb338",
        "Envelopes":url_for("static", filename="images/envelopes.avif"),
        "Fasteners": "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc",
        "Furnishings": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85"
    }

    conn = db.open_connection()
    try:
        count_row = db.run_query(conn, """
            SELECT COUNT(*) AS total
            FROM (
                SELECT sub_category
                FROM ml_inventory
                GROUP BY sub_category
            ) AS grouped
        """)[0]

        total_items = int(count_row["total"])
        total_pages = (total_items + per_page - 1) // per_page

        products = db.run_query(conn, """
            SELECT
                sub_category,
                ROUND(SUM(sales), 2) AS total_sales,
                SUM(quantity) AS total_quantity,
                ROUND(AVG(stock_level), 0) AS avg_stock_level,
                ROUND(AVG(reorder_point), 0) AS avg_reorder_point,
                MAX(low_stock) AS low_stock,
                MAX(near_expiry) AS near_expiry,
                ROUND(SUM(profit), 2) AS total_profit,
                 ROUND(AVG(discount) * 100, 1) AS avg_discount
            FROM ml_inventory
            GROUP BY sub_category
            ORDER BY sub_category
            LIMIT %s OFFSET %s
        """, (per_page, offset))

        # attach image to each grouped product
        for product in products:
            product["image"] = product_images.get(
                product["sub_category"],
                "https://via.placeholder.com/300x160?text=StockGenius"
            )

        return render_template(
            "inventory.html",
            products=products,
            active_page="inventory",
            user_name=session.get("user_name"),
        user_role=session.get("role"),
            page=page,
            total_pages=total_pages
        )

    finally:
        db.close_connection(conn)

@app.route("/alerts")
@login_required
def alerts():
    conn = db.open_connection()
    try:
        # Critical alerts: anomaly + very low stock
        critical_rows = db.run_query(conn, """
            SELECT
                sub_category,
                stock_level,
                reorder_point,
                days_to_expiry,
                quantity,
                sales,
                profit,
                is_anomaly,
                low_stock,
                near_expiry
            FROM ml_inventory
            WHERE is_anomaly = 1
               OR (low_stock = 1 AND stock_level <= reorder_point * 0.5)
               OR (near_expiry = 1 AND days_to_expiry <= 7)
            ORDER BY is_anomaly DESC, days_to_expiry ASC, stock_level ASC
            LIMIT 5
        """)

        # Warning alerts: low stock or near expiry
        warning_rows = db.run_query(conn, """
            SELECT
                sub_category,
                stock_level,
                reorder_point,
                days_to_expiry,
                quantity,
                sales,
                profit,
                is_anomaly,
                low_stock,
                near_expiry
            FROM ml_inventory
            WHERE (low_stock = 1 OR near_expiry = 1)
              AND is_anomaly = 0
            ORDER BY near_expiry DESC, low_stock DESC, stock_level ASC
            LIMIT 5
        """)

        # ML insights: top demand products
        ml_rows = db.run_query(conn, """
            SELECT
                sub_category,
                SUM(quantity) AS total_quantity,
                ROUND(SUM(sales), 2) AS total_sales,
                ROUND(AVG(profit_margin), 2) AS avg_margin
            FROM ml_inventory
            GROUP BY sub_category
            ORDER BY total_quantity DESC
            LIMIT 3
        """)

        alerts_data = []

        # Critical cards
        for row in critical_rows:
            if row["is_anomaly"] == 1:
                alerts_data.append({
                    "type": "critical",
                    "icon": "⛔",
                    "title": "Anomaly Detected",
                    "subtitle": f"Product: {row['sub_category']}",
                    "message": f"{row['sub_category']} has unusual inventory behavior. Review this item immediately.",
                    "action": "Review Alert",
                    "time": "Just now"
                })
            elif row["near_expiry"] == 1 and row["days_to_expiry"] is not None and row["days_to_expiry"] <= 7:
                alerts_data.append({
                    "type": "critical",
                    "icon": "🗓️",
                    "title": "Expiry Alert",
                    "subtitle": f"Product: {row['sub_category']}",
                    "message": f"{row['sub_category']} expires in {int(row['days_to_expiry'])} days.",
                    "action": "Apply Discount",
                    "time": "Recently"
                })
            elif row["low_stock"] == 1:
                alerts_data.append({
                    "type": "critical",
                    "icon": "📦",
                    "title": "Critical Stock Level",
                    "subtitle": f"Product: {row['sub_category']}",
                    "message": f"{row['sub_category']} stock is critically low ({int(row['stock_level'])} left). Immediate reorder required.",
                    "action": "Reorder Now",
                    "time": "Recently"
                })

        # Warning cards
        for row in warning_rows:
            if row["near_expiry"] == 1 and row["days_to_expiry"] is not None:
                alerts_data.append({
                    "type": "warning",
                    "icon": "⚠️",
                    "title": "Near Expiry Warning",
                    "subtitle": f"Product: {row['sub_category']}",
                    "message": f"{row['sub_category']} will expire in {int(row['days_to_expiry'])} days.",
                    "action": "Review Item",
                    "time": "Recently"
                })
            elif row["low_stock"] == 1:
                alerts_data.append({
                    "type": "warning",
                    "icon": "⚠️",
                    "title": "Low Stock Alert",
                    "subtitle": f"Product: {row['sub_category']}",
                    "message": f"{row['sub_category']} is below reorder point. Only {int(row['stock_level'])} units remaining.",
                    "action": "Review Order",
                    "time": "Recently"
                })

        # ML insight cards
        for row in ml_rows:
            alerts_data.append({
                "type": "ml",
                "icon": "🤖",
                "title": "AI Demand Forecast",
                "subtitle": f"Product: {row['sub_category']}",
                "message": f"{row['sub_category']} shows high demand with {int(row['total_quantity'])} units sold.",
                "action": "View Forecast",
                "time": "Today"
            })

        # counts for tabs
        counts = {
            "all": len(alerts_data),
            "critical": len([a for a in alerts_data if a["type"] == "critical"]),
            "warning": len([a for a in alerts_data if a["type"] == "warning"]),
            "info": len([a for a in alerts_data if a["type"] == "info"]),
            "ml": len([a for a in alerts_data if a["type"] == "ml"]),
        }

        return render_template(
            "alert.html",
            active_page="alerts",
            user_name=session.get("user_name"),
        user_role=session.get("role"),
            alerts_data=alerts_data,
            counts=counts
        )

    finally:
        db.close_connection(conn)
        

@app.route("/analytics")
@login_required
def analytic():
    return render_template(
        "analytic.html",
        active_page="analytic",
        user_name=session.get("user_name"),
        user_role=session.get("role")
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    conn = db.open_connection()
    try:
        users = db.run_query(conn, """
            SELECT id, full_name, email, role, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        return render_template(
            "admin_users.html",
            users=users,
            active_page="admin_users",
            user_name=session.get("user_name"),
            user_role=session.get("role")
        )
    finally:
        db.close_connection(conn)


@app.route("/admin/users/create")
@admin_required
def admin_create_user_page():
    return render_template(
        "admin_create_user.html",
        active_page="admin_create_user",
        user_name=session.get("user_name"),
        user_role=session.get("role")
    )

@app.route("/api/admin/users", methods=["POST"])
@admin_required
def admin_create_user():
    data = request.get_json() or {}

    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "staff").strip().lower()

    # full name validation
    name_parts = full_name.split()
    if len(name_parts) < 2:
        return jsonify({
            "message": "Full name must contain at least 2 words."
        }), 400

    # email validation
    if not email:
        return jsonify({
            "message": "Email is required."
        }), 400

    # role validation
    if role not in ["admin", "staff"]:
        return jsonify({
            "message": "Invalid role selected."
        }), 400

    # password validation
    if len(password) < 8:
        return jsonify({
            "message": "Password must be at least 8 characters long."
        }), 400

    if not any(char.isupper() for char in password):
        return jsonify({
            "message": "Password must contain at least one uppercase letter."
        }), 400

    if not any(char.islower() for char in password):
        return jsonify({
            "message": "Password must contain at least one lowercase letter."
        }), 400

    if not any(char.isdigit() for char in password):
        return jsonify({
            "message": "Password must contain at least one number."
        }), 400

    conn = db.open_connection()
    try:
        existing = db.run_query(
            conn,
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        if existing:
            return jsonify({
                "message": "Email already exists."
            }), 409

        password_hash = generate_password_hash(password)

        db.execute_update(
            conn,
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (full_name, email, password_hash, role)
        )

        return jsonify({
            "message": "User created successfully."
        }), 201

    finally:
        db.close_connection(conn)


@app.route("/api/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    if session.get("user_id") == user_id:
        return jsonify({"message": "You cannot delete your own admin account while logged in."}), 400

    conn = db.open_connection()
    try:
        db.execute_update(conn, "DELETE FROM users WHERE id = %s", (user_id,))
        return jsonify({"message": "User deleted successfully."}), 200
    finally:
        db.close_connection(conn)
        
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/admin/users/<int:user_id>/update", methods=["POST"])
@admin_required
def admin_update_user(user_id):
    data = request.get_json() or {}

    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "staff").strip().lower()

    if not full_name or not email:
        return jsonify({"message": "Name and email are required."}), 400

    if role not in ["admin", "staff"]:
        return jsonify({"message": "Invalid role."}), 400

    conn = db.open_connection()
    try:
        existing = db.run_query(
            conn,
            "SELECT id FROM users WHERE email = %s AND id != %s",
            (email, user_id)
        )

        if existing:
            return jsonify({"message": "Email already used by another user."}), 409

        if password:
            password_hash = generate_password_hash(password)
            db.execute_update(conn, """
                UPDATE users
                SET full_name = %s, email = %s, password_hash = %s, role = %s
                WHERE id = %s
            """, (full_name, email, password_hash, role, user_id))
        else:
            db.execute_update(conn, """
                UPDATE users
                SET full_name = %s, email = %s, role = %s
                WHERE id = %s
            """, (full_name, email, role, user_id))

        return jsonify({"message": "User updated successfully."}), 200
    finally:
        db.close_connection(conn)
        
@app.route("/signup")
def signup_page():
    return redirect(url_for("login"))

@app.route("/admin/users/edit/<int:user_id>")
@admin_required
def admin_edit_user_page(user_id):
    conn = db.open_connection()
    try:
        rows = db.run_query(
            conn,
            """
            SELECT id, full_name, email, role
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        if not rows:
            return redirect(url_for("admin_users"))

        user = rows[0]

        return render_template(
            "admin_edit_user.html",
            user=user,
            active_page="admin_users",
            user_name=session.get("user_name"),
            user_role=session.get("role")
        )
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
           "SELECT id, full_name, email, password_hash, role FROM users WHERE email=%s LIMIT 1",
            (email,)
        )
        if not rows:
            return jsonify({"message": "Invalid email or password"}), 401

        user = rows[0]
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Invalid email or password"}), 401


        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]
        session["role"] = user["role"]
        return jsonify({
            "message": "Login success",
            "role": user["role"],
            "redirect": "/dashboard"
        }), 200
    finally:
        db.close_connection(conn)
        

@app.route("/api/dashboard/stats")
@login_required
def dashboard_stats():
    conn = db.open_connection()
    try:
        row = db.run_query(conn, """
            SELECT
                COUNT(*) AS total_records,
                SUM(low_stock) AS low_stock_count,
                SUM(near_expiry) AS near_expiry_count,
                SUM(is_anomaly) AS anomaly_count,
                ROUND(SUM(sales), 2) AS total_sales,
                COUNT(DISTINCT sub_category) AS total_products,
                ROUND(AVG(sales), 2) AS avg_order_value
            FROM ml_inventory
        """)[0]

        return jsonify({
            "total_products": int(row["total_products"] or 0),
            "total_records": int(row["total_records"] or 0),
            "low_stock": int(row["low_stock_count"] or 0),
            "near_expiry": int(row["near_expiry_count"] or 0),
            "anomaly_count": int(row["anomaly_count"] or 0),
            "total_sales": float(row["total_sales"] or 0),
            "avg_order_value": float(row["avg_order_value"] or 0),
        })
    finally:
        db.close_connection(conn)


@app.route("/api/dashboard/sales_trend")
@login_required
def sales_trend():
    """
    ARIMA chart:
      Actual  → monthly SUM(sales) from ml_inventory
      Forecast → last ARIMA forecast values stored in arima_forecast table
                 (populated by save_arima_forecast.py)
    """
    conn = db.open_connection()
    try:
        # Actual monthly sales from ML dataset
        actual = db.run_query(conn, """
            SELECT
                CONCAT(year, '-', LPAD(month, 2, '0')) AS period,
                DATE_FORMAT(STR_TO_DATE(CONCAT(year,'-',month,'-01'),'%Y-%m-%d'), '%b %Y') AS label,
                ROUND(SUM(sales), 2) AS total
            FROM ml_inventory
            GROUP BY year, month
            ORDER BY year, month
        """)

        # ARIMA forecast from separate table (see save_arima_forecast.py)
        forecast = []
        try:
            forecast = db.run_query(conn, """
                SELECT label, forecast_amount AS total
                FROM arima_forecast
                ORDER BY forecast_month
            """)
        except Exception:
            pass  # table may not exist yet — chart still shows actual data

        return jsonify({
            "labels":   [r["label"]          for r in actual],
            "actual":   [float(r["total"])    for r in actual],
            "forecast": [float(r["total"])    for r in forecast] if forecast else [],
            "forecast_labels": [r["label"]   for r in forecast] if forecast else [],
        })
    finally:
        db.close_connection(conn)


@app.route("/api/dashboard/top_products")
@login_required
def top_products():
    """
    Bar chart — top sub-categories by total quantity sold (from ML dataset)
    Random Forest predicted high-demand categories appear at top naturally.
    """
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, """
            SELECT
                sub_category,
                SUM(quantity)        AS total_qty,
                ROUND(SUM(sales), 2) AS total_sales,
                ROUND(AVG(profit_margin), 1) AS avg_margin
            FROM ml_inventory
            GROUP BY sub_category
            ORDER BY total_qty DESC
            LIMIT 8
        """)

        return jsonify({
            "labels":  [r["sub_category"]      for r in rows],
            "values":  [int(r["total_qty"])     for r in rows],
            "sales":   [float(r["total_sales"]) for r in rows],
            "margins": [float(r["avg_margin"])  for r in rows],
        })
    finally:
        db.close_connection(conn)


@app.route("/api/dashboard/anomalies")
@login_required
def anomaly_summary():
    """
    Isolation Forest results — anomaly breakdown by sub-category
    is_anomaly = 1 means flagged by your IF model
    """
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, """
            SELECT
                sub_category,
                COUNT(*) AS anomaly_count,
                ROUND(AVG(discount) * 100, 1) AS avg_discount_pct,
                ROUND(AVG(profit), 2)          AS avg_profit
            FROM ml_inventory
            WHERE is_anomaly = 1
            GROUP BY sub_category
            ORDER BY anomaly_count DESC
            LIMIT 10
        """)

        total = db.run_query(conn, """
            SELECT
                SUM(is_anomaly)  AS total_anomalies,
                COUNT(*)         AS total_rows
            FROM ml_inventory
        """)[0]

        return jsonify({
            "breakdown":        rows,
            "total_anomalies":  int(total["total_anomalies"] or 0),
            "total_rows":       int(total["total_rows"]      or 0),
        })
    finally:
        db.close_connection(conn)


@app.route("/api/dashboard/recent_alerts")
@login_required
def recent_alerts():
    """
    Activity table — show anomalies, low stock, near expiry rows
    sourced entirely from ML-computed columns in ml_inventory
    """
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, """
            SELECT
                sub_category,
                state,
                region,
                ROUND(sales, 2)          AS sales,
                quantity,
                ROUND(discount * 100, 0) AS discount_pct,
                ROUND(profit, 2)         AS profit,
                ROUND(profit_margin, 1)  AS profit_margin,
                stock_level,
                reorder_point,
                days_to_expiry,
                near_expiry,
                low_stock,
                is_anomaly,
                order_date,
                CASE
                    WHEN is_anomaly = 1  THEN 'Anomaly Detected'
                    WHEN low_stock  = 1  THEN 'Low Stock'
                    WHEN near_expiry = 1 THEN 'Near Expiry'
                    ELSE 'Normal'
                END AS alert_type,
                CASE
                    WHEN is_anomaly = 1 THEN 'error'
                    WHEN low_stock  = 1 THEN 'warning'
                    WHEN near_expiry= 1 THEN 'warning'
                    ELSE 'info'
                END AS severity
            FROM ml_inventory
            WHERE is_anomaly = 1 OR low_stock = 1 OR near_expiry = 1
            ORDER BY is_anomaly DESC, low_stock DESC, near_expiry DESC
            LIMIT 15
        """)

        for r in rows:
            r["order_date"] = str(r["order_date"]) if r["order_date"] else ""

        return jsonify(rows)
    finally:
        db.close_connection(conn)


@app.route("/api/dashboard/margin_by_category")
@login_required
def margin_by_category():
    """
    Profit margin breakdown — highlights negative margin categories
    (Tables, Bookcases, Supplies from your ML analysis)
    """
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, """
            SELECT
                sub_category,
                ROUND(SUM(profit) / SUM(sales) * 100, 2) AS margin_pct,
                ROUND(SUM(profit), 2)  AS total_profit,
                ROUND(SUM(sales),  2)  AS total_sales
            FROM ml_inventory
            GROUP BY sub_category
            ORDER BY margin_pct ASC
        """)

        return jsonify({
            "labels":  [r["sub_category"]       for r in rows],
            "margins": [float(r["margin_pct"])   for r in rows],
            "profits": [float(r["total_profit"]) for r in rows],
        })
    finally:
        db.close_connection(conn)
        

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    """
    AI chat endpoint — answers inventory questions using ML data context.
    Uses Claude API (Anthropic) if available, else falls back to
    rule-based responses from your ml_inventory table.
    """
    data    = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Please send a message."}), 400

    # ── Pull live ML context from your database ───────────────────
    conn = db.open_connection()
    try:
        stats = db.run_query(conn, """
            SELECT
                COUNT(DISTINCT sub_category)    AS total_products,
                SUM(low_stock)                  AS low_stock,
                SUM(near_expiry)                AS near_expiry,
                SUM(is_anomaly)                 AS anomalies,
                ROUND(SUM(sales), 2)            AS total_sales,
                ROUND(AVG(profit_margin), 2)    AS avg_margin
            FROM ml_inventory
        """)[0]

        low_stock_items = db.run_query(conn, """
            SELECT sub_category, AVG(stock_level) AS avg_stock, AVG(reorder_point) AS avg_reorder
            FROM ml_inventory WHERE low_stock = 1
            GROUP BY sub_category ORDER BY avg_stock ASC LIMIT 5
        """)

        near_expiry_items = db.run_query(conn, """
            SELECT sub_category, AVG(days_to_expiry) AS avg_days
            FROM ml_inventory WHERE near_expiry = 1
            GROUP BY sub_category ORDER BY avg_days ASC LIMIT 5
        """)

        top_anomalies = db.run_query(conn, """
            SELECT sub_category, COUNT(*) AS cnt, ROUND(AVG(discount)*100,1) AS avg_disc, ROUND(AVG(profit),2) AS avg_profit
            FROM ml_inventory WHERE is_anomaly = 1
            GROUP BY sub_category ORDER BY cnt DESC LIMIT 5
        """)

        top_demand = db.run_query(conn, """
            SELECT sub_category, SUM(quantity) AS qty
            FROM ml_inventory GROUP BY sub_category ORDER BY qty DESC LIMIT 5
        """)

        neg_margin = db.run_query(conn, """
            SELECT sub_category, ROUND(SUM(profit)/SUM(sales)*100,2) AS margin
            FROM ml_inventory GROUP BY sub_category
            HAVING margin < 0 ORDER BY margin ASC
        """)

    finally:
        db.close_connection(conn)

    # ── Build context string ──────────────────────────────────────
    context = f"""
You are an AI inventory assistant for StockGenius, an ML-powered inventory management system.
Answer questions about the inventory data concisely and helpfully.
Use bullet points where appropriate. Keep answers under 120 words.

LIVE ML DATA SUMMARY:
- Sub-categories: {stats['total_products']}
- Low stock items (ML flagged): {stats['low_stock']}
- Near expiry items (Days_To_Expiry < 30): {stats['near_expiry']}
- Anomalies (Isolation Forest, 5% contamination): {stats['anomalies']}
- Total sales: ${stats['total_sales']:,.2f}
- Average profit margin: {stats['avg_margin']}%

LOW STOCK SUB-CATEGORIES:
{', '.join([f"{r['sub_category']} (stock: {round(float(r['avg_stock']),0)})" for r in low_stock_items]) or 'None'}

NEAR EXPIRY:
{', '.join([f"{r['sub_category']} ({round(float(r['avg_days']),0)} days)" for r in near_expiry_items]) or 'None'}

TOP ANOMALIES (Isolation Forest):
{', '.join([f"{r['sub_category']} ({r['cnt']} flagged, avg discount {r['avg_disc']}%)" for r in top_anomalies]) or 'None'}

HIGHEST DEMAND (Random Forest target):
{', '.join([f"{r['sub_category']} ({r['qty']} units)" for r in top_demand]) or 'None'}

NEGATIVE MARGIN PRODUCTS:
{', '.join([f"{r['sub_category']} ({r['margin']}%)" for r in neg_margin]) or 'None'}
"""

    # ── Try Anthropic Claude API ──────────────────────────────────
    try:
        import anthropic
        client = anthropic.Anthropic(api_key="YOUR_ANTHROPIC_API_KEY")  # ← add your key or use env var

        history = data.get("history", [])
        messages = []
        # Add last 6 turns for context (avoid token overflow)
        for turn in history[-6:]:
            if turn.get("role") in ("user", "assistant"):
                messages.append({"role": turn["role"], "content": turn["content"]})

        # Add current message
        messages.append({"role": "user", "content": message})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=context,
            messages=messages
        )
        reply = response.content[0].text

    except Exception:
        # ── Fallback: rule-based responses using ML data ──────────
        reply = rule_based_reply(message, stats, low_stock_items,
                                 near_expiry_items, top_anomalies,
                                 top_demand, neg_margin)

    return jsonify({"reply": reply})


def rule_based_reply(msg, stats, low_stock, near_expiry, anomalies, demand, neg_margin):
    """Simple keyword-based fallback if no Anthropic API key is set."""
    msg = msg.lower()

    if any(w in msg for w in ['low stock', 'stock', 'reorder']):
        if low_stock:
            items = ', '.join([r['sub_category'] for r in low_stock])
            return f"⚠️ **Low Stock Alert**\n{int(stats['low_stock'])} transactions flagged.\nAffected: {items}.\nRecommend immediate reorder review."
        return "✅ No low stock items detected in the ML dataset."

    if any(w in msg for w in ['expir', 'expiry', 'expire']):
        if near_expiry:
            items = ', '.join([f"{r['sub_category']} ({round(float(r['avg_days']),0)} days)" for r in near_expiry])
            return f"📅 **Near Expiry**\n{int(stats['near_expiry'])} items expiring within 30 days:\n{items}"
        return "✅ No items near expiry."

    if any(w in msg for w in ['anomal', 'isolation', 'suspicious', 'fraud']):
        if anomalies:
            items = ', '.join([f"{r['sub_category']} ({r['cnt']})" for r in anomalies])
            return f"🔴 **Isolation Forest Anomalies**\n{int(stats['anomalies'])} flagged (5% contamination rate).\nTop: {items}.\nHigh discounts correlating with negative profit."
        return "✅ No anomalies detected."

    if any(w in msg for w in ['demand', 'forecast', 'arima', 'predict']):
        items = ', '.join([f"{r['sub_category']} ({r['qty']} units)" for r in demand])
        return f"📈 **ARIMA Forecast & Demand**\nTop demand sub-categories:\n{items}\nARIMA(2,1,2) forecast accuracy: 64.8%"

    if any(w in msg for w in ['margin', 'profit', 'loss', 'negative']):
        if neg_margin:
            items = ', '.join([f"{r['sub_category']} ({r['margin']}%)" for r in neg_margin])
            return f"💸 **Negative Margin Products**\n{items}\nRecommend reviewing discount strategy for these categories."
        return "✅ All products have positive margins."

    if any(w in msg for w in ['hello', 'hi', 'hey', 'help']):
        return (f"👋 Hello! I can help you with:\n"
                f"• Low stock alerts ({int(stats['low_stock'])} flagged)\n"
                f"• Near expiry items ({int(stats['near_expiry'])} items)\n"
                f"• Anomaly detection ({int(stats['anomalies'])} found)\n"
                f"• Demand forecasting\n"
                f"• Profit margin analysis\n\nWhat would you like to know?")

    if any(w in msg for w in ['summary', 'overview', 'dashboard']):
        return (f"📊 **ML Dataset Summary**\n"
                f"• {stats['total_products']} sub-categories\n"
                f"• {int(stats['low_stock'])} low stock alerts\n"
                f"• {int(stats['near_expiry'])} near expiry\n"
                f"• {int(stats['anomalies'])} anomalies detected\n"
                f"• ${float(stats['total_sales']):,.0f} total sales\n"
                f"• {stats['avg_margin']}% avg profit margin")

    return ("I can help with low stock, expiry alerts, anomalies, demand forecasting, and profit margins. "
            "Try asking: 'Which products are low on stock?' or 'Show anomalies'.")

@app.route("/api/products/<int:product_id>", methods=["GET"])
@login_required
def get_product(product_id):
    conn = db.open_connection()
    try:
        rows = db.run_query(conn, """
            SELECT
                id,
                product_name,
                category,
                sub_category,
                sales,
                quantity,
                discount,
                profit,
                order_date,
                stock_level,
                reorder_point,
                shelf_life_days
            FROM manual_products
            WHERE id = %s
            LIMIT 1
        """, (product_id,))

        if not rows:
            return jsonify({"message": "Product not found."}), 404

        product = rows[0]
        product["discount"] = float(product["discount"] or 0) * 100
        product["order_date"] = str(product["order_date"]) if product["order_date"] else ""

        return jsonify(product), 200
    finally:
        db.close_connection(conn)


@app.route("/api/products/<int:product_id>/update", methods=["POST"])
@login_required
def update_product(product_id):
    data = request.get_json() or {}

    product_name = (data.get("product_name") or "").strip()
    category = (data.get("category") or "").strip()
    sub_category = (data.get("sub_category") or "").strip()

    if not product_name or not category or not sub_category:
        return jsonify({"message": "Product name, category, and sub-category are required."}), 400

    try:
        sales = float(data.get("sales", 0) or 0)
        quantity = int(data.get("quantity", 0) or 0)
        discount_input = float(data.get("discount", 0) or 0)
        profit = float(data.get("profit", 0) or 0)
        stock_level = int(data.get("stock_level", 0) or 0)
        reorder_point = int(data.get("reorder_point", 0) or 0)
        shelf_life_days = int(data.get("shelf_life_days", 365) or 365)
    except ValueError:
        return jsonify({"message": "Please enter valid numeric values."}), 400

    if discount_input < 0 or discount_input > 100:
        return jsonify({"message": "Discount must be between 0 and 100 percent."}), 400

    discount_value = discount_input / 100.0

    rebuild_script = os.path.join(BASE_DIR, "run_once_import.py")
    forecast_script = os.path.join(BASE_DIR, "save_arima_forecast.py")

    conn = db.open_connection()
    try:
        existing = db.run_query(conn, "SELECT id FROM manual_products WHERE id = %s", (product_id,))
        if not existing:
            return jsonify({"message": "Product not found."}), 404

        db.execute_update(conn, """
            UPDATE manual_products
            SET
                product_name = %s,
                category = %s,
                sub_category = %s,
                sales = %s,
                quantity = %s,
                discount = %s,
                profit = %s,
                order_date = %s,
                stock_level = %s,
                reorder_point = %s,
                shelf_life_days = %s
            WHERE id = %s
        """, (
            product_name,
            category,
            sub_category,
            sales,
            quantity,
            discount_value,
            profit,
            data.get("order_date") or None,
            stock_level,
            reorder_point,
            shelf_life_days,
            product_id
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Database update failed: {str(e)}"}), 500

    finally:
        db.close_connection(conn)

    try:
        subprocess.run(
            [sys.executable, rebuild_script],
            check=True,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

        subprocess.run(
            [sys.executable, forecast_script],
            check=True,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

    except subprocess.CalledProcessError as e:
        return jsonify({
            "message": "Product updated, but rebuild failed.",
            "error": e.stderr or e.stdout or str(e)
        }), 500

    return jsonify({"message": "Product updated successfully."}), 200


@app.route("/api/products/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    rebuild_script = os.path.join(BASE_DIR, "run_once_import.py")
    forecast_script = os.path.join(BASE_DIR, "save_arima_forecast.py")

    conn = db.open_connection()
    try:
        existing = db.run_query(conn, "SELECT id FROM manual_products WHERE id = %s", (product_id,))
        if not existing:
            return jsonify({"message": "Product not found."}), 404

        db.execute_update(conn, "DELETE FROM manual_products WHERE id = %s", (product_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Database delete failed: {str(e)}"}), 500

    finally:
        db.close_connection(conn)

    try:
        subprocess.run(
            [sys.executable, rebuild_script],
            check=True,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

        subprocess.run(
            [sys.executable, forecast_script],
            check=True,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

    except subprocess.CalledProcessError as e:
        return jsonify({
            "message": "Product deleted, but rebuild failed.",
            "error": e.stderr or e.stdout or str(e)
        }), 500

    return jsonify({"message": "Product deleted successfully."}), 200
   
@app.route("/api/products/add", methods=["POST"])
@login_required
def add_product():
    data = request.get_json() or {}

    product_name = (data.get("product_name") or "").strip()
    category = (data.get("category") or "").strip()
    sub_category = (data.get("sub_category") or "").strip()

    if not product_name or not category or not sub_category:
        return jsonify({"message": "Product name, category, and sub-category are required."}), 400

    try:
        sales = float(data.get("sales", 0) or 0)
        quantity = int(data.get("quantity", 0) or 0)
        discount_input = float(data.get("discount", 0) or 0)
        profit = float(data.get("profit", 0) or 0)
        stock_level = int(data.get("stock_level", 0) or 0)
        reorder_point = int(data.get("reorder_point", 0) or 0)
        shelf_life_days = int(data.get("shelf_life_days", 365) or 365)
    except ValueError:
        return jsonify({"message": "Please enter valid numeric values."}), 400

    if discount_input < 0 or discount_input > 100:
        return jsonify({"message": "Discount must be between 0 and 100 percent."}), 400

    discount_value = discount_input / 100.0

    rebuild_script = os.path.join(BASE_DIR, "run_once_import.py")
    forecast_script = os.path.join(BASE_DIR, "save_arima_forecast.py")

    if not os.path.exists(rebuild_script):
        return jsonify({
            "message": f"File not found: {rebuild_script}"
        }), 500

    if not os.path.exists(forecast_script):
        return jsonify({
            "message": f"File not found: {forecast_script}"
        }), 500

    conn = db.open_connection()
    try:
        db.execute_update(conn, """
            INSERT INTO manual_products (
                product_name, ship_mode, segment, country, city, state, postal_code,
                region, category, sub_category, sales, quantity, discount, profit,
                order_date, stock_level, reorder_point, shelf_life_days
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_name,
            data.get("ship_mode", "Standard Class"),
            data.get("segment", "Consumer"),
            data.get("country", "United States"),
            data.get("city", "Unknown"),
            data.get("state", "Unknown"),
            data.get("postal_code", "00000"),
            data.get("region", "Unknown"),
            category,
            sub_category,
            sales,
            quantity,
            discount_value,
            profit,
            data.get("order_date") or None,
            stock_level,
            reorder_point,
            shelf_life_days
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Database insert failed: {str(e)}"}), 500

    finally:
        db.close_connection(conn)

    try:
        rebuild_result = subprocess.run(
            [sys.executable, rebuild_script],
            check=True,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

        forecast_result = subprocess.run(
            [sys.executable, forecast_script],
            check=True,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

    except subprocess.CalledProcessError as e:
        return jsonify({
            "message": "Product saved, but rebuild failed.",
            "error": e.stderr or e.stdout or str(e)
        }), 500

    return jsonify({
        "message": "Product added and model data rebuilt successfully.",
        "rebuild_output": rebuild_result.stdout,
        "forecast_output": forecast_result.stdout
    }), 201

if __name__ == "__main__":
    app.run(debug=True)
