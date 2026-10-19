USE tz_teamzero_research_20261016;

-- 1. Historical price vs foreign flows: 20 return intervals, 20 flow observations.
WITH w AS (
 SELECT stock_cd,trd_dt,close_prc,frgn_hold_rt,
 LAG(trd_dt,20) OVER(PARTITION BY stock_cd ORDER BY trd_dt) base_dt,
 LAG(close_prc,20) OVER(PARTITION BY stock_cd ORDER BY trd_dt) base_price,
 LAG(frgn_hold_rt,20) OVER(PARTITION BY stock_cd ORDER BY trd_dt) base_hold,
 SUM(frgn_net_buy_qty) OVER(PARTITION BY stock_cd ORDER BY trd_dt ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) foreign_net20,
 COUNT(frgn_net_buy_qty) OVER(PARTITION BY stock_cd ORDER BY trd_dt ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) flow_count
 FROM g_ai_stock_daily
)
SELECT *,100*(close_prc/base_price-1) return_pct,100*(frgn_hold_rt-base_hold) hold_change_pp
FROM w WHERE trd_dt='2026-06-30' AND stock_cd IN ('005930','000660') AND flow_count=20;

-- 2. Observed valuation. Compare only the same collection snapshot, not June prices.
SELECT * FROM v_research_valuation_comparison
WHERE stock_cd IN ('005930','000660') AND metric IN ('per','pbr','cnsPer');

-- Fiscal-period multiples as retrieved now; NOT a point-in-time daily series.
SELECT stock_cd,period,period_type,metric,value,source_id
FROM research_financial WHERE metric IN ('PER','PBR') AND is_estimate='N'
ORDER BY stock_cd,period_type,period;

-- Provider-selected peer codes and their observed PER/PBR.
SELECT p.stock_cd AS subject_stock,j.peer_code,v.metric,v.value,v.observed_at
FROM research_company_info p
JOIN JSON_TABLE(p.info_json,'$[*]' COLUMNS(peer_code CHAR(6) PATH '$')) j ON TRUE
JOIN research_valuation v ON v.stock_cd=j.peer_code
WHERE p.category='provider_peer_group' AND v.metric IN ('per','pbr');

-- 3. Legacy financials with period/quality flags retained.
SELECT * FROM v_research_cash_inventory_capex ORDER BY corp_cd,bsns_yr,rpt_cd,mtrc_cd;
SELECT * FROM research_financial WHERE metric IN ('매출액','영업이익','당기순이익')
ORDER BY stock_cd,period_type,period;

-- 4. Official cash/inventory/investment/segment evidence and corporate outlook.
SELECT m.*,s.url,s.sha256 FROM research_official_metric m
JOIN research_source s ON m.source_id=s.source_id;
SELECT n.*,s.url FROM research_official_note n JOIN research_source s ON n.source_id=s.source_id;
SELECT * FROM research_company_info WHERE category='consensusInfo';

-- Raw source evidence for any extracted value.
SELECT source_id,stock_cd,kind,url,retrieved_at,sha256,bytes FROM research_source;
