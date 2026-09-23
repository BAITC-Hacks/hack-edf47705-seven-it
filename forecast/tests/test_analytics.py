from datetime import date

from django.test import SimpleTestCase

from forecast.analytics import analyze_category, analyze_records, monthly_totals


def month_seq(start_year, start_month, count):
    y, m = start_year, start_month
    for _ in range(count):
        yield (y, m)
        m += 1
        if m == 13:
            y, m = y + 1, 1


WINTER_SEASON = {1: 1.4, 2: 1.2, 3: 0.9, 4: 0.8, 5: 0.7, 6: 0.6, 7: 0.6, 8: 0.7, 9: 0.9, 10: 1.3, 11: 1.6, 12: 1.5}


def seasonal_series(start_level, monthly_growth, season=None, months=24):
    series = []
    level = start_level
    for ym in month_seq(2024, 9, months):
        factor = season[ym[1]] if season else 1.0
        series.append((ym, level * factor))
        level *= 1 + monthly_growth
    return series  # 2024-09 .. 2026-08


class MonthlyTotalsTests(SimpleTestCase):
    def test_sums_by_month_and_fills_gaps_with_zero(self):
        records = [
            (date(2026, 1, 5), 'A', 2),
            (date(2026, 1, 20), 'A', 3),
            (date(2026, 3, 31), 'A', 4),
            (date(2026, 3, 31), 'B', 1),
        ]
        totals, as_of = monthly_totals(records)
        self.assertEqual(totals['A'], [((2026, 1), 5), ((2026, 2), 0), ((2026, 3), 4)])
        self.assertEqual(totals['B'], [((2026, 1), 0), ((2026, 2), 0), ((2026, 3), 1)])
        self.assertEqual(as_of, date(2026, 3, 31))

    def test_drops_incomplete_last_month(self):
        records = [
            (date(2026, 1, 31), 'A', 1),
            (date(2026, 2, 28), 'A', 1),
            (date(2026, 3, 10), 'A', 100),
        ]
        totals, _ = monthly_totals(records)
        self.assertEqual([ym for ym, _ in totals['A']], [(2026, 1), (2026, 2)])


class AnalyzeCategoryTests(SimpleTestCase):
    def test_growing_seasonal_category(self):
        series = seasonal_series(100, 0.02, WINTER_SEASON)
        insight = analyze_category('Зимние шины', series, lead_time_weeks=3, as_of=date(2026, 8, 31))

        self.assertEqual(insight.direction, 'growing')
        self.assertGreater(insight.trend_pct, 10)
        self.assertEqual(insight.trend_basis, 'yoy')
        self.assertEqual([label for label, _ in insight.forecast], ['2026-09', '2026-10', '2026-11'])
        # Seasonal peak (November) is inside the 6-month horizon; order date is lead time before it.
        self.assertEqual(insight.peak_month, '2026-11')
        self.assertEqual(insight.order_by, date(2026, 10, 11))
        self.assertEqual(insight.confidence, 'high')
        # The forecast follows the season: October and November above September.
        values = [v for _, v in insight.forecast]
        self.assertGreater(values[2], values[0])

    def test_falling_category(self):
        series = seasonal_series(200, -0.03)
        insight = analyze_category('Летние шины', series, lead_time_weeks=2, as_of=date(2026, 8, 31))
        self.assertEqual(insight.direction, 'falling')
        self.assertLess(insight.trend_pct, -10)
        self.assertLess(insight.forecast_vs_last_year_pct, 0)

    def test_flat_category_is_stable_and_forecast_matches_level(self):
        series = seasonal_series(50, 0.0)
        insight = analyze_category('Масла', series, lead_time_weeks=2, as_of=date(2026, 8, 31))
        self.assertEqual(insight.direction, 'stable')
        self.assertIsNone(insight.peak_month)
        for _, value in insight.forecast:
            self.assertAlmostEqual(value, 50, delta=1)

    def test_short_history_has_low_confidence_and_no_yoy(self):
        series = seasonal_series(10, 0.1, months=5)
        insight = analyze_category('Новинка', series, lead_time_weeks=1, as_of=date(2025, 1, 31))
        self.assertEqual(insight.confidence, 'low')
        self.assertEqual(insight.trend_basis, 'recent')
        self.assertIsNone(insight.forecast_vs_last_year_pct)

    def test_forecast_is_never_negative(self):
        series = seasonal_series(100, -0.2)
        insight = analyze_category('Уходит', series, lead_time_weeks=1, as_of=date(2026, 8, 31))
        self.assertTrue(all(v >= 0 for _, v in insight.forecast))

    def test_all_zero_category_does_not_crash(self):
        series = [(ym, 0.0) for ym in month_seq(2025, 1, 12)]
        insight = analyze_category('Пусто', series, lead_time_weeks=1, as_of=date(2025, 12, 31))
        self.assertEqual(insight.direction, 'stable')
        self.assertEqual(insight.forecast_total, 0)


class AnalyzeRecordsTests(SimpleTestCase):
    def test_returns_insights_sorted_by_strength_of_change(self):
        records = []
        for (y, m), v in seasonal_series(100, 0.03):
            records.append((date(y, m, 28), 'Растёт', v))
        for (y, m), v in seasonal_series(100, 0.0):
            records.append((date(y, m, 28), 'Стабильно', v))
        report = analyze_records(records, lead_time_weeks=2)
        self.assertEqual([i.category for i in report.insights], ['Растёт', 'Стабильно'])
        self.assertEqual(report.as_of, date(2026, 8, 28))
