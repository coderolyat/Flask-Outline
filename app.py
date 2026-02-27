import os
from flask import Flask, render_template
from sqlalchemy import create_engine, text

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


# runtime error handling for missing DATABASE_URL
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set.\n\n"
        "In PowerShell, run:\n"
        '$env:DATABASE_URL="postgresql+psycopg2://postgres:YourPassWord@localhost:5432/sales_analysis"\n'
        "Then run:\n"
        "python app.py\n"
    )

# connects our app to the database using SQLAlchemy
engine = create_engine(DATABASE_URL, future=True)

# flask route for home page
@app.get("/")
def home():
    return render_template("index.html")

@app.get("/dashboard")
def dashboard():
    """
    Tables used:
      - public.sales
      - public.salespeople

    Revenue = quantity * unit_price
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

            top_5 = conn.execute(text("""
                SELECT
                    sp.salesperson_name,
                    SUM(s.quantity * s.unit_price) AS total_revenue
                FROM public.sales s
                JOIN public.salespeople sp
                  ON sp.salesperson_id = s.salesperson_id
                GROUP BY sp.salesperson_name
                ORDER BY total_revenue DESC
                LIMIT 5;
            """)).all()

        top_row = top_5[0] if top_5 else None
        top_salesperson_name = top_5[0][0] if top_5 else None
        top_salesperson_name = top_5[0][0] if top_5 else None

        top_salesperson_revenue = float(top_5[0][1]) if top_5 and top_5[0][1] is not None else None
        

        kpis = {
            "total_records": int(total_records or 0),
            "avg_value": round(float(avg_revenue_per_sale), 2) if avg_revenue_per_sale is not None else "—",
            "last_updated": last_updated.strftime("%Y-%m-%d") if last_updated else "—",
            "top_salesperson": top_salesperson_name if top_salesperson_name else "—",
            "top_salesperson_revenue": round(top_salesperson_revenue, 2) if top_salesperson_revenue is not None else "—",
        }

        return render_template("dashboard.html", kpis=kpis, top_5=top_5)

    except Exception as e:
        return f"<h2>Dashboard error</h2><pre>{e}</pre>", 500

if __name__ == "__main__":
    app.run(debug=True)