from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Business, Dataset, Record
from .admin_forms import AdminGroupForm, AdminUserForm
from .services import refresh_recommendations

admin.site.site_header = 'Администрирование Foresell'
admin.site.site_title = 'Foresell — управление'
admin.site.index_title = 'Управление бизнесом и данными'
admin.site.enable_nav_sidebar = False  # The admin-only shell supplies its own navigation.
admin.site.index_template = 'admin/workspace_index.html'


class ProtectedIdentityAdmin:
    """Only superusers may mutate identities or permission-bearing groups."""

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class SafeUserAdmin(ProtectedIdentityAdmin, UserAdmin):
    form = AdminUserForm
    filter_horizontal = ('groups',)
    list_display = ('username', 'email', 'first_name', 'last_name', 'access_status', 'is_active', 'is_staff')
    list_per_page = 50
    search_help_text = 'Поиск по логину, имени, фамилии или email.'

    @admin.display(description='Уровень доступа', ordering='is_superuser')
    def access_status(self, obj):
        if not obj.is_active:
            label, style = 'Отключён', 'muted'
        elif obj.is_superuser:
            label, style = 'Суперадминистратор', 'accent'
        elif obj.is_staff:
            label, style = 'Сотрудник', 'success'
        else:
            label, style = 'Пользователь', 'muted'
        return format_html('<span class="access-badge access-badge--{}">{}</span>', style, label)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            fieldsets = tuple((title, {**options, **({'description':
                'Активность и статус сотрудника открывают вход в панель. Группы объединяют права; '
                'индивидуальные права дополняют их. Суперадминистратор получает все права. '
                'Изменение пользователей и групп доступно только суперадминистратору.'
            } if 'user_permissions' in options['fields'] else {})}) for title, options in fieldsets)
        if request.user.is_superuser:
            return fieldsets
        return tuple((title, {**options, 'fields': tuple(
            field for field in options['fields'] if field != 'password'
        )}) for title, options in fieldsets)


@admin.register(Group)
class SafeGroupAdmin(ProtectedIdentityAdmin, GroupAdmin):
    form = AdminGroupForm
    filter_horizontal = ()
    list_per_page = 50
    list_display = ('name', 'permission_count', 'member_count')
    search_help_text = 'Найдите группу по названию. Права группы наследуются её участниками.'

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _permissions=Count('permissions', distinct=True), _members=Count('user', distinct=True))

    @admin.display(description='Разрешения', ordering='_permissions')
    def permission_count(self, obj):
        return obj._permissions

    @admin.display(description='Участники', ordering='_members')
    def member_count(self, obj):
        return obj._members


class NoDeleteAdmin(admin.ModelAdmin):
    list_per_page = 50

    def has_delete_permission(self, request, obj=None):
        # There is no reversal workflow for imported history in this project.
        return False


def related_list(model, field, pk, label):
    url = reverse(f'admin:forecast_{model}_changelist')
    return format_html('<a href="{}?{}">{}</a>', url, urlencode({field: pk}), label)


class BusinessAdminForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = '__all__'

    def clean_lead_time_weeks(self):
        value = self.cleaned_data['lead_time_weeks']
        if value > 52:
            raise forms.ValidationError('Срок подготовки не должен превышать 52 недели.')
        return value


@admin.register(Business)
class BusinessAdmin(NoDeleteAdmin):
    form = BusinessAdminForm
    list_display = ('name', 'business_type', 'region', 'lead_time_weeks', 'created_at', 'datasets_link')
    search_fields = ('name', 'region')
    list_filter = ('business_type', 'region', 'created_at')
    ordering = ('-created_at', '-pk')
    readonly_fields = ('created_at', 'datasets_link')
    date_hierarchy = 'created_at'

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return fields if request.user.is_superuser else (*fields, 'owner')

    @admin.display(description='Наборы данных')
    def datasets_link(self, obj):
        return related_list('dataset', 'business__id__exact', obj.pk, 'Открыть наборы данных') if obj.pk else '—'

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            if change and set(form.changed_data) & {'name', 'business_type', 'region', 'lead_time_weeks'}:
                for dataset in obj.datasets.all():
                    refresh_recommendations(dataset, use_ai=False)
                    self.log_change(request, dataset, 'Рекомендации пересчитаны после изменения бизнес-профиля.')


@admin.register(Dataset)
class DatasetAdmin(NoDeleteAdmin):
    list_display = ('name', 'business', 'record_count', 'recommendations_source', 'recommendations_at', 'report_link')
    list_filter = ('recommendations_source', 'business__business_type', 'created_at')
    search_fields = ('name', 'business__name', 'business__region')
    ordering = ('-created_at', '-pk')
    list_select_related = ('business',)
    date_hierarchy = 'created_at'
    readonly_fields = ('business', 'created_at', 'recommendations', 'recommendations_source',
                       'recommendations_at', 'recommendations_note', 'records_link', 'report_link')
    fields = ('name', 'business', 'created_at', 'records_link', 'report_link', 'recommendations_source',
              'recommendations_at', 'recommendations_note', 'recommendations')
    actions = ('recalculate',)

    def has_add_permission(self, request):
        return False  # Use the validated CSV import.

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_record_count=Count('records'))

    @admin.display(description='Число записей', ordering='_record_count')
    def record_count(self, obj):
        return obj._record_count

    @admin.display(description='История')
    def records_link(self, obj):
        return related_list('record', 'dataset__id__exact', obj.pk, 'Открыть записи')

    @admin.display(description='Прогноз')
    def report_link(self, obj):
        return format_html('<a href="{}">Открыть прогноз</a>', reverse('dashboard', args=[obj.pk]))

    @admin.action(description='Пересчитать рекомендации по правилам', permissions=['change'])
    def recalculate(self, request, queryset):
        if not self.has_change_permission(request):
            raise PermissionDenied
        with transaction.atomic():
            for dataset in queryset:
                refresh_recommendations(dataset, use_ai=False)
                self.log_change(request, dataset, 'Рекомендации пересчитаны по правилам.')
        self.message_user(request, 'Рекомендации пересчитаны из истории продаж и бронирований.', messages.SUCCESS)


@admin.register(Record)
class RecordAdmin(NoDeleteAdmin):
    list_display = ('dataset', 'date', 'category', 'quantity')
    list_filter = ('date', 'dataset__business__business_type')
    search_fields = ('category', 'dataset__name', 'dataset__business__name')
    ordering = ('-date', '-pk')
    list_select_related = ('dataset',)
    date_hierarchy = 'date'
    readonly_fields = ('dataset', 'date', 'category', 'quantity')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
