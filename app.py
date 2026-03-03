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
# flask route for dashboard page
@app.get("/dashboard")
def dashboard():
    """
    Tables used:
      - public.sales
      - public.salespeople

    Revenue = quantity * unit_price
    """
    try:
       range_key = request.args.get("range", "all").lower()

       if range_key == "30":
          start_date == date.today() - timedelta(days=30)
       elif range_key == "90":
          start_date == date.today() - timedelta(days=90)
       else:
          start_date == None
          range_key = "all"

        where_clause = ""
        params = {}
        if start_date:
          where_clause = "WHERE s.sale_date >= :start_date"
          params ["start date"]= start_date

        with engine.connect() as conn:
          #total records
          total_records = conn.execute(
             text(f"SELECT COUNT(*) FROM public.sales s {where_clause}"),
             params
          ).scalar()
        #avg revenue per sale
          avg_revenue_per_sale = conn.execute(
             text(f"SELECT AVG(s.unit_price * s.quantity) FROM public.sales s {where_clause} ")
             params
          ).scalar()
          last_updated = conn.execute(
             text(f"SELECT MAX(s.sales_date) FROM public.sales s {where_clause} ")
             params
          ).scalar
        
          
       .all()

        #unpacking query results with safety checks for empty results
        top_row = top_5[0] if top_5 else None # Safely access the top row
        top_salesperson_name = top_5[0][0] if top_5 else None # Safely access the top salesperson's name the first 0 is the row, the second 0 is the column for salesperson_name
        top_salesperson_revenue = float(top_5[0][1]) if top_5 and top_5[0][1] is not None else None # cgecjs if top_5 is empty and conmverts revenue to a float if it exists
        

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