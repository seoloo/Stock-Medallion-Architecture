"""Collect additional valuation evidence; never modify the pinned handoff.

Uses public Naver stock responses and official company IR documents.
Raw files are local artifacts, not automatically committed.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / 'data/03_C_integration_20261014/04_output/silver'
API = 'https://m.stock.naver.com/api/stock/'


def number(value):
    """Keep exact decimal strings. Missing is not zero."""
    if value is None:
        return None
    s = str(value).strip().replace(',', '').replace('−', '-')
    s = re.sub(r'(배|원|%)$', '', s)
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        n = Decimal(s)
        return format(n, 'f') if n.is_finite() else None
    except InvalidOperation:
        return None


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0; self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'tr', 'br'):
            self.parts.append('\n')
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def collect(out):
    out.mkdir(parents=True, exist_ok=False)
    (out / 'raw').mkdir()
    timestamp = dt.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    sources, errors = [], []
    tables = {k: [] for k in ['market_daily', 'valuation', 'financial', 'company_info', 'ir_document']}

    def fetch(job):
        key, url, stock, kind = job
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=40) as response:
                body = response.read(); content_type = response.headers.get('Content-Type', '')
            if not body:
                raise ValueError('Empty response')
            suffix = '.pdf' if body.startswith(b'%PDF') else '.json' if 'json' in content_type else '.html'
            path = out / 'raw' / (key + suffix)
            path.write_bytes(body)
            source = dict(source_id=key, stock_cd=stock, kind=kind, url=url,
                          retrieved_at=dt.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds'),
                          sha256=hashlib.sha256(body).hexdigest(), raw_path=str(path.relative_to(out)),
                          content_type=content_type, bytes=len(body))
            return source, body
        except Exception as exc:
            return dict(source_id=key, url=url, error=f'{type(exc).__name__}: {exc}'), None

    with (SILVER / 's_stock.csv').open(encoding='utf-8-sig') as f:
        stocks = list(csv.DictReader(f))
    jobs = [(code + '_' + endpoint.replace('/', '_'), API + code + '/' + endpoint, code, endpoint)
            for code in [s['stock_cd'] for s in stocks]
            for endpoint in ['basic', 'integration', 'finance/annual', 'finance/quarter']]
    responses = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for source, body in pool.map(fetch, jobs):
            if body is None:
                errors.append(source); continue
            sources.append(source)
            responses[(source['stock_cd'], source['kind'])] = (source, json.loads(body))

    # The provider's peer group is stored explicitly; it is not an analyst-selected comparable set.
    peer_pairs = set()
    for (stock, kind), (source, data) in responses.items():
        if kind == 'integration':
            peer_pairs.update((stock, peer['itemCode']) for peer in data.get('industryCompareInfo') or []
                              if re.fullmatch(r'\d{6}', peer.get('itemCode', '')))
    peer_codes = {peer for _, peer in peer_pairs} - {s['stock_cd'] for s in stocks}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [(c + '_integration', API + c + '/integration', c, 'integration') for c in sorted(peer_codes)]
        for source, body in pool.map(fetch, jobs):
            if body is None:
                errors.append(source); continue
            sources.append(source)
            responses[(source['stock_cd'], 'integration')] = source, json.loads(body)

    for (stock, kind), (source, data) in responses.items():
        sid = source['source_id']
        if data.get('itemCode') != stock:
            raise ValueError('Response stock mismatch: ' + stock)
        if kind == 'integration':
            for row in data.get('totalInfos') or []:
                metric = row['code']
                if metric in ['per', 'pbr', 'eps', 'bps', 'cnsPer', 'cnsEps', 'dividendYieldRatio', 'dividend', 'foreignRate']:
                    raw = row.get('value'); value = number(raw)
                    unit = 'ratio' if metric in ['foreignRate', 'dividendYieldRatio'] else 'KRW/share' if metric in ['eps', 'bps', 'cnsEps', 'dividend'] else 'multiple'
                    if unit == 'ratio' and value is not None:
                        value = str(Decimal(value) / 100)
                    tables['valuation'].append(dict(stock_cd=stock, metric=metric, value=value,
                        unit=unit, raw_value=raw, reference_period=row.get('valueDesc'),
                        observed_at=source['retrieved_at'], source_id=sid, historical_pit_eligible='N'))
            for row in data.get('dealTrendInfos') or []:
                day = row['bizdate']
                tables['market_daily'].append(dict(stock_cd=stock, trd_dt=dt.datetime.strptime(day, '%Y%m%d').date().isoformat(),
                    close_prc=number(row.get('closePrice')), frgn_net_buy_qty=number(row.get('foreignerPureBuyQuant')),
                    inst_net_buy_qty=number(row.get('organPureBuyQuant')), indv_net_buy_qty=number(row.get('individualPureBuyQuant')),
                    frgn_hold_rt=str(Decimal(number(row['foreignerHoldRatio'])) / 100) if number(row.get('foreignerHoldRatio')) is not None else None,
                    source_id=sid))
            for category in ['consensusInfo', 'irScheduleInfo']:
                if data.get(category):
                    tables['company_info'].append(dict(stock_cd=stock, category=category,
                        info_json=json.dumps(data[category], ensure_ascii=False), source_id=sid))
        if kind.startswith('finance/'):
            info = data.get('financeInfo') or {}
            periods = {p['key']: p for p in info.get('trTitleList', [])}
            for row in info.get('rowList', []):
                metric = row['title']
                for period, cell in row.get('columns', {}).items():
                    if period not in periods:
                        raise ValueError('Unknown financial period')
                    value = number(cell.get('value'))
                    unit = 'KRW' if metric in ['매출액', '영업이익', '당기순이익', '지배주주순이익', '비지배주주순이익'] else 'KRW/share' if metric in ['EPS', 'BPS', '주당배당금'] else 'multiple' if metric in ['PER', 'PBR'] else 'ratio'
                    if value is not None:
                        value = str(Decimal(value) * (100000000 if unit == 'KRW' else Decimal('.01') if unit == 'ratio' else 1))
                    tables['financial'].append(dict(stock_cd=stock, period=period, period_type=kind.split('/')[1],
                        is_estimate=periods[period]['isConsensus'], metric=metric, value=value, unit=unit,
                        raw_value=cell.get('value'), source_id=sid, historical_pit_eligible='N'))
            if data.get('corporationSummary'):
                tables['company_info'].append(dict(stock_cd=stock, category=kind + '/summary',
                    info_json=json.dumps(data['corporationSummary'], ensure_ascii=False), source_id=sid))

    for stock in sorted({a for a, _ in peer_pairs}):
        tables['company_info'].append(dict(stock_cd=stock, category='provider_peer_group',
            info_json=json.dumps(sorted(b for a, b in peer_pairs if a == stock)), source_id=stock + '_integration'))

    official = [
        ('samsung_interim_1q26', 'https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_1Q_Interim_Report.pdf', '005930', 'official_financial_report'),
        ('samsung_earnings_1q26', 'https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_1Q_conference_eng.pdf', '005930', 'official_earnings'),
        ('hynix_earnings_1q26', 'https://news.skhynix.com/en/q1-2026-business-results-1/', '000660', 'official_earnings'),
    ]
    for job in official:
        source, body = fetch(job)
        if body is None:
            errors.append(source); continue
        sources.append(source)
        if body.startswith(b'%PDF'):
            path = out / source['raw_path']
            txt = path.with_suffix('.txt')
            subprocess.run(['pdftotext', '-layout', str(path), str(txt)], check=True)
            text = txt.read_text()
        else:
            parser = Text(); parser.feed(body.decode('utf-8-sig'))
            text = re.sub(r'\n\s*\n+', '\n\n', ''.join(parser.parts))
        if len(text.strip()) < 100:
            raise ValueError('IR extraction too short')
        tables['ir_document'].append(dict(stock_cd=source['stock_cd'], title=source['source_id'],
            document_period='2026Q1', body_text=text, source_id=source['source_id'],
            historical_pit_eligible='N', review_status='EXTRACTED_PUBLICATION_DATE_REQUIRES_VERIFICATION'))

    result = dict(collection_started_at=timestamp, legacy_cutoff='2026-06-30', sources=sources,
                  errors=errors, tables=tables, base_stock_count=len(stocks), peer_stock_count=len(peer_codes))
    (out / 'collection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    summary = dict(sources=len(sources), errors=errors, tables={k: len(v) for k, v in tables.items()})
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))
    if errors:
        raise SystemExit('Partial collection: inspect errors before reporting complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    collect(args.out.resolve())
