"""Permission-aware, read-only data for the admin overview."""

from datetime import timedelta

from django import template
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from forecast.models import Business, Dataset, Record

register = template.Library()


@register.simple_tag(takes_context=True)
def workspace_summary(context):
    request = context['request']
    summary = {'metrics': [], 'datasets': [], 'chart': [], 'can_view_datasets': False}
    for model, label, note, icon in (
        (Business, 'Бизнес-профили', 'Компании в системе', 'business'),
        (Dataset, 'Наборы данных', 'История для прогнозов', 'dataset'),
        (Record, 'Записи', 'Продажи и бронирования', 'record'),
        (get_user_model(), 'Пользователи', 'Учётные записи', 'users'),
    ):
        model_admin = admin.site._registry.get(model)
        if not model_admin or not model_admin.has_view_or_change_permission(request):
            continue
        queryset = model_admin.get_queryset(request)
        summary['metrics'].append({
            'label': label, 'note': note, 'icon': icon, 'count': queryset.count(),
            'url': reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist'),
        })
        if model is Dataset:
            summary['can_view_datasets'] = True
            summary['datasets'] = list(queryset.select_related('business').order_by('-created_at', '-pk')[:5])
            today = timezone.localdate()
            start = today - timedelta(days=6)
            counts = dict(queryset.filter(created_at__date__gte=start, created_at__date__lte=today)
                          .order_by().annotate(day=TruncDate('created_at')).values('day')
                          .annotate(total=Count('pk', distinct=True)).values_list('day', 'total'))
            maximum = max(counts.values(), default=1) or 1
            summary['chart_total'] = sum(counts.values())
            for offset in range(7):
                day = start + timedelta(days=offset)
                count = counts.get(day, 0)
                summary['chart'].append({'day': day, 'count': count, 'height': round(count / maximum * 100)})
    return summary
