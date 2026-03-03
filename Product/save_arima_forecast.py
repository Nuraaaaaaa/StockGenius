import pandas as pd
import mysql.connector
from mysql.connector import Error
from statsmodels.tsa.arima.model import ARIMA

DB_HOST     = "localhost"
DB_USER     = "root"
DB_PASSWORD = "1436"
DB_NAME     = "stockgenius"



CSV_PATH = r"C:\Users\User\Desktop\Stock Genuise\Dataset\StockGenius_Enriched_Dataset.csv"

def main():
    print(" Loading CSV for ARIMA…")
    df = pd.read_csv(CSV_PATH, encoding="latin1")
    df["Order Date"] = pd.to_datetime(df["Order Date"])

    # Monthly sales — same as your Jupyter notebook
    monthly = df.groupby(df["Order Date"].dt.to_period("M"))["Sales"].sum()
    monthly.index = monthly.index.to_timestamp()

    print(f"   {len(monthly)} months of data found")

    # Fit ARIMA(2,1,2) — same params as your notebook
    print(" Fitting ARIMA(2,1,2)…")
    model = ARIMA(monthly, order=(2, 1, 2))
    fit   = model.fit()
    print(f"   AIC: {fit.aic:.2f}")

    # Forecast 10 months ahead
    forecast_vals = fit.forecast(steps=10)
    future_idx    = pd.date_range(
        start=monthly.index[-1], periods=11, freq="MS"
    )[1:]

    # Build rows
    rows = []
    for date, val in zip(future_idx, forecast_vals):
        rows.append({
            "forecast_month":  date.strftime("%Y-%m-%d"),
            "label":           date.strftime("%b %Y"),
            "forecast_amount": round(float(val), 2),
        })

    print(f"   Forecast: {[r['forecast_amount'] for r in rows]}")

    # Save to MySQL
    conn = mysql.connector.connect(
        host=DB_HOST, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arima_forecast (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            forecast_month  DATE NOT NULL,
            label           VARCHAR(20),
            forecast_amount DECIMAL(12,2),
            created_at      DATETIME DEFAULT NOW()
        )
    """)
    cursor.execute("DELETE FROM arima_forecast")  # safe to re-run

    cursor.executemany(
        "INSERT INTO arima_forecast (forecast_month, label, forecast_amount) VALUES (%s, %s, %s)",
        [(r["forecast_month"], r["label"], r["forecast_amount"]) for r in rows]
    )
    conn.commit()
    cursor.close()
    conn.close()

    print(" ARIMA forecast saved to `arima_forecast` table")
    print(" Done!")

if __name__ == "__main__":
    main()