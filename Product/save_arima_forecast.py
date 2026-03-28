import pandas as pd
import mysql.connector
from statsmodels.tsa.arima.model import ARIMA

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


def load_combined_sales_data():
    print("Loading CSV + manual product sales for ARIMA...")

    csv_df = pd.read_csv(CSV_PATH, encoding="latin1")
    csv_df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in csv_df.columns]

    # support either order_date or order date
    if "order_date" not in csv_df.columns:
        raise ValueError("CSV must contain order_date / Order Date column")

    csv_df["order_date"] = pd.to_datetime(csv_df["order_date"], errors="coerce")
    csv_df["sales"] = pd.to_numeric(csv_df["sales"], errors="coerce").fillna(0)

    conn = get_conn()
    try:
        manual_df = pd.read_sql("SELECT order_date, sales FROM manual_products", conn)
    finally:
        conn.close()

    if manual_df.empty:
        combined = csv_df[["order_date", "sales"]].copy()
    else:
        manual_df["order_date"] = pd.to_datetime(manual_df["order_date"], errors="coerce")
        manual_df["sales"] = pd.to_numeric(manual_df["sales"], errors="coerce").fillna(0)

        combined = pd.concat([
            csv_df[["order_date", "sales"]],
            manual_df[["order_date", "sales"]]
        ], ignore_index=True)

    combined = combined.dropna(subset=["order_date"])
    return combined


def main():
    df = load_combined_sales_data()

    monthly = df.groupby(df["order_date"].dt.to_period("M"))["sales"].sum()
    monthly.index = monthly.index.to_timestamp()

    print(f"{len(monthly)} months of data found")

    if len(monthly) < 6:
        print("Not enough monthly data for ARIMA forecast.")
        return

    print("Fitting ARIMA(2,1,2)...")
    model = ARIMA(monthly, order=(2, 1, 2))
    fit = model.fit()

    forecast_vals = fit.forecast(steps=10)
    future_idx = pd.date_range(start=monthly.index[-1], periods=11, freq="MS")[1:]

    rows = []
    for date, val in zip(future_idx, forecast_vals):
        rows.append({
            "forecast_month": date.strftime("%Y-%m-%d"),
            "label": date.strftime("%b %Y"),
            "forecast_amount": round(float(val), 2)
        })

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arima_forecast (
                id INT AUTO_INCREMENT PRIMARY KEY,
                forecast_month DATE NOT NULL,
                label VARCHAR(20),
                forecast_amount DECIMAL(12,2),
                created_at DATETIME DEFAULT NOW()
            )
        """)
        conn.commit()

        cursor.execute("DELETE FROM arima_forecast")
        conn.commit()

        cursor.executemany(
            "INSERT INTO arima_forecast (forecast_month, label, forecast_amount) VALUES (%s, %s, %s)",
            [(r["forecast_month"], r["label"], r["forecast_amount"]) for r in rows]
        )
        conn.commit()

    finally:
        cursor.close()
        conn.close()

    print("ARIMA forecast saved to arima_forecast")
    print("Done!")


if __name__ == "__main__":
    main()