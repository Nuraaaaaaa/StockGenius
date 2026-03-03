
import pandas as pd
import mysql.connector
from mysql.connector import Error

DB_HOST     = "localhost"
DB_USER     = "root"
DB_PASSWORD = "1436"
DB_NAME     = "stockgenius"


CSV_PATH = r"C:\Users\User\Desktop\Stock Genuise\Dataset\StockGenius_Enriched_Dataset.csv"

# ── CONNECT ──────────────────────────────────────────────────────
def get_conn():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )

# ── CREATE TABLE ─────────────────────────────────────────────────
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ml_inventory (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ship_mode       VARCHAR(50),
    segment         VARCHAR(50),
    country         VARCHAR(100),
    city            VARCHAR(100),
    state           VARCHAR(100),
    postal_code     VARCHAR(20),
    region          VARCHAR(50),
    category        VARCHAR(100),
    sub_category    VARCHAR(100),
    sales           DECIMAL(10,2),
    quantity        INT,
    discount        DECIMAL(5,2),
    profit          DECIMAL(10,2),
    order_date      DATE,
    month           INT,
    year            INT,
    quarter         INT,
    stock_level     INT,
    reorder_point   INT,
    shelf_life_days INT,
    days_to_expiry  INT,
    near_expiry     TINYINT(1),
    low_stock       TINYINT(1),
    profit_margin   DECIMAL(10,2),
    is_anomaly      TINYINT(1),
    anomaly_score   INT
);
"""

# ── INSERT ROWS ──────────────────────────────────────────────────
INSERT_ROW = """
INSERT INTO ml_inventory (
    ship_mode, segment, country, city, state, postal_code, region,
    category, sub_category, sales, quantity, discount, profit,
    order_date, month, year, quarter,
    stock_level, reorder_point, shelf_life_days,
    days_to_expiry, near_expiry, low_stock,
    profit_margin, is_anomaly, anomaly_score
) VALUES (
    %s,%s,%s,%s,%s,%s,%s,
    %s,%s,%s,%s,%s,%s,
    %s,%s,%s,%s,
    %s,%s,%s,
    %s,%s,%s,
    %s,%s,%s
)
"""

def main():
    print(" Loading CSV…")
    df = pd.read_csv(CSV_PATH)

    # Normalise column names to lowercase + underscores
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

    # Parse order_date
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce").dt.date

    # Fill NaN safely
    df = df.fillna(0)

    print(f"   {len(df)} rows loaded from CSV")

    conn = get_conn()
    cursor = conn.cursor()

    # Create table
    cursor.execute(CREATE_TABLE)
    conn.commit()
    print(" Table `ml_inventory` ready")

    # Clear old data so re-running is safe
    cursor.execute("DELETE FROM ml_inventory")
    conn.commit()

    # Batch insert
    rows = []
    for _, r in df.iterrows():
        rows.append((
            r.get("ship_mode"),   r.get("segment"),  r.get("country"),
            r.get("city"),        r.get("state"),     r.get("postal_code"),
            r.get("region"),      r.get("category"),  r.get("sub_category"),
            float(r.get("sales",0)),    int(r.get("quantity",0)),
            float(r.get("discount",0)), float(r.get("profit",0)),
            r.get("order_date"),
            int(r.get("month",0)),  int(r.get("year",0)), int(r.get("quarter",0)),
            int(r.get("stock_level",0)),   int(r.get("reorder_point",0)),
            int(r.get("shelf_life_days",0)),
            int(r.get("days_to_expiry",0)),
            int(r.get("near_expiry",0)),   int(r.get("low_stock",0)),
            float(r.get("profit_margin",0)),
            int(r.get("is_anomaly",0)),    int(r.get("anomaly_score",0)),
        ))

    cursor.executemany(INSERT_ROW, rows)
    conn.commit()
    print(f" {len(rows)} rows inserted into `ml_inventory`")

    cursor.close()
    conn.close()
    print(" data is loaded in stockgenius database.")

if __name__ == "__main__":
    main()