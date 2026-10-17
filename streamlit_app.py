import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Sale performance dashboard", page_icon="🦐", layout="wide")
DATA_FILE = Path(__file__).parent / "sample_sales.csv"

st.markdown("""
<style>
.stApp { background: #f4f7fb; }
[data-testid="stMetric"] { background: white; padding: 16px; border-radius: 12px; border: 1px solid #dce5ef; }
h1, h2, h3 { color: #173b65; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_sample_data():
    return pd.read_csv(DATA_FILE, parse_dates=["Date"])

def normalize_columns(df):
    aliases = {
        "date":"Date", "order id":"Order ID", "order_id":"Order ID",
        "customer name":"Customer Name", "customer":"Customer Name",
        "p code":"Product", "p_code":"Product", "product":"Product",
        "market":"Market", "area":"Area", "hatchery":"Hatchery",
        "staff":"Salesperson", "salesperson":"Salesperson",
        "qty":"Quantity", "quantity":"Quantity", "bonus qty":"Bonus",
        "bonus":"Bonus", "total (rs)":"Revenue", "revenue":"Revenue",
        "amount":"Revenue", "total":"Revenue"
    }
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in aliases:
            rename[col] = aliases[key]
    return df.rename(columns=rename)

def prepare_data(df):
    df = normalize_columns(df.copy())
    missing = [c for c in ["Date", "Quantity", "Revenue"] if c not in df.columns]
    if missing:
        raise ValueError("Required columns not found: " + ", ".join(missing))
    defaults = {
        "Order ID":"", "Customer Name":"Unknown", "Product":"Unknown",
        "Market":"Unknown", "Area":"Unknown", "Hatchery":"Unknown",
        "Salesperson":"Unknown", "Bonus":0
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Quantity", "Revenue", "Bonus"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"])
    for col in ["Order ID", "Customer Name", "Product", "Market", "Area", "Hatchery", "Salesperson"]:
        df[col] = df[col].fillna("Unknown").astype(str)
    return df

st.title("🦐 Sale performance dashboard")
st.caption("Interactive sales overview • Prototype using sample data")

with st.sidebar:
    st.header("Dashboard controls")
    st.write("Use filters to explore the sample sales data.")
    uploaded = st.file_uploader("Preview an Excel or CSV file", type=["xlsx", "xlsm", "xls", "csv"])
    st.caption("Uploads are previewed only in your session; they are not published to other viewers.")

try:
    if uploaded is not None:
        if uploaded.name.lower().endswith(".csv"):
            raw = pd.read_csv(uploaded)
        else:
            book = pd.ExcelFile(uploaded)
            sheet = st.sidebar.selectbox("Choose worksheet", book.sheet_names)
            raw = pd.read_excel(uploaded, sheet_name=sheet)
        df = prepare_data(raw)
        source_label = f"Uploaded preview: {uploaded.name}"
    else:
        df = prepare_data(load_sample_data())
        source_label = "Sample data"
except Exception as e:
    st.error(f"Could not load this file: {e}")
    st.info("Check that your file includes Date, Quantity and Revenue columns, or use sample data.")
    st.stop()

if df.empty:
    st.warning("No valid dated records were found.")
    st.stop()

min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
with st.sidebar:
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    def choices(label, col):
        vals = sorted(df[col].dropna().astype(str).unique().tolist())
        return st.multiselect(label, vals, default=vals)
    markets = choices("Market", "Market")
    areas = choices("Area", "Area")
    products = choices("Product", "Product")
    salespeople = choices("Salesperson", "Salesperson")
    customers = choices("Customer", "Customer Name")

start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_date, max_date)
filtered = df[
    (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date) &
    (df["Market"].isin(markets)) & (df["Area"].isin(areas)) &
    (df["Product"].isin(products)) & (df["Salesperson"].isin(salespeople)) &
    (df["Customer Name"].isin(customers))
].copy()

orders = filtered["Order ID"].replace("", pd.NA).nunique()
if orders == 0:
    orders = len(filtered)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sales Quantity", f"{filtered['Quantity'].sum():,.0f}")
c2.metric("Number of Orders", f"{orders:,.0f}")
c3.metric("Total Bonus", f"{filtered['Bonus'].sum():,.0f}")
c4.metric("Total Revenue", f"₹{filtered['Revenue'].sum():,.2f}")
st.caption(f"Data source: {source_label} · Last loaded: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

if filtered.empty:
    st.info("No records match these filters. Change the filters to see results.")
    st.stop()

left, right = st.columns(2)
with left:
    monthly = filtered.assign(Month=filtered["Date"].dt.to_period("M").astype(str)).groupby("Month", as_index=False)["Revenue"].sum()
    st.plotly_chart(px.line(monthly, x="Month", y="Revenue", markers=True, title="Monthly Revenue Trend"), use_container_width=True)
with right:
    market = filtered.groupby("Market", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
    st.plotly_chart(px.bar(market, x="Market", y="Revenue", title="Revenue by Market"), use_container_width=True)
left, right = st.columns(2)
with left:
    product = filtered.groupby("Product", as_index=False)["Quantity"].sum().sort_values("Quantity", ascending=False).head(15)
    st.plotly_chart(px.bar(product, x="Product", y="Quantity", title="Sales Quantity by Product"), use_container_width=True)
with right:
    staff = filtered.groupby("Salesperson", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
    st.plotly_chart(px.bar(staff, x="Salesperson", y="Revenue", title="Revenue by Salesperson"), use_container_width=True)
with st.expander("View filtered records"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)
st.caption("Prototype only: uploads are session-specific. Shared persistent updates, protected admin publishing, and automatic OneDrive sync are not implemented yet.")
