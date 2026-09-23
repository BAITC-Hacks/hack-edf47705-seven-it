"""Rule-based recommendations. Used on their own when Claude is unavailable and as the baseline."""

from datetime import date, timedelta

from .analytics import DIRECTION_THRESHOLD_PCT

MONTHS_IN = {
    1: 'январе', 2: 'феврале', 3: 'марте', 4: 'апреле', 5: 'мае', 6: 'июне',
    7: 'июле', 8: 'августе', 9: 'сентябре', 10: 'октябре', 11: 'ноябре', 12: 'декабре',
}
# How far ahead a preparation deadline is worth mentioning.
DEADLINE_HORIZON = timedelta(weeks=12)


def month_in(label: str) -> str:
    """'2026-11' -> 'ноябре 2026'."""
    year, month = label.split('-')
    return f'{MONTHS_IN[int(month)]} {year}'


def format_date(value: date) -> str:
    return value.strftime('%d.%m.%Y')


def _signed(pct: float) -> str:
    return f'{pct:+.0f}%'.replace('-', '−')


def _change_pct(insight):
    """The best available measure of change: forecast vs last year, else the recent trend."""
    if insight.forecast_vs_last_year_pct is not None:
        return insight.forecast_vs_last_year_pct, 'прогноз на 3 месяца против тех же месяцев прошлого года'
    if insight.trend_pct is not None:
        return insight.trend_pct, 'последние месяцы против предыдущих'
    return None, ''


def rule_recommendations(report, business):
    retail = business.business_type == 'retail'
    stock, extra = ('закупку', 'запас') if retail else ('число смен', 'дополнительные смены')
    items = []

    for insight in report.insights:
        change, change_basis = _change_pct(insight)
        deadline = insight.order_by
        near_peak = deadline is not None and deadline - report.as_of <= DEADLINE_HORIZON

        if near_peak:
            overdue = deadline < report.as_of
            action_text = 'закажите товар' if retail else 'составьте график с дополнительными сменами'
            reason = (
                f'В {month_in(insight.peak_month)} спрос обычно в {insight.peak_index:.1f} раза выше '
                f'среднего месяца. Срок подготовки — {business.lead_time_weeks} нед., '
                f'поэтому {action_text} до {format_date(deadline)}.'
            )
            if overdue:
                reason += ' Этот срок уже прошёл — действовать нужно срочно.'
            if change is not None and abs(change) >= DIRECTION_THRESHOLD_PCT:
                reason += f' Общий спрос тоже меняется: {_signed(change)} ({change_basis}).'
            items.append({
                'category': insight.category,
                'action': 'prepare_peak',
                'title': f'{insight.category}: подготовьте {extra} к пику в {month_in(insight.peak_month)}',
                'reason': reason,
                'deadline': deadline.isoformat(),
                'confidence': insight.confidence,
            })
        elif insight.direction == 'growing' and change is not None and change >= DIRECTION_THRESHOLD_PCT:
            items.append({
                'category': insight.category,
                'action': 'increase',
                'title': f'{insight.category}: увеличьте {stock} примерно на {change:.0f}%',
                'reason': f'Спрос растёт: {_signed(change)} ({change_basis}). '
                          f'Ожидается около {insight.forecast_total:.0f} ед. за 3 месяца.',
                'deadline': None,
                'confidence': insight.confidence,
            })
        elif insight.direction == 'falling' and change is not None and change <= -DIRECTION_THRESHOLD_PCT:
            items.append({
                'category': insight.category,
                'action': 'decrease',
                'title': f'{insight.category}: сократите {stock} примерно на {abs(change):.0f}%',
                'reason': f'Спрос падает: {_signed(change)} ({change_basis}). '
                          f'Ожидается около {insight.forecast_total:.0f} ед. за 3 месяца.',
                'deadline': None,
                'confidence': insight.confidence,
            })

    items.sort(key=lambda r: (r['deadline'] is None, r['deadline'] or ''))
    growing, falling = len(report.growing), len(report.falling)
    summary = (
        f'Проанализировано категорий: {len(report.insights)}. '
        f'Спрос растёт в {growing}, падает в {falling}. '
        + (f'Ближайший срок подготовки — {format_date(date.fromisoformat(items[0]["deadline"]))} '
           f'({items[0]["category"]}).' if items and items[0]['deadline'] else '')
    ).strip()
    return {'summary': summary, 'items': items}
