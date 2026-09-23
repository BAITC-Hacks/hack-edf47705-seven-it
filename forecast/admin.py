from django.contrib import admin

from .models import Business, Dataset, Record


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'business_type', 'region', 'lead_time_weeks', 'created_at']


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'recommendations_source', 'created_at']


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ['dataset', 'date', 'category', 'quantity']
    list_filter = ['dataset', 'category']
