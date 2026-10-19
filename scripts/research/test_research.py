"""Small regression checks for units, absent values, and non-destructive DDL extraction."""
import re
import unittest

from collect import ROOT, number
from enrich_official import require_checked
from load_mysql import qi
from assess import classify, evaluate, LABELS, RAW_FIELDS, published
from decimal import Decimal
import json
from forecast_cleaned import calculate as calculate_cleaned, classify as classify_cleaned


class ResearchChecks(unittest.TestCase):
    def test_exact_numbers_and_missing(self):
        self.assertEqual(number('1,234,567원'), '1234567')
        self.assertEqual(number('(17,127,003)'), '-17127003')
        self.assertEqual(number('45.98%'), '45.98')
        self.assertEqual(number('0'), '0')
        for value in ['-', 'N/A', '', None, 'NaN', 'Infinity', '1조 8,158억']:
            self.assertIsNone(number(value))

    def test_ddl_preserves_semicolon_in_comment(self):
        folder = ROOT / 'data/03_C_integration_20261014/03_model/ddl'
        statements = []
        for filename in ['02_silver.sql', '03_gold.sql']:
            statements.extend(re.findall(r'CREATE TABLE `\w+` \(.*?;(?=\r?\n|$)',
                              (folder / filename).read_text(encoding='utf-8-sig'), flags=re.S))
        self.assertEqual(len(statements), 19)
        self.assertTrue(all(s.rstrip().endswith("';") for s in statements))
        self.assertTrue(all('DROP TABLE' not in s for s in statements))

    def test_sql_identifiers(self):
        self.assertEqual(qi('tz_teamzero_research_20261016'), '`tz_teamzero_research_20261016`')
        for name in ['tz; DROP DATABASE mysql', 'a.b', '', '`root`']:
            with self.assertRaises(ValueError):
                qi(name)

    def test_changed_curated_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Official source changed'):
            require_checked(b'changed source', '0' * 64)

    def test_forecast_requires_valuation_and_earnings(self):
        t = Decimal('1.5')
        self.assertEqual(classify(2, 2, -.1, 1, 2, t), 'STRONG')
        self.assertEqual(classify(2, 2, .1, 3, 2, t), 'WATCH')
        self.assertEqual(classify(1, 1, -.1, -1, 2, t), 'NOT_MET')
        self.assertEqual(classify(t, 1, .1, 3, 2, t), 'WATCH')
        with self.assertRaises(ValueError):
            classify(None, 2, .1, 3, 2, t)

    def test_published_results_have_no_provider_values(self):
        expected = json.loads((ROOT / 'docs/research/assessment-results.json').read_text())
        self.assertEqual(len(expected['rows']), 20)
        self.assertTrue(all(r['label'] in LABELS.values() for r in expected['rows']))
        self.assertFalse(any(f in r for r in expected['rows'] for f in RAW_FIELDS))

    def test_local_snapshot_reproduces_all_twenty_forecasts(self):
        # Collected inputs are not in the public repository; they exist only after a local collection run.
        path = ROOT / 'build/research/assessment-inputs.json'
        if not path.exists():
            self.skipTest('local collected inputs absent (build/research); run scripts/research/assess.py')
        inputs = json.loads(path.read_text())
        expected = json.loads((ROOT / 'docs/research/assessment-results.json').read_text())
        actual = published(dict(rows=json.loads(json.dumps(evaluate(inputs), default=str))))['rows']
        self.assertEqual(actual, expected['rows'])

    def test_cleaned_forecast_thresholds_and_invalid_flags(self):
        self.assertEqual(classify_cleaned([True]*4+[False]), '시장 대비 강세 예상')
        self.assertEqual(classify_cleaned([True]*3+[False]*2), '혼조 예상')
        self.assertEqual(classify_cleaned([True]+[False]*4), '시장 대비 약세 예상')
        with self.assertRaises(ValueError):
            classify_cleaned([True,True,None,False,False])

    def test_cleaned_forecast_reproduction_and_disclosure_boundary(self):
        expected=json.loads((ROOT/'docs/research/cleaned-data-forecast.json').read_text())
        actual=json.loads(json.dumps(calculate_cleaned(),default=str))
        self.assertEqual(actual,expected['rows'])
        self.assertEqual(len(actual),20)
        self.assertTrue(all(r['disclosure_date'] < r['as_of'] for r in actual))


if __name__ == '__main__':
    unittest.main()
