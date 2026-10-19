"""Add visually checked official report evidence to an existing collection.

Numbers retain the report's precision. This is curated extraction, not OCR.
"""
import argparse
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

CHECKED_PDFS = {
    'samsung_interim_1q26': '76eeea46437b2bb0980f0d11efde39ff92c5e128ad92b4e206ebae58d7f1c669',
    'samsung_earnings_1q26': '33140e1501207e19741efa7220b9cd39a4f68ba288854b526ab26a6a17e1db83',
}
CHECKED_IMAGE = '2bea12b609aa2e500880d71edb38c76bc990a6b909bfe037ec8bd51ff9e8fb1a'


def require_checked(body, expected):
    if hashlib.sha256(body).hexdigest() != expected:
        raise ValueError('Official source changed: visually review before using curated values')


def enrich(folder):
    path = folder / 'collection.json'
    bundle = json.loads(path.read_text())
    source_id = 'hynix_earnings_1q26_infographic'
    if any(s['source_id'] == source_id for s in bundle['sources']):
        raise ValueError('Official enrichment already present')
    sources = {s['source_id']: s for s in bundle['sources']}
    for sid, expected in CHECKED_PDFS.items():
        require_checked((folder / sources[sid]['raw_path']).read_bytes(), expected)
    url = 'https://d18r0a86za96sg.cloudfront.net/wp-content/uploads/2026/05/26155231/SK-hynix-Announces-1Q26-Financial-Results_info_2026_2.jpg'
    with urllib.request.urlopen(url, timeout=30) as response:
        body = response.read()
    if not body.startswith(b'\xff\xd8'):
        raise ValueError('Expected official JPEG attachment')
    require_checked(body, CHECKED_IMAGE)
    target = folder / 'raw' / (source_id + '.jpg')
    target.write_bytes(body)
    bundle['sources'].append(dict(source_id=source_id, stock_cd='000660', kind='official_earnings_image',
        url=url, retrieved_at=dt.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds'),
        sha256=hashlib.sha256(body).hexdigest(), raw_path=str(target.relative_to(folder)),
        content_type='image/jpeg', bytes=len(body)))
    # Samsung pages 30 and 39: consolidated KRW columns, not adjacent USD columns.
    # Inventory is a point-in-time balance; operating cash and acquisitions are Q1 flows.
    metrics = []
    def add(stock, metric, period, period_type, value, source, location):
        metrics.append(dict(stock_cd=stock, metric=metric, period=period, period_type=period_type,
            fs_div_cd='CFS', value=str(value), unit='KRW', source_id=source,
            source_location=location, historical_pit_eligible='N', review_status='VISUALLY_CHECKED'))
    for metric, page, values in [
        ('INVENTORIES', 30, [('202603', 58278373), ('202512', 52636828)]),
        ('OPERATING_CASH_FLOW', 39, [('202603', 40274106), ('202503', 16580866)]),
        ('PPE_ACQUISITION_CASH_OUTFLOW_SIGNED', 39, [('202603', -17127003), ('202503', -12127934)]),
        ('INTANGIBLE_ACQUISITION_CASH_OUTFLOW_SIGNED', 39, [('202603', -1049952), ('202503', -1257544)]),
    ]:
        for period, value in values:
            add('005930', metric, period, 'ASOF' if metric == 'INVENTORIES' else 'Q3M',
                value * 1000000, 'samsung_interim_1q26', 'PDF page ' + str(page) + '; KRW million column')
    # Segment values include intersegment sales and must not be summed to consolidated revenue.
    for segment, revenue, profit in [('DS', 81700000000000, 53700000000000),
                                     ('DX', 52700000000000, 3000000000000),
                                     ('SDC', 6700000000000, 400000000000),
                                     ('HARMAN', 3800000000000, 200000000000)]:
        for suffix, value in [('REVENUE', revenue), ('OPERATING_PROFIT', profit)]:
            add('005930', segment + '_' + suffix, '202603', 'Q3M', value,
                'samsung_earnings_1q26', 'PDF page 6; KRW trillion, rounded presentation value')
    for metric, value in [('REVENUE', 52576300000000), ('OPERATING_PROFIT', 37610300000000),
                          ('NET_INCOME', 40345900000000), ('CASH_AND_CASH_EQUIVALENTS', 54300000000000),
                          ('BORROWINGS', 19300000000000), ('NET_CASH', 35000000000000)]:
        add('000660', metric, '202603', 'Q3M' if metric in ['REVENUE', 'OPERATING_PROFIT', 'NET_INCOME'] else 'ASOF',
            value, source_id, 'Official Q1 2026 infographic; KRW trillion; published precision retained')
    notes = [
        dict(stock_cd='005930', topic='BUSINESS_OUTLOOK', period='2026Q2/H2',
             note_ko='회사는 AI 인프라 확장에 따른 메모리 수요 지속과 HBM4E 샘플 공급, 고부가 AI 제품 판매 확대를 전망했다. 회사의 전망이며 실현된 실적이 아니다.',
             source_id='samsung_earnings_1q26', source_location='PDF page 7, Outlook', is_forecast='Y'),
        dict(stock_cd='000660', topic='PRODUCT_AND_DEMAND_OUTLOOK', period='2026Q1 release',
             note_ko='회사는 AI 수요에 따른 HBM·고용량 서버 DRAM·eSSD 판매 확대를 설명하고, Agentic AI와 메모리 효율 기술에 따른 DRAM·NAND 수요 확대를 전망했다. 회사의 설명이며 주가 상승 원인으로 확정하지 않는다.',
             source_id=source_id, source_location='Q1 Key Results & Market Outlook / Product Status', is_forecast='Y'),
    ]
    # The Hynix HTML is an image wrapper. Do not label menu text as extracted earnings content.
    for doc in bundle['tables']['ir_document']:
        if doc['source_id'] == 'hynix_earnings_1q26':
            doc['review_status'] = 'IMAGE_WRAPPER_SEE_OFFICIAL_INFOGRAPHIC'
    bundle['tables']['official_metric'] = metrics
    bundle['tables']['official_note'] = notes
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))
    summary = dict(sources=len(bundle['sources']), errors=bundle['errors'],
                   tables={k: len(v) for k, v in bundle['tables'].items()})
    (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True)
    enrich(parser.parse_args().collection)
