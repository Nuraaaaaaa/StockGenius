import pandas as pd
import mysql.connector
from mysql.connector import Error
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1436"
DB_NAME = "stockgenius"

CSV_PATH = r"C:\Users\User\Desktop\Stock Genuise\Dataset\StockGenius_Enriched_Dataset.csv"


def get_conn():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ml_inventory (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    product_name    VARCHAR(255),
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
    anomaly_score   DECIMAL(10,4),
    source_type     VARCHAR(20)
);
"""


INSERT_ROW = """
INSERT INTO ml_inventory (
    product_name, ship_mode, segment, country, city, state, postal_code, region,
    category, sub_category, sales, quantity, discount, profit,
    order_date, month, year, quarter,
    stock_level, reorder_point, shelf_life_days,
    days_to_expiry, near_expiry, low_stock,
    profit_margin, is_anomaly, anomaly_score, source_type
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s, %s
)
"""


def load_csv_data():
    print("Loading CSV data...")
    df = pd.read_csv(CSV_PATH, encoding="latin1")

    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

    if "product_name" not in df.columns:
        if "sub_category" in df.columns:
            df["product_name"] = df["sub_category"]
        else:
            df["product_name"] = "Unknown Product"

    df["order_date"] = pd.to_datetime(df.get("order_date"), errors="coerce")

    # Ensure required columns exist
    required_cols = [
        "product_name", "ship_mode", "segment", "country", "city", "state",
        "postal_code", "region", "category", "sub_category", "sales", "quantity",
        "discount", "profit", "order_date", "stock_level", "reorder_point",
        "shelf_life_days"
    ]

    for col in required_cols:
        if col not in df.columns:
            if col in ["sales", "discount", "profit"]:
                df[col] = 0.0
            elif col in ["quantity", "stock_level", "reorder_point", "shelf_life_days"]:
                df[col] = 0
            else:
                df[col] = ""

    df["source_type"] = "csv"
    return df


def load_manual_data():
    print("Loading manual products from MySQL...")

    conn = get_conn()
    try:
        query = "SELECT * FROM manual_products"
        manual_df = pd.read_sql(query, conn)
    finally:
        conn.close()

    if manual_df.empty:
        print("No manual products found.")
        return pd.DataFrame(columns=[
            "product_name", "ship_mode", "segment", "country", "city", "state",
            "postal_code", "region", "category", "sub_category", "sales", "quantity",
            "discount", "profit", "order_date", "stock_level", "reorder_point",
            "shelf_life_days", "source_type"
        ])

    manual_df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in manual_df.columns]
    manual_df["order_date"] = pd.to_datetime(manual_df.get("order_date"), errors="coerce")
    manual_df["source_type"] = "manual"

    return manual_df


def prepare_data(df):
    df = df.copy()

    df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["discount"] = pd.to_numeric(df["discount"], errors="coerce").fillna(0)
    df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
    df["stock_level"] = pd.to_numeric(df["stock_level"], errors="coerce").fillna(0).astype(int)
    df["reorder_point"] = pd.to_numeric(df["reorder_point"], errors="coerce").fillna(0).astype(int)
    df["shelf_life_days"] = pd.to_numeric(df["shelf_life_days"], errors="coerce").fillna(365).astype(int)

    df["month"] = df["order_date"].dt.month.fillna(0).astype(int)
    df["year"] = df["order_date"].dt.year.fillna(0).astype(int)
    df["quarter"] = df["order_date"].dt.quarter.fillna(0).astype(int)

    # basic expiry logic
    df["days_to_expiry"] = df["shelf_life_days"]
    df["near_expiry"] = (df["days_to_expiry"] < 30).astype(int)
    df["low_stock"] = (df["stock_level"] < df["reorder_point"]).astype(int)

    df["profit_margin"] = df.apply(
        lambda r: round((r["profit"] / r["sales"]) * 100, 2) if r["sales"] > 0 else 0,
        axis=1
    )

    return df


def train_anomaly_model(df):
    df = df.copy()

    categorical_cols = ["ship_mode", "segment", "category", "sub_category", "region", "state"]

    for col in categorical_cols:
        df[col] = df[col].astype(str).fillna("Unknown")
        encoder = LabelEncoder()
        df[col + "_enc"] = encoder.fit_transform(df[col])

    feature_cols = [
        "sales", "quantity", "discount",
        "ship_mode_enc", "segment_enc", "category_enc",
        "sub_category_enc", "region_enc", "state_enc",
        "month", "quarter", "year",
        "stock_level", "reorder_point", "shelf_life_days", "days_to_expiry"
    ]

    X = df[feature_cols].fillna(0)

    model = IsolationForest(contamination=0.05, random_state=42)
    preds = model.fit_predict(X)
    scores = model.decision_function(X)

    df["is_anomaly"] = (preds == -1).astype(int)
    df["anomaly_score"] = scores.round(4)

    return df


def save_to_mysql(df):
    print("Saving combined data into ml_inventory...")

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(CREATE_TABLE)
        conn.commit()

        cursor.execute("DELETE FROM ml_inventory")
        conn.commit()

        rows = []
        for _, r in df.iterrows():
            order_date = pd.to_datetime(r.get("order_date"), errors="coerce")
            order_date = None if pd.isna(order_date) else order_date.date()

            rows.append((
                str(r.get("product_name", "")),
                str(r.get("ship_mode", "")),
                str(r.get("segment", "")),
                str(r.get("country", "")),
                str(r.get("city", "")),
                str(r.get("state", "")),
                str(r.get("postal_code", "")),
                str(r.get("region", "")),
                str(r.get("category", "")),
                str(r.get("sub_category", "")),
                float(r.get("sales", 0)),
                int(r.get("quantity", 0)),
                float(r.get("discount", 0)),
                float(r.get("profit", 0)),
                order_date,
                int(r.get("month", 0)),
                int(r.get("year", 0)),
                int(r.get("quarter", 0)),
                int(r.get("stock_level", 0)),
                int(r.get("reorder_point", 0)),
                int(r.get("shelf_life_days", 365)),
                int(r.get("days_to_expiry", 0)),
                int(r.get("near_expiry", 0)),
                int(r.get("low_stock", 0)),
                float(r.get("profit_margin", 0)),
                int(r.get("is_anomaly", 0)),
                float(r.get("anomaly_score", 0)),
                str(r.get("source_type", "csv"))
            ))

        cursor.executemany(INSERT_ROW, rows)
        conn.commit()

        print(f"{len(rows)} rows inserted into ml_inventory")

    finally:
        cursor.close()
        conn.close()


def main():
    csv_df = load_csv_data()
    manual_df = load_manual_data()

    combined_df = pd.concat([csv_df, manual_df], ignore_index=True, sort=False)
    combined_df = prepare_data(combined_df)
    combined_df = train_anomaly_model(combined_df)
    combined_df = combined_df.fillna(0)

    print(f"Total combined rows: {len(combined_df)}")
    save_to_mysql(combined_df)
    print("Done. ml_inventory now contains CSV + manual products.")


if __name__ == "__main__":
    main()