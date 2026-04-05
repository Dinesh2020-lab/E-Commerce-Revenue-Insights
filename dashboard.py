"""
Project 2: E-Commerce Sales & Revenue Insights — Streamlit Dashboard
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="E-Commerce Analytics", layout="wide", page_icon="🛒")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    orders      = pd.read_csv("data/olist_orders_dataset.csv",
                              parse_dates=["order_purchase_timestamp","order_delivered_customer_date"])
    order_items = pd.read_csv("data/olist_order_items_dataset.csv")
    customers   = pd.read_csv("data/olist_customers_dataset.csv")
    products    = pd.read_csv("data/olist_products_dataset.csv")
    payments    = pd.read_csv("data/olist_order_payments_dataset.csv")
    reviews     = pd.read_csv("data/olist_order_reviews_dataset.csv")

    try:
        cat_tr = pd.read_csv("data/product_category_name_translation.csv")
        products = products.merge(cat_tr, on="product_category_name", how="left")
        products["category"] = products["product_category_name_english"].fillna(products["product_category_name"])
    except Exception:
        products["category"] = products["product_category_name"]

    delivered = orders[orders["order_status"] == "delivered"].copy()
    delivered["month"] = delivered["order_purchase_timestamp"].dt.to_period("M")
    delivered["month_str"] = delivered["month"].astype(str)
    delivered["weekday"] = delivered["order_purchase_timestamp"].dt.day_name()
    delivered["delivery_days"] = (
        (delivered["order_delivered_customer_date"] - delivered["order_purchase_timestamp"]).dt.days
    )

    items = order_items.merge(delivered[["order_id","month","month_str"]], on="order_id")
    items["total_value"] = items["price"] + items["freight_value"]
    items = items.merge(products[["product_id","category"]], on="product_id", how="left")

    return delivered, items, customers, payments, reviews

try:
    delivered, items, customers, payments, reviews = load_data()
except FileNotFoundError:
    st.error("⚠️ Place Olist CSV files in a 'data/' subfolder and re-run.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filters")
all_months = sorted(delivered["month_str"].unique())
sel_months = st.sidebar.select_slider("Month range", options=all_months,
                                       value=(all_months[0], all_months[-1]))
sel_states = st.sidebar.multiselect("State", sorted(customers["customer_state"].unique()),
                                     default=list(customers["customer_state"].unique()))

state_customers = customers[customers["customer_state"].isin(sel_states)]["customer_id"]
mask = (
    delivered["month_str"].between(sel_months[0], sel_months[1]) &
    delivered["customer_id"].isin(state_customers)
)
filtered_orders = delivered[mask]
filtered_items  = items[items["order_id"].isin(filtered_orders["order_id"])]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🛒 E-Commerce Sales & Revenue Dashboard")
st.caption("Brazilian E-Commerce (Olist) · SQL + Pandas + Plotly · Data Analyst Project")
st.divider()

# ── KPIs ─────────────────────────────────────────────────────────────────────
total_rev = filtered_items["total_value"].sum()
total_ord = filtered_orders["order_id"].nunique()
aov       = filtered_items.groupby("order_id")["total_value"].sum().mean()
repeat    = (filtered_orders.groupby("customer_id")["order_id"].count() > 1).mean() * 100

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Revenue",    f"R${total_rev:,.0f}")
c2.metric("Total Orders",     f"{total_ord:,}")
c3.metric("Avg Order Value",  f"R${aov:.2f}")
c4.metric("Repeat Rate",      f"{repeat:.1f}%")

# ── Monthly revenue ───────────────────────────────────────────────────────────
monthly = (filtered_items.groupby("month_str")["total_value"]
           .sum().reset_index().rename(columns={"month_str":"Month","total_value":"Revenue"}))
fig1 = px.area(monthly, x="Month", y="Revenue",
               title="Monthly Revenue Trend",
               color_discrete_sequence=["#3266ad"])
fig1.update_layout(xaxis_tickangle=-40, margin=dict(t=40,b=10))
fig1.update_yaxes(tickprefix="R$", tickformat=",.0f")
st.plotly_chart(fig1, use_container_width=True)

# ── Category + Payment ────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    cat_rev = (filtered_items.groupby("category")["price"]
               .sum().sort_values(ascending=False).head(10).reset_index())
    cat_rev.columns = ["Category","Revenue"]
    fig2 = px.bar(cat_rev, x="Revenue", y="Category", orientation="h",
                  title="Top 10 Categories by Revenue",
                  color_discrete_sequence=["#3266ad"])
    fig2.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=40,b=10))
    fig2.update_xaxes(tickprefix="R$", tickformat=",.0f")
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    pay = (payments[payments["order_id"].isin(filtered_orders["order_id"])]
           .groupby("payment_type")["payment_value"].sum()
           .sort_values(ascending=False).reset_index())
    pay.columns = ["Payment","Revenue"]
    fig3 = px.pie(pay, names="Payment", values="Revenue",
                  title="Revenue by Payment Method", hole=0.45,
                  color_discrete_sequence=["#3266ad","#5fa8d3","#ef9f27","#e24b4a"])
    fig3.update_layout(margin=dict(t=40,b=10))
    st.plotly_chart(fig3, use_container_width=True)

# ── Review score + Delivery ───────────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    rev_del = (filtered_orders.merge(reviews[["order_id","review_score"]], on="order_id", how="left")
               .dropna(subset=["delivery_days","review_score"])
               .groupby("review_score")["delivery_days"].mean().reset_index())
    rev_del.columns = ["Score","Avg Delivery Days"]
    fig4 = px.bar(rev_del, x="Score", y="Avg Delivery Days",
                  title="Avg Delivery Days by Review Score",
                  color="Avg Delivery Days",
                  color_continuous_scale=["#1d9e75","#ef9f27","#e24b4a"])
    fig4.update_layout(margin=dict(t=40,b=10), coloraxis_showscale=False)
    st.plotly_chart(fig4, use_container_width=True)

with col4:
    weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    wd = (filtered_orders["weekday"].value_counts()
          .reindex(weekday_order).reset_index())
    wd.columns = ["Weekday","Orders"]
    fig5 = px.bar(wd, x="Weekday", y="Orders",
                  title="Orders by Day of Week",
                  color_discrete_sequence=["#3266ad"])
    fig5.update_layout(xaxis_tickangle=-30, margin=dict(t=40,b=10))
    st.plotly_chart(fig5, use_container_width=True)

# ── Cohort heatmap ────────────────────────────────────────────────────────────
st.subheader("Customer Cohort Retention Heatmap")
cohort_df = filtered_orders[["customer_id","month"]].drop_duplicates()
first_purchase = cohort_df.groupby("customer_id")["month"].min().reset_index()
first_purchase.columns = ["customer_id","cohort_month"]
cohort_df = cohort_df.merge(first_purchase, on="customer_id")
cohort_df["period"] = (cohort_df["month"] - cohort_df["cohort_month"]).apply(lambda x: x.n)

cohort_counts = (cohort_df.groupby(["cohort_month","period"])["customer_id"]
                 .nunique().unstack(fill_value=0))
cohort_size   = cohort_counts.iloc[:,0]
retention     = (cohort_counts.divide(cohort_size, axis=0) * 100).round(1)
retention_show = retention.iloc[:12, :7]
retention_show.index = retention_show.index.astype(str)

fig6 = px.imshow(retention_show,
                 labels=dict(x="Months Since First Purchase", y="Cohort Month", color="Retention %"),
                 color_continuous_scale="Blues", text_auto=True, aspect="auto")
fig6.update_layout(margin=dict(t=10,b=10))
st.plotly_chart(fig6, use_container_width=True)

# ── Key insights ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Key Business Insights")
peak = monthly.loc[monthly["Revenue"].idxmax()]
top_cat_name = (filtered_items.groupby("category")["price"].sum().idxmax()
                if not filtered_items.empty else "N/A")

i1,i2 = st.columns(2)
i1.info(f"📈 Peak revenue in **{peak['Month']}** — R${peak['Revenue']:,.0f}")
i1.info(f"🏆 Top category: **{top_cat_name}**")
i2.warning(f"🔁 Only **{repeat:.1f}%** of customers made a repeat purchase — high churn opportunity")
i2.warning(f"🚚 Avg delivery time: **{filtered_orders['delivery_days'].mean():.1f} days** — impacts review scores")

with st.expander("View Raw Orders Table"):
    st.dataframe(filtered_orders[["order_id","customer_id","month_str","delivery_days"]].head(100),
                 use_container_width=True)

st.caption("Built with Python · Pandas · SQL · Plotly · Streamlit")
