"""Load immutable GitHub handoff and new collection into a NEW MySQL schema.

No DROP, TRUNCATE, REPLACE or writes to an existing schema. Password is prompted.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'data/03_C_integration_20261014'


def qi(name):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
        raise ValueError('Invalid SQL identifier')
    return '`' + name + '`'


def digest(rows):
    hashes = sorted(hashlib.sha256(json.dumps(list(row), ensure_ascii=False, default=str,
                    separators=(',', ':')).encode()).digest() for row in rows)
    return hashlib.sha256(b''.join(hashes)).hexdigest()


def load(collection, schema, password, host='127.0.0.1', port=3306, user='root'):
    bundle = json.loads((collection / 'collection.json').read_text())
    if bundle['errors']:
        raise ValueError('Collection has unresolved errors')
    for source in bundle['sources']:
        body = (collection / source['raw_path']).read_bytes()
        if hashlib.sha256(body).hexdigest() != source['sha256']:
            raise ValueError('Raw source hash mismatch')
    qi(schema)
    con = pymysql.connect(host=host, port=port, user=user, password=password, charset='utf8mb4',
                          autocommit=False, connect_timeout=10, read_timeout=300, write_timeout=300)
    checks = []
    report_path = collection / 'mysql_validation.json'
    report = dict(status='STARTED', schema=schema, host=host, port=port,
                  tables=checks, existing_database_writes=False)
    try:
        with con.cursor() as cur:
            cur.execute('SELECT VERSION()'); report['server_version'] = cur.fetchone()[0]
            cur.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s', (schema,))
            schema_exists = bool(cur.fetchone())
            previous = json.loads(report_path.read_text()) if report_path.exists() else {}
            if schema_exists and not (previous.get('schema') == schema and previous.get('status') == 'FAIL'
                                      and previous.get('created_by_this_loader') is True):
                raise ValueError('Refusing pre-existing target schema not owned by this failed run')
            if schema_exists:
                cur.execute('SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s',
                            (schema, 'research_source'))
                if cur.fetchone()[0]:
                    raise ValueError('Research loading already started; preserve this schema and choose a new target')
            # Inventory is read-only; record the database the user was already using.
            cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='stock_analysis_2026' AND TABLE_TYPE='BASE TABLE'")
            existing = [row[0] for row in cur]
            before = {}
            for table in existing:
                cur.execute('SELECT * FROM stock_analysis_2026.' + qi(table))
                rows = cur.fetchall(); before[table] = dict(rows=len(rows), digest=digest(rows))
            report['existing_database_before'] = before
            if not schema_exists:
                cur.execute('CREATE DATABASE ' + qi(schema) + ' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin')
            report['created_by_this_loader'] = True
            cur.execute('USE ' + qi(schema))
            cur.execute("SET SESSION sql_mode='STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'")
            # Reuse only CREATE TABLE statements, never the pinned DDL's destructive prologue.
            for layer, filename in [('silver', '02_silver.sql'), ('gold', '03_gold.sql')]:
                ddl = (PACKAGE / '03_model/ddl' / filename).read_text(encoding='utf-8-sig')
                for statement in re.findall(r'CREATE TABLE `\w+` \(.*?;(?=\r?\n|$)', ddl, flags=re.S):
                    table = re.search(r'CREATE TABLE `(\w+)`', statement)[1]
                    csv_path = PACKAGE / '04_output' / layer / (table + '.csv')
                    cur.execute('SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s', (schema, table))
                    if not cur.fetchone()[0]:
                        cur.execute(statement)
                    with csv_path.open(encoding='utf-8-sig', newline='') as f:
                        reader = csv.DictReader(f); columns = reader.fieldnames
                        rows = [tuple(row[c] if row[c] != '' else None for c in columns) for row in reader]
                    sql = 'INSERT INTO ' + qi(table) + ' (' + ','.join(map(qi, columns)) + ') VALUES (' + ','.join(['%s'] * len(columns)) + ')'
                    cur.execute('SELECT COUNT(*) FROM ' + qi(table))
                    if not cur.fetchone()[0]:
                        for start in range(0, len(rows), 1000):
                            cur.executemany(sql, rows[start:start + 1000])
                    con.commit()
                    # Compare all source values using MySQL's declared type conversions.
                    cur.execute('SELECT ' + ','.join(map(qi, columns)) + ' FROM ' + qi(table))
                    actual = cur.fetchall()
                    cur.execute('SHOW COLUMNS FROM ' + qi(table))
                    types = {r[0]: r[1] for r in cur}
                    def normalize(row):
                        from decimal import Decimal
                        values = []
                        for col, value in zip(columns, row):
                            if value is None:
                                values.append(None)
                            elif any(types[col].startswith(t) for t in ['decimal', 'bigint', 'int', 'smallint', 'tinyint']):
                                values.append(format(Decimal(str(value)).normalize(), 'f'))
                            else:
                                values.append(str(value))
                        return values
                    expected_hash = digest(normalize(row) for row in rows)
                    actual_hash = digest(normalize(row) for row in actual)
                    if len(rows) != len(actual) or expected_hash != actual_hash:
                        raise ValueError('Full reconciliation failed: ' + table)
                    checks.append(dict(table=table, rows=len(actual), status='PASS', sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(), values_digest=actual_hash))
                    print('PASS', table, len(actual), flush=True)

            cur.execute('CREATE TABLE research_source (source_id VARCHAR(100) PRIMARY KEY, stock_cd CHAR(6), kind VARCHAR(100), url TEXT, retrieved_at VARCHAR(40), sha256 CHAR(64), raw_path TEXT, content_type VARCHAR(200), bytes BIGINT, raw_body LONGBLOB)')
            for source in bundle['sources']:
                columns = list(source) + ['raw_body']
                cur.execute('INSERT INTO research_source (' + ','.join(map(qi, columns)) + ') VALUES (' + ','.join(['%s'] * len(columns)) + ')',
                            tuple(source.values()) + ((collection / source['raw_path']).read_bytes(),))
            con.commit()
            cur.execute('SELECT source_id,sha256,raw_body FROM research_source')
            for sid, expected, body in cur:
                if hashlib.sha256(body).hexdigest() != expected:
                    raise ValueError('Stored raw hash mismatch: ' + sid)
            checks.append(dict(table='research_source', rows=len(bundle['sources']), status='PASS'))

            numeric = {'value': 'DECIMAL(38,10)', 'close_prc': 'DECIMAL(20,0)',
                       'frgn_net_buy_qty': 'BIGINT', 'inst_net_buy_qty': 'BIGINT',
                       'indv_net_buy_qty': 'BIGINT', 'frgn_hold_rt': 'DECIMAL(18,8)'}
            for kind, items in bundle['tables'].items():
                if not items:
                    raise ValueError('Empty required dataset: ' + kind)
                table = 'research_' + kind
                columns = list(items[0])
                def sql_type(col):
                    if col in numeric:
                        return numeric[col]
                    if col == 'stock_cd':
                        return 'CHAR(6)'
                    if col == 'trd_dt':
                        return 'DATE'
                    if col == 'source_id':
                        return 'VARCHAR(100)'
                    return 'LONGTEXT'
                cur.execute('CREATE TABLE ' + qi(table) + ' (id BIGINT PRIMARY KEY AUTO_INCREMENT,' +
                            ','.join(qi(c) + ' ' + sql_type(c) for c in columns) +
                            ',FOREIGN KEY (source_id) REFERENCES research_source(source_id))')
                sql = 'INSERT INTO ' + qi(table) + ' (' + ','.join(map(qi, columns)) + ') VALUES (' + ','.join(['%s'] * len(columns)) + ')'
                cur.executemany(sql, [tuple(row[c] for c in columns) for row in items])
                con.commit()
                cur.execute('SELECT COUNT(*) FROM ' + qi(table))
                if cur.fetchone()[0] != len(items):
                    raise ValueError('Count mismatch ' + table)
                cur.execute('SELECT ' + ','.join(map(qi, columns)) + ' FROM ' + qi(table))
                actual = cur.fetchall()
                def canonical(row):
                    from decimal import Decimal
                    return [format(Decimal(str(v)).normalize(), 'f') if c in numeric and v is not None
                            else str(v) if v is not None else None for c, v in zip(columns, row)]
                expected_hash = digest(canonical([r[c] for c in columns]) for r in items)
                actual_hash = digest(canonical(r) for r in actual)
                if expected_hash != actual_hash:
                    raise ValueError('Full reconciliation failed ' + table)
                checks.append(dict(table=table, rows=len(items), status='PASS', values_digest=actual_hash))
                print('PASS', table, len(items), flush=True)
            cur.execute("CREATE VIEW v_research_price_flow AS SELECT stock_cd,trd_dt,close_prc,frgn_net_buy_qty,inst_net_buy_qty,frgn_hold_rt,fin_rpt_id,dscl_dt FROM g_ai_stock_daily")
            cur.execute("CREATE VIEW v_research_cash_inventory_capex AS SELECT r.fin_rpt_id,r.corp_cd,r.bsns_yr,r.rpt_cd,r.fs_div_cd,r.pit_join_elig_yn,r.cf_prd_stts_cd,m.mtrc_cd,m.prd_type_cd,m.mtrc_amt FROM s_fin_rpt r JOIN s_fin_mtrc m ON r.fin_rpt_id=m.fin_rpt_id WHERE m.mtrc_cd IN ('OPERATING_CASH_FLOW','INVENTORIES','PPE_PURCHASE_REPORTED','INTANGIBLE_PURCHASE_REPORTED','OPERATING_PROFIT','NET_INCOME')")
            cur.execute("CREATE VIEW v_research_valuation_comparison AS SELECT v.stock_cd,s.stock_nm,v.metric,v.value,v.unit,v.reference_period,v.observed_at,v.historical_pit_eligible,v.source_id FROM research_valuation v LEFT JOIN s_stock s ON v.stock_cd=s.stock_cd")
            cur.execute("CREATE TABLE research_manifest (manifest_key VARCHAR(100) PRIMARY KEY, manifest_json JSON NOT NULL)")
            cur.execute('INSERT INTO research_manifest VALUES (%s,%s)', ('collection', json.dumps({k: v for k, v in bundle.items() if k != 'tables'}, ensure_ascii=False)))
            con.commit()
            after = {}
            for table in existing:
                cur.execute('SELECT * FROM stock_analysis_2026.' + qi(table))
                rows = cur.fetchall(); after[table] = dict(rows=len(rows), digest=digest(rows))
            if before != after:
                raise ValueError('Existing DB changed during run; inspect concurrent writers')
            report['existing_database_unchanged'] = True
            report['status'] = 'PASS'
            report['completed_at'] = dt.datetime.now().astimezone().isoformat()
            cur.execute('INSERT INTO research_manifest VALUES (%s,%s)', ('mysql_validation', json.dumps(report, ensure_ascii=False)))
            con.commit()
    except BaseException as exc:
        con.rollback(); report['status'] = 'FAIL'; report['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        if report.get('created_by_this_loader'):
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        con.close()
    print('SUCCESS:', schema, 'all source values matched; existing database unchanged')


if __name__ == '__main__':
    import getpass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--schema', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='root')
    args = parser.parse_args()
    load(args.collection.resolve(), args.schema, getpass.getpass('MySQL password: '), args.host, args.port, args.user)
