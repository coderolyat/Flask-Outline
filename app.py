import os
from datetime import date, timedelta
from flask import Flask, render_template, request
from sqlalchemy import create_engine, text

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set.\n\n"
        "In PowerShell, run:\n"
        '$env:DATABASE_URL="postgresql+psycopg2://postgres:YourPassWord@localhost:5432/sales_analysis"\n'
        "Then run:\n"
        "python app.py\n"
    )

engine = create_engine(DATABASE_URL, future=True)

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/dashboard")
def dashboard():
    """
    Tables used:
      - public.sales
      - public.salespeople

    Assumed columns in public.sales:
      - sale_date (DATE or TIMESTAMP)
      - salesperson_id
      - quantity
      - unit_price

    Revenue per sale row = quantity * unit_price
    """

    # --- Read filters from URL query params ---
    range_key = request.args.get("range", "all").lower()          # all | 7d | 30d
    salesperson_id = request.args.get("salesperson_id", "").strip()  # "" means all

    # --- Convert range filter into a start_date ---
    start_date = None
    if range_key == "7d":
        start_date = date.today() - timedelta(days=7)
    elif range_key == "30d":
        start_date = date.today() - timedelta(days=30)

    # --- Build WHERE clause and bind params safely ---
    where_parts = []
    params = {}

    if start_date is not None:
        # If sale_date is TIMESTAMP, this still works fine in Postgres
        where_parts.append("s.sale_date >= :start_date")
        params["start_date"] = start_date

    if salesperson_id:
        where_parts.append("s.salesperson_id = :salesperson_id")
        params["salesperson_id"] = int(salesperson_id)

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    try:
        with engine.connect() as conn:
            # --- For dropdown filter options (salespeople list) ---
            salespeople = conn.execute(text("""
                SELECT salesperson_id AS id, name
                FROM public.salespeople
                ORDER BY name
            """)).mappings().all()

            # --- KPI: total records (filtered) ---
            total_records = conn.execute(
                text(f"SELECT COUNT(*) FROM public.sales s {where_sql}"),
                params
            ).scalar()

            # --- KPI: average revenue per sale (filtered) ---
            # avg(quantity * unit_price)
            avg_revenue_per_sale = conn.execute(
                text(f"""
                    SELECT AVG(s.quantity * s.unit_price)
                    FROM public.sales s
                    {where_sql}
                """),
                params
            ).scalar()

            # --- KPI: last updated (filtered) ---
            # (assumes last updated = latest sale_date in the filtered set)
            last_updated = conn.execute(
                text(f"""
                    SELECT MAX(s.sale_date)
                    FROM public.sales s
                    {where_sql}
                """),
                params
            ).scalar()

            # --- Top 5 salespeople (filtered) ---
            # NOTE: if salesperson_id filter is set, this will just show that person (fine).
            top_5 = conn.execute(
                text(f"""
                    SELECT sp.name AS salesperson_name,
                           SUM(s.quantity * s.unit_price) AS total_revenue
                    FROM public.sales s
                    JOIN public.salespeople sp
                      ON sp.salesperson_id = s.salesperson_id
                    {where_sql}
                    GROUP BY sp.name
                    ORDER BY total_revenue DESC
                    LIMIT 5
                """),
                params
            ).all()

        # --- Extract top salesperson from top_5 safely ---
        top_row = top_5[0] if top_5 else None
        top_salesperson_name = top_row[0] if top_row else None
        top_salesperson_revenue = float(top_row[1]) if top_row and top_row[1] is not None else None

        # --- Build kpis dict for Jinja (display-ready values) ---
        kpis = {
            "total_records": int(total_records or 0),
            "avg_value": round(float(avg_revenue_per_sale), 2) if avg_revenue_per_sale is not None else "—",
            "last_updated": last_updated.strftime("%Y-%m-%d") if last_updated else "—",
            "top_salesperson": top_salesperson_name if top_salesperson_name else "—",
            "top_salesperson_revenue": round(top_salesperson_revenue, 2) if top_salesperson_revenue is not None else "—",
        }

        # --- Send everything to the template (including selected filter state) ---
        return render_template(
            "dashboard.html",
            kpis=kpis,
            top_5=top_5,  # so you can render the table
            salespeople=salespeople,  # so you can render the dropdown
            selected_range=range_key,
            selected_salesperson_id=int(salesperson_id) if salesperson_id else None,
        )

    except Exception as e:
        # Fail gracefully (you can show the error string or a nicer message)
        kpis = {
            "total_records": "—",
            "avg_value": "—",
            "last_updated": "—",
            "top_salesperson": "—",
            "top_salesperson_revenue": "—",
        }
        return render_template(
            "dashboard.html",
            kpis=kpis,
            top_5=[],
            salespeople=[],
            selected_range=range_key,
            selected_salesperson_id=int(salesperson_id) if salesperson_id else None,
            error=str(e),
        )

if __name__ == "__main__":
    app.run(debug=True)