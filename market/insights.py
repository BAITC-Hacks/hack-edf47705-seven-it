"""Transparent estimates from seller-entered history, never invented market data."""
from datetime import timedelta
from decimal import Decimal
from math import ceil

from django.utils import timezone


def product_insights(product, today=None):
    today = today or timezone.localdate()
    observations = sorted([row for row in product.observations.all() if row.date <= today], key=lambda row: row.date)
    recent = [row for row in observations if today - timedelta(days=29) <= row.date]
    previous = [row for row in observations if today - timedelta(days=59) <= row.date < today - timedelta(days=29)]
    last = observations[-1] if observations else None
    stale = last is None or (today - last.date).days > 14
    average = sum(row.sold for row in recent) / len(recent) if recent else 0
    old_average = sum(row.sold for row in previous) / len(previous) if previous else 0
    trend = None
    if len(recent) >= 7 and len(previous) >= 7 and old_average > 0 and not stale:
        trend = round((average / old_average - 1) * 100, 1)
    demand = 'Недостаточно данных'
    tone = 'neutral'
    if trend is not None:
        demand, tone = ('Спрос растёт', 'good') if trend >= 10 else ('Спрос снижается', 'bad') if trend <= -10 else ('Спрос стабилен', 'neutral')
    days_left = ceil(product.stock / average) if product.stock is not None and average > 0 and len(recent) >= 7 and not stale else None
    forecast = price_change = None
    price_rows = [row for row in observations if row.date >= today - timedelta(days=179)]
    if product.price is not None and len(price_rows) >= 6 and (price_rows[-1].date - price_rows[0].date).days >= 30 and not stale:
        xs = [(row.date - price_rows[0].date).days for row in price_rows]
        ys = [float(row.price) for row in price_rows]
        mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
        variance = sum((x - mean_x) ** 2 for x in xs)
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / variance
        delta = max(-float(product.price) * .3, min(float(product.price) * .3, slope * 30))
        forecast = (product.price + Decimal(str(delta))).quantize(Decimal('.01'))
        price_change = round(float((forecast / product.price - 1) * 100), 1)
    reviews = [review for review in product.reviews.all() if not review.is_hidden]
    rating = round(sum(review.rating for review in reviews) / len(reviews), 1) if reviews else None
    return {
        'demand': demand, 'tone': tone, 'trend': trend, 'sold_30': sum(row.sold for row in recent),
        'observed_days': len(recent), 'daily_sales': round(average, 1), 'days_left': days_left,
        'restock_soon': days_left is not None and days_left <= product.lead_days,
        'forecast_price': forecast, 'price_change': price_change, 'as_of': last.date if last else None,
        'stale': stale, 'review_count': len(reviews), 'rating': rating,
        'positive': sum(review.rating >= 4 for review in reviews),
        'negative': sum(review.rating <= 2 for review in reviews),
        'chart': {'dates': [row.date.isoformat() for row in observations[-90:]],
                  'prices': [float(row.price) for row in observations[-90:]],
                  'sales': [row.sold for row in observations[-90:]]},
    }
