"""Deterministic demo history: an auto parts store in Almaty, daily sales for ~2.7 years."""

import random
from datetime import date, timedelta

DEMO_BUSINESS = {
    'name': 'Автозапчасти «Жолда»',
    'business_type': 'retail',
    'region': 'Алматы',
    'lead_time_weeks': 3,
}
DEMO_START = date(2024, 1, 1)
DEMO_END = date(2026, 8, 31)

FLAT = {m: 1.0 for m in range(1, 13)}
# category: (units per average month at the start, yearly growth, seasonality by month)
CATEGORIES = {
    'Зимние шины': (120, 0.30, {1: 0.5, 2: 0.3, 3: 0.2, 4: 0.1, 5: 0.1, 6: 0.1,
                                7: 0.2, 8: 0.5, 9: 1.4, 10: 3.2, 11: 3.6, 12: 1.9}),
    'Летние шины': (140, -0.22, {1: 0.2, 2: 0.4, 3: 2.4, 4: 3.4, 5: 2.2, 6: 1.2,
                                 7: 0.8, 8: 0.6, 9: 0.3, 10: 0.2, 11: 0.1, 12: 0.2}),
    'Аккумуляторы': (90, 0.03, {1: 1.6, 2: 1.3, 3: 0.9, 4: 0.7, 5: 0.7, 6: 0.8,
                                7: 0.9, 8: 0.8, 9: 0.9, 10: 1.1, 11: 1.4, 12: 1.9}),
    'Антифриз и незамерзайка': (200, 0.05, {1: 1.7, 2: 1.4, 3: 0.8, 4: 0.5, 5: 0.4, 6: 0.4,
                                            7: 0.4, 8: 0.5, 9: 0.9, 10: 1.6, 11: 2.0, 12: 1.4}),
    'Моторное масло': (300, 0.06, FLAT),
    'Фреон для кондиционера': (40, 0.35, {1: 0.1, 2: 0.1, 3: 0.3, 4: 0.8, 5: 1.8, 6: 2.8,
                                          7: 3.0, 8: 2.0, 9: 0.6, 10: 0.2, 11: 0.1, 12: 0.1}),
    'Щётки стеклоочистителя': (110, 0.0, {1: 0.8, 2: 0.9, 3: 1.4, 4: 1.3, 5: 0.9, 6: 0.7,
                                          7: 0.6, 8: 0.7, 9: 1.1, 10: 1.6, 11: 1.3, 12: 0.7}),
    'Видеорегистраторы': (60, -0.15, FLAT),
}


def demo_rows(seed=7):
    """Daily (date, category, quantity) rows; the same seed always gives the same data."""
    rng = random.Random(seed)
    rows = []
    day = DEMO_START
    while day <= DEMO_END:
        years = (day - DEMO_START).days / 365.25
        for category, (base, growth, season) in CATEGORIES.items():
            expected = base * (1 + growth) ** years * season[day.month] / 30.4 * rng.uniform(0.7, 1.3)
            quantity = int(expected + rng.random())  # unbiased rounding to whole units
            if quantity:
                rows.append((day, category, float(quantity)))
        day += timedelta(days=1)
    return rows


def demo_csv():
    lines = ['date,category,quantity']
    lines += [f'{d.isoformat()},{c},{q:.0f}' for d, c, q in demo_rows()]
    return '\n'.join(lines) + '\n'
