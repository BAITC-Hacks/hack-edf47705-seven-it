from datetime import date

from django.test import SimpleTestCase

from forecast.csv_import import CsvImportError, parse_csv


class ParseCsvTests(SimpleTestCase):
    def test_parses_english_headers_and_iso_dates(self):
        data = b'date,category,quantity\n2026-01-05,Tires,4\n2026-01-06,Oil,2.5\n'
        self.assertEqual(
            parse_csv(data).rows,
            [(date(2026, 1, 5), 'Tires', 4.0), (date(2026, 1, 6), 'Oil', 2.5)],
        )

    def test_parses_russian_excel_export(self):
        data = 'Дата;Категория;Количество\n05.01.2026;Шины;1 200,5\n'.encode('cp1251')
        self.assertEqual(parse_csv(data).rows, [(date(2026, 1, 5), 'Шины', 1200.5)])

    def test_accepts_utf8_bom(self):
        data = '﻿дата,товар,продажи\n2026-02-01,Аккумуляторы,3\n'.encode('utf-8')
        self.assertEqual(parse_csv(data).rows, [(date(2026, 2, 1), 'Аккумуляторы', 3.0)])

    def test_missing_column_is_an_error(self):
        with self.assertRaisesMessage(CsvImportError, 'количество'):
            parse_csv(b'date,category\n2026-01-01,A\n')

    def test_bad_rows_are_skipped_and_reported(self):
        data = b'date,category,quantity\n' + b''.join(
            f'2026-01-{d:02d},A,1\n'.encode() for d in range(1, 11)
        ) + b'not-a-date,A,1\n2026-01-12,,1\n'
        result = parse_csv(data)
        self.assertEqual(len(result.rows), 10)
        self.assertEqual(len(result.skipped), 2)
        self.assertIn('строка 12', result.skipped[0])

    def test_mostly_broken_file_is_rejected(self):
        with self.assertRaisesMessage(CsvImportError, 'Слишком много'):
            parse_csv(b'date,category,quantity\nx,A,1\ny,A,1\n2026-01-01,A,1\n')

    def test_empty_file_is_rejected(self):
        with self.assertRaises(CsvImportError):
            parse_csv(b'date,category,quantity\n')
