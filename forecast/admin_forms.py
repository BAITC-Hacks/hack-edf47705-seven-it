"""Presentation of Django permissions; authorization remains in ModelAdmin."""

from collections import OrderedDict

from django import forms
from django.apps import apps
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group, Permission


class PermissionCards(forms.CheckboxSelectMultiple):
    template_name = 'forecast/admin/permission_cards.html'

    def optgroups(self, name, value, attrs=None):
        grouped = OrderedDict()
        for _, options, _ in super().optgroups(name, value, attrs):
            for option in options:
                permission = option['value'].instance
                content_type = permission.content_type
                model = content_type.model_class()
                app = apps.get_app_config(content_type.app_label)
                label = f'{app.verbose_name} / {model._meta.verbose_name_plural if model else content_type.model}'
                grouped.setdefault(label, []).append(option)
        return [(label, options, index) for index, (label, options) in enumerate(grouped.items())]

    class Media:
        js = ('forecast/admin_permissions.js',)


class PermissionField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        model = obj.content_type.model_class()
        action, _, model_name = obj.codename.partition('_')
        labels = {'view': 'Просмотр', 'add': 'Добавление', 'change': 'Изменение', 'delete': 'Удаление'}
        if model and model_name == model._meta.model_name and action in labels:
            return labels[action]
        return obj.name


def permission_field(label):
    return PermissionField(
        label=label, required=False,
        queryset=Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model', 'codename'),
        widget=PermissionCards,
        help_text='Отметьте нужные действия и сохраните форму. Ограничения разделов действуют независимо от выбранных прав.',
    )


class AdminUserForm(UserChangeForm):
    user_permissions = permission_field('Индивидуальные права')


class AdminGroupForm(forms.ModelForm):
    permissions = permission_field('Права группы')

    class Meta:
        model = Group
        fields = '__all__'
