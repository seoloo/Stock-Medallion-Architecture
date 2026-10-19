"""Verify a prepared Gold Delta snapshot against a new isolated MySQL database.

Run with B's locked Python environment. Never targets an existing database.
"""
import argparse
import getpass
import json
import sys
from decimal import Decimal, getcontext
from pathlib import Path


def verify(run, host, port, user, password):
    getcontext().prec = 80
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project / 'backend/service'))
    sys.path.insert(0, str(project / 'backend/medallion_pipeline'))
    import engine
    import pymysql
    from import_analysis import mysql_load
    from mysql_load import qi

    catalog = json.loads((run / 'catalog.json').read_text(encoding='utf-8'))
    mysql_load(run, catalog, host, port, user, password)
    db = qi(catalog['database'])
    checks = []
    con = pymysql.connect(host=host, port=port, user=user, password=password, charset='utf8mb4')
    try:
        with con.cursor() as cur:
            cur.execute('SELECT VERSION()')
            version = cur.fetchone()[0]
            # MySQL defaults to only four extra division digits; preserve Q8 rounding.
            cur.execute('SET SESSION div_precision_increment = 30')
            for entry in catalog['tables']:
                # Independently derive exact expected sums and NULL counts from Delta.
                rows = engine.load_delta(run, entry).to_pylist()
                for col in entry['columns']:
                    name = col['name']
                    cur.execute(f'SELECT COUNT(*)-COUNT({qi(name)}) FROM {db}.{qi(entry["name"])}')
                    actual = cur.fetchone()[0]
                    expected = sum(r[name] is None for r in rows)
                    checks.append(dict(check=entry['name']+'.'+name+'.nulls', actual=actual, expected=expected, passed=actual == expected))
                    if col['sql'].startswith(('DECIMAL', 'INT', 'BIGINT')):
                        values = [Decimal(str(r[name])) for r in rows if r[name] is not None]
                        expected = sum(values, Decimal(0)) if values else None
                        cur.execute(f'SELECT SUM({qi(name)}) FROM {db}.{qi(entry["name"])}')
                        actual = cur.fetchone()[0]
                        checks.append(dict(check=entry['name']+'.'+name+'.sum', actual=actual, expected=expected, passed=actual == expected))
            queries = {
                'pit_date_violations': f'SELECT COUNT(*) FROM {db}.g_stock_daily_analysis WHERE dscl_dt >= trd_dt',
                'revenue_growth_mismatches': f"SELECT COUNT(*) FROM {db}.g_fin_rpt_analysis WHERE rev_yoy_rt_stts_cd='OK' AND NOT(rev_yoy_rt <=> ROUND(rev_ytd_amt / rev_prior_ytd_amt - 1, 8))",
            }
            for name, sql in queries.items():
                cur.execute(sql)
                actual = cur.fetchone()[0]
                checks.append(dict(check=name, actual=actual, expected=0, passed=actual == 0))
    finally:
        con.close()
    report = dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL', mysql_version=version,
                  database=catalog['database'], tables=json.loads((run/'mysql_validation.json').read_text())['tables'],
                  checks=checks, scope='new C Gold only; does not certify historical 58-table or Bronze replay')
    (run/'c_sql_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], checks=len(checks), report=str(run/'c_sql_validation.json'))))
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='root')
    parser.add_argument('--local-empty-password', action='store_true', help='Only for a disposable loopback validation server')
    args = parser.parse_args()
    if args.local_empty_password and args.host != '127.0.0.1':
        parser.error('Empty-password validation is restricted to loopback')
    password = '' if args.local_empty_password else getpass.getpass('MySQL password: ')
    raise SystemExit(verify(args.run.resolve(), args.host, args.port, args.user, password))
