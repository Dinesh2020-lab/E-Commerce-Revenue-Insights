"""
Project 2: E-Commerce Sales & Revenue Insights
Dataset: Brazilian E-Commerce (Olist) — Kaggle
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Steps to run:
1. pip install pandas numpy matplotlib seaborn plotly streamlit
2. Download all CSV files from Kaggle and place in a folder called 'data/'
3. python eda_analysis.py            ← saves PNG charts
   streamlit run dashboard.py        ← interactive dashboard
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────

print("Loading data...")
orders     = pd.read_csv("data/olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp","order_delivered_customer_date"])
order_items= pd.read_csv("data/olist_order_items_dataset.csv")
customers  = pd.read_csv("data/olist_customers_dataset.csv")
products   = pd.read_csv("data/olist_products_dataset.csv")
payments   = pd.read_csv("data/olist_order_payments_dataset.csv")
reviews    = pd.read_csv("data/olist_order_reviews_dataset.csv")

try:
    cat_translation = pd.read_csv("data/product_category_name_translation.csv")
    products = products.merge(cat_translation, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(products["product_category_name"])
except Exception:
    products["category"] = products["product_category_name"]

# Filter delivered orders only
delivered = orders[orders["order_status"] == "delivered"].copy()

# ─────────────────────────────────────────
# 2. FEATURE ENGINEERING
# ─────────────────────────────────────────

# Monthly revenue
delivered["month"] = delivered["order_purchase_timestamp"].dt.to_period("M")

# Merge for revenue
items_orders = order_items.merge(delivered[["order_id","month"]], on="order_id")
items_orders["total_value"] = items_orders["price"] + items_orders["freight_value"]

monthly_rev = (items_orders.groupby("month")["total_value"]
               .sum().reset_index())
monthly_rev.columns = ["Month","Revenue"]
monthly_rev["Month_str"] = monthly_rev["Month"].astype(str)

# Category revenue
items_cat = items_orders.merge(products[["product_id","category"]], on="product_id", how="left")
cat_rev = (items_cat.groupby("category")["price"]
           .sum().reset_index()
           .sort_values("price", ascending=False)
           .head(10))
cat_rev.columns = ["Category","Revenue"]

# Delivery time
delivered["delivery_days"] = (
    (delivered["order_delivered_customer_date"] - delivered["order_purchase_timestamp"])
    .dt.days
)
orders_reviews = delivered.merge(reviews[["order_id","review_score"]], on="order_id", how="left")

# Payment breakdown
payment_summary = (payments.merge(delivered[["order_id"]], on="order_id")
                   .groupby("payment_type")["payment_value"].sum()
                   .sort_values(ascending=False).reset_index())
payment_summary.columns = ["Payment Type","Revenue"]

# Cohort analysis
delivered["cohort_month"] = (delivered.merge(
    delivered.groupby("customer_id")["order_purchase_timestamp"].min().reset_index().rename(
        columns={"order_purchase_timestamp":"first_purchase"}),
    on="customer_id")["first_purchase"].dt.to_period("M"))

print(f"Total delivered orders: {len(delivered):,}")
print(f"Total revenue: ${items_orders['total_value'].sum():,.0f}")
print(f"Avg order value: ${items_orders.groupby('order_id')['total_value'].sum().mean():.2f}")
print(f"Date range: {delivered['order_purchase_timestamp'].min().date()} → {delivered['order_purchase_timestamp'].max().date()}")

# ─────────────────────────────────────────
# 3. EDA PLOTS
# ─────────────────────────────────────────

sns.set_theme(style="whitegrid", palette="muted")
fig = plt.figure(figsize=(20, 14))
fig.suptitle("E-Commerce Sales & Revenue Insights — Olist Dataset", fontsize=16, fontweight="bold", y=0.98)
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.38)

# Plot 1: Monthly revenue trend
ax1 = fig.add_subplot(gs[0, :2])
ax1.fill_between(monthly_rev["Month_str"], monthly_rev["Revenue"], alpha=0.3, color="#3266ad")
ax1.plot(monthly_rev["Month_str"], monthly_rev["Revenue"], color="#3266ad", linewidth=2, marker="o", markersize=4)
ax1.set_title("Monthly Revenue Trend", fontsize=11, fontweight="bold")
ax1.set_ylabel("Revenue (BRL)")
ax1.set_xlabel("")
ax1.tick_params(axis="x", rotation=45, labelsize=8)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R${x/1000:.0f}K"))

# Plot 2: Payment breakdown
ax2 = fig.add_subplot(gs[0, 2])
colors_pay = ["#3266ad","#5fa8d3","#ef9f27","#e24b4a"]
ax2.pie(payment_summary["Revenue"], labels=payment_summary["Payment Type"],
        colors=colors_pay[:len(payment_summary)],
        autopct="%1.1f%%", startangle=90, textprops={"fontsize": 9})
ax2.set_title("Revenue by Payment Method", fontsize=11, fontweight="bold")

# Plot 3: Top categories
ax3 = fig.add_subplot(gs[1, :2])
colors_cat = sns.color_palette("Blues_r", len(cat_rev))
bars = ax3.barh(cat_rev["Category"], cat_rev["Revenue"], color=colors_cat)
ax3.set_title("Top 10 Categories by Revenue", fontsize=11, fontweight="bold")
ax3.set_xlabel("Revenue (BRL)")
ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))
ax3.invert_yaxis()

# Plot 4: Review score vs delivery days
ax4 = fig.add_subplot(gs[1, 2])
del_review = (orders_reviews.groupby("review_score")["delivery_days"]
              .mean().reset_index().dropna())
colors_score = ["#e24b4a","#ef9f27","#f5c4b3","#9fe1cb","#1d9e75"]
ax4.bar(del_review["review_score"].astype(int), del_review["delivery_days"],
        color=colors_score[:len(del_review)], edgecolor="none")
ax4.set_title("Avg Delivery Days by Review Score", fontsize=11, fontweight="bold")
ax4.set_xlabel("Review Score (1–5)")
ax4.set_ylabel("Avg Delivery Days")

# Plot 5: Orders per day of week
ax5 = fig.add_subplot(gs[2, 0])
delivered["weekday"] = delivered["order_purchase_timestamp"].dt.day_name()
weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
weekday_cnt = delivered["weekday"].value_counts().reindex(weekday_order)
ax5.bar(range(7), weekday_cnt.values, color="#3266ad", edgecolor="none")
ax5.set_xticks(range(7))
ax5.set_xticklabels(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], fontsize=8)
ax5.set_title("Orders by Day of Week", fontsize=11, fontweight="bold")
ax5.set_ylabel("Order Count")

# Plot 6: Top 10 cities
ax6 = fig.add_subplot(gs[2, 1:])
city_rev = (delivered.merge(customers[["customer_id","customer_city"]], on="customer_id")
            .merge(items_orders[["order_id","total_value"]].groupby("order_id").sum().reset_index(), on="order_id")
            .groupby("customer_city")["total_value"].sum()
            .sort_values(ascending=False).head(10))
ax6.bar(city_rev.index, city_rev.values, color="#3266ad", edgecolor="none")
ax6.set_title("Top 10 Cities by Revenue", fontsize=11, fontweight="bold")
ax6.set_ylabel("Revenue (BRL)")
ax6.set_xticklabels(city_rev.index, rotation=35, ha="right", fontsize=9)
ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))

plt.savefig("ecommerce_eda_report.png", dpi=150, bbox_inches="tight")
print("\nEDA saved as: ecommerce_eda_report.png")
plt.show()


# ─────────────────────────────────────────
# 4. COHORT RETENTION TABLE
# ─────────────────────────────────────────

print("\n=== Customer Cohort Retention ===")

cohort_df = delivered[["customer_id","month","cohort_month"]].drop_duplicates()
cohort_df["period_number"] = (cohort_df["month"] - cohort_df["cohort_month"]).apply(lambda x: x.n)

cohort_counts = (cohort_df.groupby(["cohort_month","period_number"])["customer_id"]
                 .nunique().unstack(fill_value=0))
cohort_size = cohort_counts.iloc[:,0]
retention = cohort_counts.divide(cohort_size, axis=0).round(3) * 100

print(retention.iloc[:8, :6].to_string())
print("\nOverall repeat purchase rate: {:.1f}%".format(
    (delivered.groupby("customer_id")["order_id"].count() > 1).mean() * 100))


# ─────────────────────────────────────────
# 5. KEY INSIGHTS
# ─────────────────────────────────────────

print("\n=== Key Business Insights ===")
top_cat = cat_rev.iloc[0]
peak_month = monthly_rev.loc[monthly_rev["Revenue"].idxmax()]
avg_del = orders_reviews["delivery_days"].mean()
repeat_rate = (delivered.groupby("customer_id")["order_id"].count() > 1).mean() * 100

print(f"1. Top category: {top_cat['Category']} — R${top_cat['Revenue']:,.0f}")
print(f"2. Peak revenue month: {peak_month['Month_str']} — R${peak_month['Revenue']:,.0f}")
print(f"3. Avg delivery time: {avg_del:.1f} days")
print(f"4. Repeat purchase rate: {repeat_rate:.1f}%")
print(f"5. Most popular payment: {payment_summary.iloc[0]['Payment Type']} ({payment_summary.iloc[0]['Revenue']/payment_summary['Revenue'].sum()*100:.1f}%)")
