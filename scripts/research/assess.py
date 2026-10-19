"""Team forecast v1: explain elevated valuation, earnings weakness and missing cash data.

This is an uncalibrated, explicit screening rule, not a bubble probability model.
Only the collected October snapshot is evaluated. No June backfilling.
"""
import argparse
import getpass
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from statistics import median

import pymysql

VERSION = 'overheating-forecast-0.2.0'
ROOT = Path(__file__).resolve().parents[2]
LABELS = {'STRONG': '과열 가능성을 높게 예상', 'WATCH': '과열 가능성이 일부 있다고 예상',
          'NOT_MET': '과열 가능성을 낮게 예상'}


def positive(value):
    return value is not None and value > 0


def classify(history_ratio, peer_ratio, revenue_growth, operating_current, operating_prior, threshold):
    """Require both valuation comparisons and matched actual financials before grading."""
    if any(v is None for v in [history_ratio, peer_ratio, revenue_growth, operating_current, operating_prior]):
        raise ValueError('Required forecast inputs missing; repair the input dataset')
    expensive_history = history_ratio >= threshold
    expensive_peers = peer_ratio >= threshold
    earnings_weak = operating_current <= 0 or operating_current < operating_prior or revenue_growth < 0
    if expensive_history and expensive_peers and earnings_weak:
        return 'STRONG'
    if expensive_history or expensive_peers:
        return 'WATCH'
    return 'NOT_MET'


def evaluate(bundle):
    tables = bundle['tables']
    values = {(r['stock_cd'], r['metric']): Decimal(r['value']) if r['value'] is not None else None
              for r in tables['valuation']}
    fin = {(r['stock_cd'], r['period_type'], r['period'], r['metric']):
           Decimal(r['value']) if r['value'] is not None else None
           for r in tables['financial'] if r['is_estimate'] == 'N'}
    names = bundle['stock_names']
    peers = {r['stock_cd']: json.loads(r['info_json']) for r in tables['company_info']
             if r['category'] == 'provider_peer_group'}
    rows = []
    for stock, name in names.items():
        pbr = values.get((stock, 'pbr'))
        history = sorted((period, value) for (code, kind, period, metric), value in fin.items()
                         if code == stock and kind == 'annual' and metric == 'PBR' and positive(value))
        history_median = median([v for _, v in history]) if len(history) >= 3 else None
        peer_values = [values.get((p, 'pbr')) for p in peers.get(stock, []) if p != stock]
        peer_values = [v for v in peer_values if positive(v)]
        peer_median = median(peer_values) if len(peer_values) >= 3 else None
        history_ratio = pbr / history_median if positive(pbr) and positive(history_median) else None
        peer_ratio = pbr / peer_median if positive(pbr) and positive(peer_median) else None
        # Require a matching prior-year quarter. Forecast rows were excluded above.
        matched = []
        for code, kind, period, metric in fin:
            if code == stock and kind == 'quarter' and metric == '매출액':
                prior = str(int(period[:4]) - 1) + period[4:]
                if all(fin.get((stock, 'quarter', p, m)) is not None
                       for p in [period, prior] for m in ['매출액', '영업이익']):
                    matched.append(period)
        period = max(matched) if matched else None
        prior = str(int(period[:4]) - 1) + period[4:] if period else None
        revenue = fin.get((stock, 'quarter', period, '매출액'))
        base_revenue = fin.get((stock, 'quarter', prior, '매출액'))
        operating = fin.get((stock, 'quarter', period, '영업이익'))
        base_operating = fin.get((stock, 'quarter', prior, '영업이익'))
        growth = revenue / base_revenue - 1 if positive(base_revenue) and revenue is not None else None
        status = classify(history_ratio, peer_ratio, growth, operating, base_operating, Decimal('1.5'))
        sensitivity = {str(t): classify(history_ratio, peer_ratio, growth, operating, base_operating, t)
                       for t in [Decimal('1.25'), Decimal('1.5'), Decimal('2.0')]}
        market = sorted((r for r in tables['market_daily'] if r['stock_cd'] == stock), key=lambda r: r['trd_dt'])
        flow = sum(Decimal(r['frgn_net_buy_qty']) for r in market) if market and all(r['frgn_net_buy_qty'] is not None for r in market) else None
        price_change = Decimal(market[-1]['close_prc']) / Decimal(market[0]['close_prc']) - 1 if len(market) >= 2 and all(r['close_prc'] is not None for r in market) else None
        # Official cash rows currently cover Samsung Q1; do not relabel them as Q2.
        cash = [r for r in tables.get('official_metric', []) if r['stock_cd'] == stock
                and r['metric'] == 'OPERATING_CASH_FLOW' and r['period'] == period]
        reasons = []
        if history_ratio is not None:
            reasons.append(f'현재 PBR / 과거 3개 연말 PBR 중앙값 {history_ratio:.2f}배')
        else:
            reasons.append('양수 PBR 연말 관측 3개 부족 또는 현재 PBR 없음')
        if peer_ratio is not None:
            reasons.append(f'현재 PBR / 제공사 비교군 PBR 중앙값 {peer_ratio:.2f}배')
        else:
            reasons.append('양수 PBR 비교군 3개 부족')
        if growth is not None:
            reasons.append(f'{period} 분기 매출 전년동기 {growth * 100:+.2f}%')
        if operating is not None and base_operating is not None:
            reasons.append('영업이익 ' + ('적자' if operating <= 0 else '감소' if operating < base_operating else '증가 또는 유지'))
        if flow is not None:
            reasons.append(f'별도 단기 수급 {len(market)}개 관측 순매수 {flow:,.0f}주; 등급 가감 없음')
        reasons.append('같은 최신 분기 영업현금흐름 ' + ('원문 수치 존재; 정량등급 미반영' if cash else '정량등급 미반영'))
        if len(set(sensitivity.values())) > 1:
            reasons.append('비교 임계값에 따라 등급 변경: 민감한 결과')
        rows.append(dict(stock_cd=stock, stock_nm=name, status=status, label=LABELS[status],
            assessment_scope='TEAM_VALUATION_EARNINGS_FORECAST',
            current_pbr=pbr, historical_pbr_median=history_median, historical_periods=[p for p, _ in history],
            historical_pbr_ratio=history_ratio, provider_peer_pbr_median=peer_median,
            provider_peer_pbr_ratio=peer_ratio, peer_count=len(peer_values), peer_codes=peers.get(stock, []),
            financial_period=period, revenue_yoy=growth, operating_profit=operating, prior_operating_profit=base_operating,
            cash_review_complete=False, short_foreign_net_qty=flow, short_price_return=price_change,
            short_price_intervals=max(0, len(market)-1), flow_observations=len(market),
            flow_start=market[0]['trd_dt'] if market else None, flow_end=market[-1]['trd_dt'] if market else None,
            sensitivity=sensitivity, reasons=reasons, version=VERSION))
    return rows


# Provider level values omitted from the public results file (ratios, labels and reasons are kept).
RAW_FIELDS = ('current_pbr', 'historical_pbr_median', 'provider_peer_pbr_median', 'operating_profit',
              'prior_operating_profit', 'short_foreign_net_qty', 'short_price_return')


def published(result):
    rows = [{k: v for k, v in r.items() if k not in RAW_FIELDS} for r in result['rows']]
    note = ('Provider level values (PBR levels, medians, operating profit amounts, short-window flow and '
            'return) are omitted from the public file. Full results and inputs are regenerated locally '
            'under build/research/ by scripts/research/assess.py.')
    return {**{k: v for k, v in result.items() if k != 'rows'}, 'rows': rows, 'published_fields_note': note}


def run(folder, schema, password):
    from load_mysql import qi
    data = json.loads((folder / 'collection.json').read_text())
    if not data['collection_started_at'].startswith('2026-10-16'):
        raise ValueError('This published rule version is pinned to the 2026-10-16 snapshot')
    with (ROOT / 'data/03_C_integration_20261014/04_output/silver/s_stock.csv').open(encoding='utf-8-sig') as f:
        import csv
        data['stock_names'] = {r['stock_cd']: r['stock_nm'] for r in csv.DictReader(f)}
    rows = evaluate(data)
    # Store the exact public screen inputs so anyone can reproduce without DB credentials.
    public = dict(stock_names=data['stock_names'], tables={k: data['tables'][k] for k in
                  ['valuation', 'financial', 'company_info', 'market_daily', 'official_metric']})
    # Only the twenty subjects and the peer PBRs needed by this screen are retained.
    public['tables']['valuation'] = [r for r in public['tables']['valuation'] if r['metric'] == 'pbr']
    public['tables']['financial'] = [r for r in public['tables']['financial'] if r['is_estimate'] == 'N'
                                   and r['metric'] in ['PBR', '매출액', '영업이익']]
    public['tables']['company_info'] = [r for r in public['tables']['company_info'] if r['category'] == 'provider_peer_group']
    public['tables']['market_daily'] = [r for r in public['tables']['market_daily'] if r['stock_cd'] in data['stock_names']]
    public['sources'] = [s for s in data['sources'] if s['kind'] in ['integration','finance/annual','finance/quarter']]
    # Collected provider values stay local (build/ is git-ignored); only derived results are published.
    local = ROOT / 'build/research'
    local.mkdir(parents=True, exist_ok=True)
    (local / 'assessment-inputs.json').write_text(json.dumps(public, ensure_ascii=False, indent=2))
    result = dict(version=VERSION, snapshot_date='2026-10-16', threshold='1.5',
                  counts=dict(Counter(r['label'] for r in rows)), rows=rows)
    serialized = json.loads(json.dumps(result, ensure_ascii=False, default=str))
    (local / 'assessment-results.json').write_text(json.dumps(serialized, ensure_ascii=False, indent=2))
    (ROOT / 'docs/research/assessment-results.json').write_text(
        json.dumps(published(serialized), ensure_ascii=False, indent=2))
    con = pymysql.connect(host='127.0.0.1', user='root', password=password, database=schema, charset='utf8mb4')
    table = 'research_overheating_assessment_v1'
    try:
        with con.cursor() as q:
            q.execute('CREATE TABLE IF NOT EXISTS ' + qi(table) + ' (stock_cd CHAR(6) PRIMARY KEY,snapshot_date DATE NOT NULL,status VARCHAR(30) NOT NULL,label VARCHAR(100) NOT NULL,version VARCHAR(100) NOT NULL,result_json JSON NOT NULL)')
            q.execute('SELECT DISTINCT version FROM ' + qi(table))
            assert all(v[0] in ['overheating-evidence-0.1.0', VERSION] for v in q.fetchall()), 'Unexpected existing assessment version'
            for row in serialized['rows']:
                payload = json.dumps(row, ensure_ascii=False)
                q.execute('SELECT COUNT(*) FROM ' + qi(table) + ' WHERE stock_cd=%s', (row['stock_cd'],))
                if q.fetchone()[0]:
                    q.execute('UPDATE ' + qi(table) + ' SET snapshot_date=%s,status=%s,label=%s,version=%s,result_json=%s WHERE stock_cd=%s',
                              ('2026-10-16',row['status'],row['label'],VERSION,payload,row['stock_cd']))
                else:
                    q.execute('INSERT INTO ' + qi(table) + ' VALUES (%s,%s,%s,%s,%s,%s)',
                              (row['stock_cd'],'2026-10-16',row['status'],row['label'],VERSION,payload))
            con.commit()
            q.execute('SELECT stock_cd,result_json FROM ' + qi(table))
            actual = {code: json.loads(payload) for code,payload in q.fetchall()}
            assert actual == {r['stock_cd']: r for r in serialized['rows']}
    finally:
        con.close()
    print(json.dumps(serialized['counts'], ensure_ascii=False))
    for row in rows:
        print(row['stock_nm'], row['label'], ' / '.join(row['reasons']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=Path, required=True)
    p.add_argument('--schema', default='tz_teamzero_research_20261016')
    a = p.parse_args()
    run(a.collection, a.schema, getpass.getpass('MySQL password: '))
