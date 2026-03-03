from flask import Flask, render_template ,  redirect, session, url_for, jsonify, request
from database.database import MySqlConnection
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "9#kL2!xQz@81bP$7vR_stockgenius_2026"
db = MySqlConnection()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
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
    return render_template("dashboard.html")

@app.route("/inventory")
def inventory():
    return render_template("inventory.html")

@app.route("/alerts")
def alerts():
    return render_template("alert.html")

@app.route("/logout")
def logout():
    session.clear()
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
        

@app.route("/api/dashboard/stats")
@login_required
def dashboard_stats():
    """
    KPI cards — all sourced directly from ML-computed columns:
      Low_Stock    → flagged by your reorder_point logic
      Near_Expiry  → flagged by Days_To_Expiry < 30
      Is_Anomaly   → flagged by Isolation Forest
      Sales        → total revenue in dataset
    """
    conn = db.open_connection()
    try:
        row = db.run_query(conn, """
            SELECT
                COUNT(*)                        AS total_records,
                SUM(low_stock)                  AS low_stock_count,
                SUM(near_expiry)                AS near_expiry_count,
                SUM(is_anomaly)                 AS anomaly_count,
                ROUND(SUM(sales), 2)            AS total_sales,
                COUNT(DISTINCT sub_category)    AS total_products
            FROM ml_inventory
        """)[0]

        return jsonify({
            "total_products":  int(row["total_products"]),
            "low_stock":       int(row["low_stock_count"]   or 0),
            "near_expiry":     int(row["near_expiry_count"] or 0),
            "anomaly_count":   int(row["anomaly_count"]     or 0),
            "total_sales":     float(row["total_sales"]     or 0),
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

if __name__ == "__main__":
    app.run(debug=True)
