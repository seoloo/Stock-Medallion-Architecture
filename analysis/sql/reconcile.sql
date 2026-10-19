-- C expected-result contract. Execute against the accepted Gold database.
-- Session arithmetic setting only; no stored data is modified.
SET SESSION div_precision_increment = 30;
-- B must load the reviewed c-gold-0.1.0 schemas first; NULL fields are SQL NULL.
-- Compare numerically as Decimal strings, ignoring trailing decimal zeros.
SELECT 'financial_rows' AS check_id, CAST(COUNT(*) AS CHAR) AS result FROM tz_gold.g_fin_rpt_analysis
UNION ALL SELECT 'daily_rows', CAST(COUNT(*) AS CHAR) FROM tz_gold.g_stock_daily_analysis
UNION ALL SELECT 'financial_pk_duplicates', CAST(COUNT(*) - COUNT(DISTINCT fin_rpt_id) AS CHAR) FROM tz_gold.g_fin_rpt_analysis
UNION ALL SELECT 'daily_pk_duplicates', CAST(COUNT(*) - COUNT(DISTINCT stock_cd, trd_dt) AS CHAR) FROM tz_gold.g_stock_daily_analysis
UNION ALL SELECT 'pit_date_violations', CAST(COUNT(*) AS CHAR) FROM tz_gold.g_stock_daily_analysis WHERE dscl_dt >= trd_dt
UNION ALL SELECT 'rev_ytd_sum_amt', CAST(SUM(rev_ytd_amt) AS CHAR) FROM tz_gold.g_fin_rpt_analysis
UNION ALL SELECT 'op_cf_ytd_sum_amt', CAST(SUM(op_cf_ytd_amt) AS CHAR) FROM tz_gold.g_fin_rpt_analysis
UNION ALL SELECT 'close_prc_sum', CAST(SUM(close_prc) AS CHAR) FROM tz_gold.g_stock_daily_analysis
UNION ALL SELECT 'frgn_daily_net_sum_qty', CAST(SUM(frgn_net_buy_qty) AS CHAR) FROM tz_gold.g_stock_daily_analysis
UNION ALL SELECT 'inst_daily_net_sum_qty', CAST(SUM(inst_net_buy_qty) AS CHAR) FROM tz_gold.g_stock_daily_analysis;

-- Business-rule comparison: exact stored half-up ratios, same-period eligible only.
SELECT COUNT(*) AS revenue_growth_mismatches
FROM tz_gold.g_fin_rpt_analysis
WHERE rev_yoy_rt_stts_cd = 'OK'
  AND rev_yoy_rt <> ROUND(rev_ytd_amt / rev_prior_ytd_amt - 1, 8);

SELECT co_move_cd, COUNT(*) AS row_count FROM tz_gold.g_stock_daily_analysis GROUP BY co_move_cd;
-- Retain source review flags. No UPDATE, DELETE, DROP or automated repair.
