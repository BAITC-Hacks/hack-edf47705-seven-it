from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .demo_data import demo_csv
from .forms import UploadForm
from .models import Business, Dataset
from .recommendations import format_date, month_in

DIRECTION_LABELS = {'growing': 'Растёт', 'falling': 'Падает', 'stable': 'Стабильно'}
CONFIDENCE_LABELS = {'high': 'высокая', 'medium': 'средняя', 'low': 'низкая'}
ACTION_LABELS = {
    'increase': ('up', 'Увеличить'),
    'decrease': ('down', 'Сократить'),
    'prepare_peak': ('clock', 'Подготовиться к пику'),
    'hold': ('pause', 'Держать уровень'),
}


def accessible_datasets(request):
    query = Dataset.objects.select_related('business')
    if request.user.is_authenticated and request.user.is_staff:
        return query
    permitted = Q(is_demo=True) | Q(pk__in=request.session.get('forecast_datasets', []), business__owner__isnull=True)
    if request.user.is_authenticated:
        permitted |= Q(business__owner=request.user)
    return query.filter(permitted)


SHORT_MONTHS = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']


def format_items(recommendations):
    """Stored recommendation dicts plus the labels the action cards display."""
    items = []
    for item in recommendations.get('items', []):
        icon, label = ACTION_LABELS.get(item['action'], ACTION_LABELS['hold'])
        items.append({
            **item,
            'icon': icon,
            'action_label': label,
            'confidence_label': CONFIDENCE_LABELS.get(item['confidence'], ''),
            'deadline_label': format_date(date.fromisoformat(item['deadline'])) if item.get('deadline') else '',
        })
    return items


def short_month(label):
    year, month = label.split('-')
    return f'{SHORT_MONTHS[int(month) - 1]} {year}'


def sparkline(insight, width=640, height=160, pad=6):
    """SVG polyline points for the last 24 months of history and the forecast after it."""
    history = insight.history[-24:]
    values = [v for _, v in history] + [v for _, v in insight.forecast]
    top = max(values) or 1
    step = (width - 2 * pad) / (len(values) - 1)

    def point(i, value):
        return f'{pad + i * step:.1f},{height - pad - value / top * (height - 2 * pad):.1f}'

    last = len(history) - 1
    forecast = [history[-1][1]] + [v for _, v in insight.forecast]  # starts at the last actual point
    split_x = pad + last * step
    return {
        'width': width,
        'height': height,
        'fact': ' '.join(point(i, v) for i, (_, v) in enumerate(history)),
        'forecast': ' '.join(point(last + i, v) for i, v in enumerate(forecast)),
        'split_x': f'{split_x:.1f}',
        'future_width': f'{width - split_x:.1f}',
        'split_pct': f'{split_x / width * 100:.1f}',
        'start_label': short_month(history[0][0]),
        'end_label': short_month(insight.forecast[-1][0]),
    }


def example_forecast():
    """A ready-made forecast on the demo data, shown on the start page for presentations."""
    dataset = services.get_demo_dataset()
    report = services.load_report(dataset)
    if not report.insights:
        return None
    items = format_items(dataset.recommendations or {})
    insights = {i.category: i for i in report.insights}
    # Feature the category with the most visible seasonal peak among those with a deadline.
    featured = max(
        (insights[i['category']] for i in items if i['action'] == 'prepare_peak' and i['category'] in insights),
        key=lambda insight: insight.peak_index or 0,
        default=report.insights[0],
    )
    next_deadline = next((i for i in report.upcoming_deadlines if i.order_by >= report.as_of), None)
    # For the slide show one decision of each kind: the featured peak, a cut and a raise.
    showcase = []
    for wanted in (
        lambda i: i['category'] == featured.category,
        lambda i: i['action'] == 'decrease',
        lambda i: i['action'] == 'increase',
        lambda i: True,
    ):
        for item in items:
            if len(showcase) < 3 and item not in showcase and wanted(item):
                showcase.append(item)
                break
    while len(showcase) < 3 and len(showcase) < len(items):
        showcase.append(next(i for i in items if i not in showcase))
    return {
        'dataset': dataset,
        'business': dataset.business,
        'report': report,
        'items': showcase,
        'featured': featured,
        'featured_peak': month_in(featured.peak_month) if featured.peak_month else '',
        'featured_order_by': format_date(featured.order_by) if featured.order_by else '',
        'chart': sparkline(featured),
        'next_deadline': next_deadline,
        'next_deadline_label': format_date(next_deadline.order_by) if next_deadline else '',
    }


def index(request):
    form = UploadForm()
    return render(request, 'forecast/index.html', {
        'form': form,
        'datasets': accessible_datasets(request)[:8],
        'example': example_forecast(),
    })


@require_POST
def upload(request):
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'forecast/index.html', {
            'form': form,
            'datasets': accessible_datasets(request)[:8],
        }, status=400)

    parsed = form.parsed
    with transaction.atomic():
        business = form.save(commit=False)
        if request.user.is_authenticated:
            business.owner = request.user
        business.save()
        dataset = services.create_dataset(business, request.FILES['file'].name, parsed.rows)
    request.session['forecast_datasets'] = (request.session.get('forecast_datasets', []) + [dataset.pk])[-50:]
    if parsed.skipped_count:
        messages.warning(
            request,
            f'Пропущено строк с ошибками: {parsed.skipped_count}. Например: ' + '; '.join(parsed.skipped[:3]),
        )
    return redirect('dashboard', dataset_id=dataset.id)


@require_POST
def demo(request):
    return redirect('dashboard', dataset_id=services.get_demo_dataset().id)


def sample_csv(request):
    response = HttpResponse(demo_csv(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="foresell-sample.csv"'
    return response


def dashboard(request, dataset_id):
    dataset = get_object_or_404(accessible_datasets(request), pk=dataset_id)
    report = services.load_report(dataset)

    rows = []
    for insight in report.insights:
        rows.append({
            'insight': insight,
            'direction_label': DIRECTION_LABELS[insight.direction],
            'confidence_label': CONFIDENCE_LABELS[insight.confidence],
            'peak_label': month_in(insight.peak_month) if insight.peak_month else '',
            'order_by_label': format_date(insight.order_by) if insight.order_by else '',
            'order_by_overdue': bool(insight.order_by and insight.order_by < report.as_of),
        })

    recs = dataset.recommendations or {}
    items = format_items(recs)

    chart_data = {
        insight.category: {
            'history': insight.history[-24:],
            'forecast': insight.forecast,
        }
        for insight in report.insights
    }
    next_deadline = next(
        (i for i in report.upcoming_deadlines if i.order_by >= report.as_of), None,
    )

    return render(request, 'forecast/dashboard.html', {
        'dataset': dataset,
        'business': dataset.business,
        'report': report,
        'rows': rows,
        'summary': recs.get('summary', ''),
        'items': items,
        'chart_data': chart_data,
        'next_deadline': next_deadline,
        'next_deadline_label': format_date(next_deadline.order_by) if next_deadline else '',
        'unit': 'шт.' if dataset.business.business_type == Business.TYPE_RETAIL else 'записей',
    })


@require_POST
def recommend(request, dataset_id):
    dataset = get_object_or_404(accessible_datasets(request), pk=dataset_id)
    services.refresh_recommendations(dataset, use_ai=True)
    if dataset.recommendations_source == Dataset.SOURCE_AI:
        messages.success(request, 'Рекомендации ИИ готовы.')
    else:
        messages.warning(request, dataset.recommendations_note)
    return redirect('dashboard', dataset_id=dataset.id)
