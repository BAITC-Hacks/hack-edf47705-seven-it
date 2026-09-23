"""Glue between the database and the analytics / recommendation modules."""

from django.db import transaction
from django.utils import timezone

from .ai import AiUnavailable, ai_recommendations
from .analytics import analyze_records
from .demo_data import DEMO_BUSINESS, DEMO_DATASET_NAME, demo_rows
from .models import Business, Dataset, Record
from .recommendations import rule_recommendations


def load_report(dataset):
    rows = dataset.records.order_by('date').values_list('date', 'category', 'quantity')
    return analyze_records(rows, dataset.business.lead_time_weeks)


@transaction.atomic
def create_dataset(business, name, rows):
    dataset = Dataset.objects.create(business=business, name=name)
    Record.objects.bulk_create(
        [Record(dataset=dataset, date=d, category=c, quantity=q) for d, c, q in rows],
        batch_size=2000,
    )
    refresh_recommendations(dataset, use_ai=False)
    return dataset


def get_demo_dataset():
    """The shared demo dataset: reused if it exists, created on first use."""
    dataset = Dataset.objects.filter(is_demo=True).select_related('business').order_by('-created_at').first()
    if dataset:
        return dataset
    with transaction.atomic():
        business = Business.objects.create(**DEMO_BUSINESS)
        dataset = create_dataset(business, DEMO_DATASET_NAME, demo_rows())
        dataset.is_demo = True
        dataset.save(update_fields=['is_demo'])
    return dataset


def refresh_recommendations(dataset, use_ai):
    """Recompute and store recommendations. With use_ai, falls back to rules if Claude fails."""
    report = load_report(dataset)
    note = ''
    if use_ai:
        try:
            result, source = ai_recommendations(report, dataset.business), Dataset.SOURCE_AI
        except AiUnavailable as error:
            result, source = rule_recommendations(report, dataset.business), Dataset.SOURCE_RULES
            note = f'{error} Показаны рекомендации по правилам.'
    else:
        result, source = rule_recommendations(report, dataset.business), Dataset.SOURCE_RULES

    dataset.recommendations = result
    dataset.recommendations_source = source
    dataset.recommendations_note = note[:300]
    dataset.recommendations_at = timezone.now()
    dataset.save(update_fields=[
        'recommendations', 'recommendations_source', 'recommendations_note', 'recommendations_at',
    ])
    return report
