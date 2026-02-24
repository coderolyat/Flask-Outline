import os
from flask import Flask, render_template
from sqlalchemy import create_engine, text

app = Flask(__name__)


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set.\n\n"
        "In PowerShell, run:\n"
        '$env:DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/sales_analysis"\n'
        "Then run:\n"
        "python app.py\n"
    )

print("DATABASE_URL =", DATABASE_URL)
engine = create_engine(DATABASE_URL, future=True)

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/dashboard")
def dashboard():
    """
    Uses Postgres table: public.sales
    Columns (from your schema):
      - sale_date (date)
      - quantity (int)
      - unit_price (numeric)

    Revenue is computed as: quantity * unit_price
    """
    try:
        with engine.connect() as conn:
            total_records = conn.execute(
                text("SELECT COUNT(*) FROM public.sales")
            ).scalar()

            avg_revenue_per_sale = conn.execute(
                text("SELECT AVG(quantity * unit_price) FROM public.sales")
            ).scalar()

            last_updated = conn.execute(
                text("SELECT MAX(sale_date) FROM public.sales")
            ).scalar()

        kpis = {
            "total_records": int(total_records or 0),
            "avg_value": round(float(avg_revenue_per_sale), 2) if avg_revenue_per_sale is not None else "—",
            "last_updated": last_updated.strftime("%Y-%m-%d") if last_updated else "—",
        }

        return render_template("dashboard.html", kpis=kpis)

    except Exception as e:
        return f"<h2>Dashboard error</h2><pre>{e}</pre>", 500

if __name__ == "__main__":
    app.run(debug=True)