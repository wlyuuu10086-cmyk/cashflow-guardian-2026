SHOW TABLES;
SELECT * FROM vw_table_row_counts ORDER BY row_count DESC;
SELECT industry, region, COUNT(*) AS business_count FROM business_customers GROUP BY 1,2 ORDER BY 3 DESC;
SELECT payment_status, COUNT(*) AS rows, AVG(days_past_due) AS avg_dpd FROM repayments GROUP BY 1 ORDER BY 2 DESC;
