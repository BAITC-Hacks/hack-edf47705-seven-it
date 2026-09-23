from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .demo_data import DEMO_BUSINESS, demo_csv, demo_rows
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


def index(request):
    form = UploadForm()
    return render(request, 'forecast/index.html', {
        'form': form,
        'datasets': Dataset.objects.select_related('business')[:8],
    })


@require_POST
def upload(request):
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'forecast/index.html', {
            'form': form,
            'datasets': Dataset.objects.select_related('business')[:8],
        }, status=400)

    business = form.save()
    parsed = form.parsed
    dataset = services.create_dataset(business, request.FILES['file'].name, parsed.rows)
    if parsed.skipped_count:
        messages.warning(
            request,
            f'Пропущено строк с ошибками: {parsed.skipped_count}. Например: ' + '; '.join(parsed.skipped[:3]),
        )
    return redirect('dashboard', dataset_id=dataset.id)


@require_POST
def demo(request):
    business = Business.objects.create(**DEMO_BUSINESS)
    dataset = services.create_dataset(business, 'Демо: продажи 2024–2026', demo_rows())
    return redirect('dashboard', dataset_id=dataset.id)


def sample_csv(request):
    response = HttpResponse(demo_csv(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="foresell-sample.csv"'
    return response


def dashboard(request, dataset_id):
    dataset = get_object_or_404(Dataset.objects.select_related('business'), pk=dataset_id)
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
    items = []
    for item in recs.get('items', []):
        icon, label = ACTION_LABELS.get(item['action'], ACTION_LABELS['hold'])
        items.append({
            **item,
            'icon': icon,
            'action_label': label,
            'confidence_label': CONFIDENCE_LABELS.get(item['confidence'], ''),
            'deadline_label': format_date(date.fromisoformat(item['deadline'])) if item.get('deadline') else '',
        })

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
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    services.refresh_recommendations(dataset, use_ai=True)
    if dataset.recommendations_source == Dataset.SOURCE_AI:
        messages.success(request, 'Рекомендации ИИ готовы.')
    else:
        messages.warning(request, dataset.recommendations_note)
    return redirect('dashboard', dataset_id=dataset.id)
