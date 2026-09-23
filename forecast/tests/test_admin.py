from datetime import date

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from forecast.models import Business, Dataset, Record
from forecast.services import create_dataset, load_report
from forecast.recommendations import rule_recommendations


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.business = Business.objects.create(name='Кофейня', region='Алматы')
        cls.dataset = create_dataset(cls.business, 'Продажи', [
            (date(2025, month, 1), 'Кофе', month * 10) for month in range(1, 13)
        ])
        cls.root = User.objects.create_superuser(username='root', password=None)
        cls.regular = User.objects.create_user(username='regular')
        cls.inactive = User.objects.create_user(username='inactive', is_staff=True, is_active=False)
        cls.staff = User.objects.create_user(username='staff', is_staff=True)

    def grant(self, *codenames):
        self.staff.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
        self.client.force_login(self.staff)

    def change_url(self, model, obj):
        return reverse(f'admin:forecast_{model}_change', args=[obj.pk])

    def test_only_active_staff_can_enter(self):
        for user in (self.regular, self.inactive):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:forecast_business_changelist')).status_code, 403)

    def test_permission_cards_save_and_validate_group_permissions(self):
        self.client.force_login(self.root)
        group = Group.objects.create(name='Аналитики')
        permission = Permission.objects.get(codename='view_dataset')
        url = reverse('admin:auth_group_change', args=[group.pk])
        response = self.client.get(url)
        self.assertContains(response, 'data-permission-picker')
        self.assertContains(response, 'forecast/admin_permissions.js')
        self.assertContains(response, 'Просмотр')
        self.assertEqual(self.client.post(url, {'name': group.name, 'permissions': [permission.pk]}).status_code, 302)
        self.assertEqual(list(group.permissions.all()), [permission])
        self.staff.groups.add(group)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin:forecast_dataset_changelist')).status_code, 200)
        self.assertEqual(self.client.post(self.change_url('dataset', self.dataset), {'name': 'Wrong'}).status_code, 403)
        self.client.force_login(self.root)
        response = self.client.post(url, {'name': group.name, 'permissions': ['99999999']})
        self.assertEqual(response.status_code, 200)
        self.assertIn('permissions', response.context['adminform'].form.errors)
        self.assertEqual(list(group.permissions.all()), [permission])
        self.assertEqual(self.client.post(url, {'name': group.name}).status_code, 302)
        self.assertFalse(group.permissions.exists())

    def test_user_permission_cards_preserve_selected_permissions(self):
        from forecast.admin_forms import AdminUserForm

        permission = Permission.objects.get(codename='view_business')
        self.staff.user_permissions.add(permission)
        self.client.force_login(self.root)
        response = self.client.get(reverse('admin:auth_user_change', args=[self.staff.pk]))
        self.assertContains(response, 'data-permission-picker')
        self.assertContains(response, 'Индивидуальные права')
        form = AdminUserForm(instance=self.staff)
        groups = form.fields['user_permissions'].widget.optgroups('user_permissions', [str(permission.pk)])
        selected = [option for _, options, _ in groups for option in options if option['selected']]
        self.assertEqual([str(option['value']) for option in selected], [str(permission.pk)])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin:auth_user_change', args=[self.staff.pk])).status_code, 403)

    def test_dashboard_respects_model_permissions(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Разделы пока недоступны')
        self.grant('view_business')
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, reverse('admin:forecast_business_changelist'))
        self.assertNotContains(response, reverse('admin:auth_user_changelist'))
        self.assertNotContains(response, reverse('admin:forecast_business_add'))

    def test_workspace_statistics_obey_permissions_and_count_real_records(self):
        from forecast.templatetags.admin_workspace import workspace_summary
        from django.test import RequestFactory

        request = RequestFactory().get('/admin/')
        request.user = self.staff
        self.assertEqual(workspace_summary({'request': request})['metrics'], [])
        self.grant('view_dataset')
        request.user = User.objects.get(pk=self.staff.pk)
        summary = workspace_summary({'request': request})
        self.assertEqual(len(summary['metrics']), 1)
        self.assertEqual(summary['metrics'][0]['count'], 1)
        self.assertEqual(sum(day['count'] for day in summary['chart']), 1)
        self.assertEqual([dataset.pk for dataset in summary['datasets']], [self.dataset.pk])
        request.user = self.root
        self.assertEqual([metric['count'] for metric in workspace_summary({'request': request})['metrics']], [1, 1, 12, 4])

    def test_pro_admin_assets_are_scoped_to_admin(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'forecast/admin_pro.css?v=')
        self.assertContains(response, 'id="pro-sidebar"')
        self.assertContains(response, 'Обзор системы')
        self.assertNotContains(self.client.get(reverse('index')), 'forecast/admin_pro.css')

    def test_view_permission_cannot_change_or_recalculate(self):
        self.grant('view_dataset')
        url = self.change_url('dataset', self.dataset)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {'name': 'Tampered'}).status_code, 403)
        previous = self.dataset.recommendations_at
        self.client.post(reverse('admin:forecast_dataset_changelist'), {
            'action': 'recalculate', '_selected_action': [self.dataset.pk],
        })
        self.dataset.refresh_from_db()
        self.assertEqual(previous, self.dataset.recommendations_at)

    def test_recalculate_uses_existing_formula_and_logs(self):
        self.grant('view_dataset', 'change_dataset')
        Dataset.objects.filter(pk=self.dataset.pk).update(recommendations={})
        response = self.client.post(reverse('admin:forecast_dataset_changelist'), {
            'action': 'recalculate', '_selected_action': [self.dataset.pk],
        })
        self.assertEqual(response.status_code, 302)
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.recommendations, rule_recommendations(load_report(self.dataset), self.business))
        self.assertTrue(LogEntry.objects.filter(user=self.staff, object_id=str(self.dataset.pk)).exists())

    def test_calculated_fields_and_business_cannot_be_forged(self):
        self.grant('change_dataset')
        other = Business.objects.create(name='Другой бизнес', region='Астана')
        before = self.dataset.recommendations
        response = self.client.post(self.change_url('dataset', self.dataset), {
            'name': 'Новое название', 'business': other.pk,
            'recommendations': '{"forged": true}', 'recommendations_source': 'ai',
        })
        self.assertEqual(response.status_code, 302)
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.name, 'Новое название')
        self.assertEqual(self.dataset.business_id, self.business.pk)
        self.assertEqual(self.dataset.recommendations, before)
        self.assertEqual(self.dataset.recommendations_source, 'rules')

    def test_business_change_refreshes_recommendations(self):
        self.grant('change_business')
        Dataset.objects.filter(pk=self.dataset.pk).update(recommendations={})
        response = self.client.post(self.change_url('business', self.business), {
            'name': 'Кофейня', 'region': 'Алматы', 'business_type': 'retail', 'lead_time_weeks': 8,
        })
        self.assertEqual(response.status_code, 302)
        self.business.refresh_from_db()
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.recommendations, rule_recommendations(load_report(self.dataset), self.business))
        self.assertEqual(LogEntry.objects.filter(user=self.staff).count(), 2)

    def test_staff_cannot_reassign_private_business_owner(self):
        self.business.owner = self.regular
        self.business.save(update_fields=['owner'])
        self.grant('change_business')
        self.client.post(self.change_url('business', self.business), {
            'name': 'Кофейня', 'region': 'Алматы', 'business_type': 'retail',
            'lead_time_weeks': 3, 'owner': self.staff.pk,
        })
        self.business.refresh_from_db()
        self.assertEqual(self.business.owner, self.regular)

    def test_validation(self):
        self.grant('change_business')
        response = self.client.post(self.change_url('business', self.business), {
            'name': '', 'region': '', 'business_type': 'retail', 'lead_time_weeks': 53,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['adminform'].form.errors), {'name', 'region', 'lead_time_weeks'})
        self.business.refresh_from_db()
        self.assertEqual(self.business.lead_time_weeks, 3)

    def test_imported_history_is_protected_even_for_superuser(self):
        self.client.force_login(self.root)
        record = self.dataset.records.first()
        self.assertEqual(self.client.post(self.change_url('record', record), {'quantity': 999}).status_code, 403)
        for model, obj in [('business', self.business), ('dataset', self.dataset), ('record', record)]:
            self.assertEqual(self.client.post(reverse(f'admin:forecast_{model}_delete', args=[obj.pk]), {'post': 'yes'}).status_code, 403)
            self.client.post(reverse(f'admin:forecast_{model}_changelist'), {
                'action': 'delete_selected', '_selected_action': [obj.pk], 'post': 'yes',
            })
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
        for model in ('record', 'dataset'):
            self.assertEqual(self.client.post(reverse(f'admin:forecast_{model}_add'), {}).status_code, 403)
        record.refresh_from_db()
        self.assertNotEqual(record.quantity, 999)

    def test_staff_cannot_elevate_users_or_groups(self):
        self.grant('view_user', 'change_user', 'add_user', 'delete_user',
                   'view_group', 'change_group', 'add_group', 'delete_group')
        url = reverse('admin:auth_user_change', args=[self.staff.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {'is_superuser': 'on'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:auth_user_password_change', args=[self.staff.pk]), {}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:auth_user_add'), {}).status_code, 403)
        group = Group.objects.create(name='Операторы')
        self.assertEqual(self.client.post(reverse('admin:auth_group_change', args=[group.pk]), {}).status_code, 403)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_superuser)
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_staff)

    def test_lists_search_and_related_filters(self):
        self.client.force_login(self.root)
        for model in ('business', 'dataset', 'record'):
            self.assertEqual(self.client.get(reverse(f'admin:forecast_{model}_changelist'), {'q': 'Кофе'}).status_code, 200)
        response = self.client.get(reverse('admin:forecast_record_changelist'), {'dataset__id__exact': self.dataset.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cl'].result_count, 12)

    def test_admin_theme_is_shared_with_public_site(self):
        response = self.client.get(reverse('admin:login'))
        self.assertTemplateUsed(response, 'admin/base_site.html')
        self.assertContains(response, 'forecast/admin.css')
        self.assertContains(response, 'forecast/theme.js')
        self.assertContains(response, 'data-set-theme="dark"')
        self.assertNotContains(response, 'admin/js/theme.js')
        self.client.force_login(self.root)
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'data-set-theme="light"')
        self.assertContains(response, 'brand-mark')

    def test_site_admin_link_is_only_shown_to_active_staff(self):
        admin_url = f'href="{reverse("admin:index")}"'
        self.assertNotContains(self.client.get(reverse('index')), admin_url)
        self.client.force_login(self.regular)
        self.assertNotContains(self.client.get(reverse('index')), admin_url)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse('index')), admin_url)

    def test_dataset_admin_links_to_report_and_explains_recommendations(self):
        self.grant('view_dataset')
        self.dataset.recommendations_note = 'Использованы рекомендации по правилам.'
        self.dataset.save(update_fields=['recommendations_note'])
        response = self.client.get(self.change_url('dataset', self.dataset))
        self.assertContains(response, reverse('dashboard', args=[self.dataset.pk]))
        self.assertContains(response, self.dataset.recommendations_note)
