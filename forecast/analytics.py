"""Demand analytics: monthly aggregation, trend, seasonality and a short-term forecast.

Pure Python on purpose: the numbers here are the facts that the AI layer is allowed to talk
about, so they must be deterministic and explainable (see README, "Как считается прогноз").
"""

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

FORECAST_MONTHS = 3
PEAK_HORIZON_MONTHS = 6
# A month counts as a seasonal peak when demand is this much above an average month.
PEAK_THRESHOLD = 1.2
# Trend of +-10% or more is reported as growth / decline.
DIRECTION_THRESHOLD_PCT = 10.0
# The last month in the file counts as complete if data reaches its final week.
COMPLETE_MONTH_TAIL_DAYS = 7

Month = tuple[int, int]


@dataclass
class CategoryInsight:
    category: str
    months_of_data: int
    history: list[tuple[str, float]]
    forecast: list[tuple[str, float]]
    trend_pct: float | None
    trend_basis: str  # 'yoy' (vs same months last year), 'recent' (vs previous months), 'none'
    direction: str  # 'growing', 'falling', 'stable'
    forecast_total: float
    last_year_same_total: float | None
    forecast_vs_last_year_pct: float | None
    peak_month: str | None
    peak_index: float | None
    order_by: date | None
    confidence: str  # 'high', 'medium', 'low'

    def to_dict(self):
        return {
            'category': self.category,
            'months_of_data': self.months_of_data,
            'trend_pct': self.trend_pct,
            'trend_basis': self.trend_basis,
            'direction': self.direction,
            'forecast': [{'month': m, 'value': v} for m, v in self.forecast],
            'forecast_total': self.forecast_total,
            'last_year_same_total': self.last_year_same_total,
            'forecast_vs_last_year_pct': self.forecast_vs_last_year_pct,
            'peak_month': self.peak_month,
            'peak_vs_average_month': self.peak_index,
            'order_by': self.order_by.isoformat() if self.order_by else None,
            'confidence': self.confidence,
        }


@dataclass
class Report:
    as_of: date | None
    insights: list[CategoryInsight] = field(default_factory=list)

    @property
    def growing(self):
        return [i for i in self.insights if i.direction == 'growing']

    @property
    def falling(self):
        return [i for i in self.insights if i.direction == 'falling']

    @property
    def upcoming_deadlines(self):
        with_dates = [i for i in self.insights if i.order_by]
        return sorted(with_dates, key=lambda i: i.order_by)


def month_label(ym: Month) -> str:
    return f'{ym[0]:04d}-{ym[1]:02d}'


def add_months(ym: Month, n: int) -> Month:
    index = ym[0] * 12 + (ym[1] - 1) + n
    return (index // 12, index % 12 + 1)


def _month_range(first: Month, last: Month) -> list[Month]:
    months = []
    ym = first
    while ym <= last:
        months.append(ym)
        ym = add_months(ym, 1)
    return months


def monthly_totals(records):
    """Sum (date, category, quantity) records per category and calendar month.

    All categories share one month axis; months without sales are 0. A trailing month that the
    data covers only partially is dropped so it does not look like a sudden fall in demand.
    Returns ({category: [(month, total), ...]}, date of the last record).
    """
    sums = defaultdict(float)
    categories = set()
    first = last = None
    as_of = None
    for day, category, quantity in records:
        ym = (day.year, day.month)
        sums[(category, ym)] += quantity
        categories.add(category)
        first = ym if first is None or ym < first else first
        last = ym if last is None or ym > last else last
        as_of = day if as_of is None or day > as_of else as_of

    if as_of is None:
        return {}, None

    days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]
    if as_of.day <= days_in_month - COMPLETE_MONTH_TAIL_DAYS and last > first:
        last = add_months(last, -1)

    months = _month_range(first, last)
    totals = {c: [(ym, sums.get((c, ym), 0.0)) for ym in months] for c in sorted(categories)}
    return totals, as_of


def _linear_fit(ys):
    """Least squares y = a + b*x over x = 0..n-1."""
    n = len(ys)
    if n == 1:
        return ys[0], 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in range(n))
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(ys))
    b = sxy / sxx
    return mean_y - b * mean_x, b


def _seasonal_indices(series):
    """Average ratio of each calendar month to the fitted trend, normalised to a mean of 1."""
    values = [v for _, v in series]
    if len(values) < 12:
        return {m: 1.0 for m in range(1, 13)}
    a, b = _linear_fit(values)
    floor = max(sum(values) / len(values) * 0.05, 1e-9)
    ratios = defaultdict(list)
    for x, (ym, v) in enumerate(series):
        ratios[ym[1]].append(v / max(a + b * x, floor))
    indices = {m: sum(r) / len(r) for m, r in ratios.items()}
    mean = sum(indices.values()) / len(indices)
    if mean <= 0:
        return {m: 1.0 for m in range(1, 13)}
    return {m: indices.get(m, mean) / mean for m in range(1, 13)}


def _pct_change(new, old):
    if old <= 0:
        return None
    return round((new - old) / old * 100, 1)


def _trend(series, season):
    values = [v for _, v in series]
    n = len(values)
    if n >= 15:
        return _pct_change(sum(values[-3:]), sum(values[-15:-12])), 'yoy'
    deseasonalized = [v / season[ym[1]] for ym, v in series]
    window = 3 if n >= 6 else 2 if n >= 4 else 0
    if not window:
        return None, 'none'
    return _pct_change(sum(deseasonalized[-window:]), sum(deseasonalized[-2 * window:-window])), 'recent'


def _confidence(series, season):
    values = [v for _, v in series]
    n = len(values)
    if n < 12:
        return 'low'
    mean = sum(values) / n
    if mean <= 0:
        return 'low'
    a, b = _linear_fit(values)
    errors = [abs(v - (a + b * x) * season[ym[1]]) for x, (ym, v) in enumerate(series)]
    relative_error = sum(errors[-12:]) / 12 / mean
    if n >= 24 and relative_error < 0.25:
        return 'high'
    return 'medium'


def analyze_category(category, series, lead_time_weeks, as_of):
    """Turn one category's monthly series into trend, forecast and preparation deadline."""
    n = len(series)
    season = _seasonal_indices(series)
    trend_pct, trend_basis = _trend(series, season)

    # Forecast: extrapolate the de-seasonalised level of the last year, then re-apply seasonality.
    recent = series[-12:]
    deseasonalized = [v / season[ym[1]] for ym, v in recent]
    a, b = _linear_fit(deseasonalized)
    anchor = sum(deseasonalized[-3:]) / len(deseasonalized[-3:])
    last_month = series[-1][0]
    forecast = []
    for k in range(1, FORECAST_MONTHS + 1):
        ym = add_months(last_month, k)
        level = a + b * (len(recent) - 1 + k)
        level = min(max(level, anchor * 0.5), anchor * 1.5)  # guard against wild extrapolation
        forecast.append((month_label(ym), round(max(level, 0.0) * season[ym[1]], 1)))
    forecast_total = round(sum(v for _, v in forecast), 1)

    last_year_same_total = None
    forecast_vs_last_year_pct = None
    if n >= 12:
        last_year_same_total = round(sum(v for _, v in series[n - 12:n - 12 + FORECAST_MONTHS]), 1)
        forecast_vs_last_year_pct = _pct_change(forecast_total, last_year_same_total)

    peak_month = peak_index = order_by = None
    if n >= 12:
        upcoming = [add_months(last_month, k) for k in range(1, PEAK_HORIZON_MONTHS + 1)]
        peak = max(upcoming, key=lambda ym: season[ym[1]])
        if season[peak[1]] >= PEAK_THRESHOLD:
            peak_month = month_label(peak)
            peak_index = round(season[peak[1]], 2)
            order_by = date(peak[0], peak[1], 1) - timedelta(weeks=lead_time_weeks)

    if trend_pct is not None and trend_pct >= DIRECTION_THRESHOLD_PCT:
        direction = 'growing'
    elif trend_pct is not None and trend_pct <= -DIRECTION_THRESHOLD_PCT:
        direction = 'falling'
    else:
        direction = 'stable'

    return CategoryInsight(
        category=category,
        months_of_data=n,
        history=[(month_label(ym), round(v, 1)) for ym, v in series],
        forecast=forecast,
        trend_pct=trend_pct,
        trend_basis=trend_basis,
        direction=direction,
        forecast_total=forecast_total,
        last_year_same_total=last_year_same_total,
        forecast_vs_last_year_pct=forecast_vs_last_year_pct,
        peak_month=peak_month,
        peak_index=peak_index,
        order_by=order_by,
        confidence=_confidence(series, season),
    )


def analyze_records(records, lead_time_weeks):
    """Full report for (date, category, quantity) records, strongest changes first."""
    totals, as_of = monthly_totals(records)
    insights = [analyze_category(c, s, lead_time_weeks, as_of) for c, s in totals.items()]
    insights.sort(key=lambda i: abs(i.trend_pct or 0), reverse=True)
    return Report(as_of=as_of, insights=insights)
