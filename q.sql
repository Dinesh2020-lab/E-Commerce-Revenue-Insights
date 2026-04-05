-- ================================================================
-- Project 2: E-Commerce Sales & Revenue Insights
-- Dataset: Brazilian E-Commerce (Olist) — Kaggle
-- https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
-- ================================================================
-- Load CSVs into a SQLite or MySQL database using the Python script
-- then run these queries for analysis.
-- ================================================================


-- ── 1. Total revenue & order count ───────────────────────────────
SELECT
    COUNT(DISTINCT o.order_id)                     AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)     AS total_revenue,
    ROUND(AVG(oi.price + oi.freight_value), 2)     AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';


-- ── 2. Monthly revenue trend ──────────────────────────────────────
SELECT
    strftime('%Y-%m', o.order_purchase_timestamp)  AS month,
    COUNT(DISTINCT o.order_id)                     AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)     AS monthly_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY month
ORDER BY month;


-- ── 3. Revenue by product category ───────────────────────────────
SELECT
    p.product_category_name_english               AS category,
    COUNT(DISTINCT o.order_id)                    AS order_count,
    ROUND(SUM(oi.price), 2)                       AS category_revenue,
    ROUND(AVG(oi.price), 2)                       AS avg_item_price
FROM orders o
JOIN order_items oi       ON o.order_id  = oi.order_id
JOIN products pr          ON oi.product_id = pr.product_id
JOIN product_category p   ON pr.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY category
ORDER BY category_revenue DESC
LIMIT 15;


-- ── 4. Customer segmentation (RFM) ───────────────────────────────
WITH rfm AS (
    SELECT
        o.customer_id,
        MAX(o.order_purchase_timestamp)                      AS last_purchase,
        COUNT(DISTINCT o.order_id)                           AS frequency,
        ROUND(SUM(oi.price + oi.freight_value), 2)          AS monetary
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_id
),
rfm_scored AS (
    SELECT *,
        CASE
            WHEN julianday('now') - julianday(last_purchase) <= 90  THEN 3
            WHEN julianday('now') - julianday(last_purchase) <= 180 THEN 2
            ELSE 1
        END AS recency_score,
        CASE WHEN frequency >= 2 THEN 2 ELSE 1 END AS freq_score,
        CASE
            WHEN monetary >= 500 THEN 3
            WHEN monetary >= 200 THEN 2
            ELSE 1
        END AS monetary_score
    FROM rfm
)
SELECT
    CASE
        WHEN recency_score = 3 AND freq_score = 2 THEN 'Champions'
        WHEN recency_score >= 2 AND freq_score >= 2 THEN 'Loyal Customers'
        WHEN recency_score = 3                     THEN 'Recent Customers'
        WHEN recency_score = 1 AND freq_score = 1  THEN 'At Risk'
        ELSE 'Need Attention'
    END AS segment,
    COUNT(*)                           AS customer_count,
    ROUND(AVG(monetary), 2)           AS avg_revenue,
    ROUND(AVG(frequency), 2)          AS avg_orders
FROM rfm_scored
GROUP BY segment
ORDER BY customer_count DESC;


-- ── 5. Customer retention (cohort analysis) ───────────────────────
WITH first_purchase AS (
    SELECT
        customer_id,
        MIN(strftime('%Y-%m', order_purchase_timestamp)) AS cohort_month
    FROM orders
    WHERE order_status = 'delivered'
    GROUP BY customer_id
),
orders_with_cohort AS (
    SELECT
        o.customer_id,
        fp.cohort_month,
        strftime('%Y-%m', o.order_purchase_timestamp) AS order_month
    FROM orders o
    JOIN first_purchase fp ON o.customer_id = fp.customer_id
    WHERE o.order_status = 'delivered'
),
cohort_data AS (
    SELECT
        cohort_month,
        order_month,
        COUNT(DISTINCT customer_id) AS customers
    FROM orders_with_cohort
    GROUP BY cohort_month, order_month
),
cohort_size AS (
    SELECT cohort_month, customers AS cohort_customers
    FROM cohort_data
    WHERE cohort_month = order_month
)
SELECT
    cd.cohort_month,
    cd.order_month,
    cd.customers,
    cs.cohort_customers,
    ROUND(100.0 * cd.customers / cs.cohort_customers, 1) AS retention_rate
FROM cohort_data cd
JOIN cohort_size cs ON cd.cohort_month = cs.cohort_month
ORDER BY cd.cohort_month, cd.order_month;


-- ── 6. Top cities by revenue ──────────────────────────────────────
SELECT
    c.customer_city                                AS city,
    c.customer_state                               AS state,
    COUNT(DISTINCT o.order_id)                     AS orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)    AS revenue
FROM orders o
JOIN order_items oi  ON o.order_id      = oi.order_id
JOIN customers c     ON o.customer_id   = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY city, state
ORDER BY revenue DESC
LIMIT 10;


-- ── 7. Average delivery time vs review score ──────────────────────
SELECT
    r.review_score,
    COUNT(*)                                                      AS order_count,
    ROUND(AVG(
        julianday(o.order_delivered_customer_date) -
        julianday(o.order_purchase_timestamp)
    ), 1)                                                         AS avg_delivery_days
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY r.review_score
ORDER BY r.review_score;


-- ── 8. Payment method breakdown ───────────────────────────────────
SELECT
    op.payment_type,
    COUNT(DISTINCT op.order_id)                   AS order_count,
    ROUND(SUM(op.payment_value), 2)               AS total_revenue,
    ROUND(AVG(op.payment_installments), 1)        AS avg_installments
FROM order_payments op
JOIN orders o ON op.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY op.payment_type
ORDER BY total_revenue DESC;
