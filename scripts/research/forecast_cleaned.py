"""Forecast from the pinned, cleaned handoff only; no new external data.

Five sign indicators, >=4 positive: outperform; <=1: underperform; otherwise mixed.
These are team hypotheses for the next 20 trading days, not measured accuracy.
"""
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'data/03_C_integration_20261014'
VERSION = 'cleaned-outlook-0.1.0'
AS_OF = '2026-06-30'


def read(relative):
    with (PACKAGE / relative).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def classify(flags):
    if len(flags) != 5 or any(type(flag) is not bool for flag in flags):
        raise ValueError('Five complete boolean indicators required')
    n = sum(flags)
    return '시장 대비 강세 예상' if n >= 4 else '시장 대비 약세 예상' if n <= 1 else '혼조 예상'


def calculate():
    names = {r['stock_cd']: r['stock_nm'] for r in read('04_output/silver/s_stock.csv')}
    reports = {r['fin_rpt_id']: r for r in read('04_output/silver/s_fin_rpt.csv')}
    metrics = {(r['fin_rpt_id'],r['mtrc_cd'],r['prd_type_cd']): Decimal(r['mtrc_amt'])
               for r in read('04_output/silver/s_fin_mtrc.csv') if r['mtrc_amt'] != ''}
    daily = read('04_output/gold/g_ai_stock_daily.csv')
    output = []
    for stock,name in names.items():
        history = sorted((r for r in daily if r['stock_cd']==stock and r['trd_dt'] <= AS_OF), key=lambda r:r['trd_dt'])
        end = history[-1]
        if end['trd_dt'] != AS_OF or end['fin_avail_yn'] != 'Y' or len(history) < 21:
            raise ValueError('Incomplete historical snapshot '+stock)
        report = reports[end['fin_rpt_id']]
        if not (end['dscl_dt'] < AS_OF and report['same_prd_cmpr_elig_yn']=='Y'
                and report['pit_join_elig_yn']=='Y' and report['cf_prd_stts_cd']=='VERIFIED_XML_YTD'):
            raise ValueError('Unverified report used: '+stock)
        def metric(code,period):
            return metrics[(end['fin_rpt_id'],code,period)]
        revenue,prior_revenue = metric('REVENUE','YTD'),metric('REVENUE','PRIOR_YTD')
        if prior_revenue <= 0:
            raise ValueError('Nonpositive revenue denominator')
        revenue_growth = revenue/prior_revenue-1
        cash_change = metric('OPERATING_CASH_FLOW','YTD')-metric('OPERATING_CASH_FLOW','PRIOR_YTD')
        # Public report baseline: latest observed trading date strictly before disclosure.
        before = [r for r in history if r['trd_dt'] < end['dscl_dt']]
        if not before:
            raise ValueError('Missing pre-disclosure price')
        base = before[-1]
        relative = Decimal(end['close_prc'])/Decimal(base['close_prc'])-Decimal(end['idx_close_prc'])/Decimal(base['idx_close_prc'])
        window = history[-20:]
        if any(r[c]=='' for r in window for c in ['frgn_net_buy_qty','inst_net_buy_qty']):
            raise ValueError('Missing flow observation')
        foreign = sum(Decimal(r['frgn_net_buy_qty']) for r in window)
        institution = sum(Decimal(r['inst_net_buy_qty']) for r in window)
        flags = [revenue_growth>0, relative>0, cash_change>0, foreign>0, institution>0]
        output.append(dict(stock_cd=stock,stock_nm=name,as_of=AS_OF,
            forecast=classify(flags),positive_count=sum(flags),
            revenue_yoy=revenue_growth,post_disclosure_excess_return=relative,
            operating_cash_change_krw=cash_change,foreign_net_20obs_shares=foreign,
            institution_net_20obs_shares=institution,report_id=end['fin_rpt_id'],
            disclosure_date=end['dscl_dt'],financial_year=report['bsns_yr'],
            report_type=report['rpt_cd'],fs_div=report['fs_div_cd'],
            flow_start=window[0]['trd_dt'],flow_end=window[-1]['trd_dt'],
            positive_flags=flags,version=VERSION))
    return output


if __name__ == '__main__':
    rows=calculate()
    files=['04_output/gold/g_ai_stock_daily.csv','04_output/silver/s_fin_rpt.csv',
           '04_output/silver/s_fin_mtrc.csv','04_output/silver/s_stock.csv']
    result=dict(version=VERSION,as_of=AS_OF,target='next 20 trading days: stock return minus same-market index return',
                empirical_accuracy_evaluated=False,counts=dict(Counter(r['forecast'] for r in rows)),
                sources=[dict(path=str(PACKAGE.relative_to(ROOT)/p),sha256=hashlib.sha256((PACKAGE/p).read_bytes()).hexdigest()) for p in files],rows=rows)
    path=ROOT/'docs/research/cleaned-data-forecast.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str))
    print(json.dumps(result['counts'],ensure_ascii=False))
    for r in rows:
        print(r['stock_nm'],r['forecast'],r['positive_count'],str(r['revenue_yoy']),str(r['operating_cash_change_krw']))
