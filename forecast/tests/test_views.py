from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from forecast.ai import AiAnswer, AiRecommendation
from forecast.models import Business, Dataset


class ViewsTests(TestCase):
    def test_index_shows_example_forecast_on_demo_data(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'ПРИМЕР ПРОГНОЗА')
        self.assertContains(response, 'Зимние шины')
        self.assertContains(response, 'заказать до 11.10.2026')
        self.assertContains(response, 'class="example-fact"')
        dataset = Dataset.objects.get()
        self.assertTrue(dataset.is_demo)
        self.assertContains(response, reverse('dashboard', args=[dataset.id]))

    def test_demo_dataset_is_reused(self):
        self.client.get(reverse('index'))
        self.client.post(reverse('demo'))
        self.client.post(reverse('demo'))
        self.assertEqual(Dataset.objects.count(), 1)

    def test_demo_creates_dataset_and_dashboard_shows_recommendations(self):
        response = self.client.post(reverse('demo'), follow=True)
        self.assertEqual(response.status_code, 200)
        dataset = Dataset.objects.get()
        self.assertEqual(dataset.recommendations_source, Dataset.SOURCE_RULES)
        self.assertContains(response, 'Зимние шины')
        self.assertContains(response, '11.10.2026')
        self.assertContains(response, 'chart-data')

    def test_upload_csv(self):
        rows = ['date;category;quantity'] + [
            f'28.{i % 12 + 1:02d}.{2024 + i // 12};Кофе;{10 + i}' for i in range(28)
        ]
        csv = SimpleUploadedFile('sales.csv', '\n'.join(rows).encode('utf-8'), content_type='text/csv')
        response = self.client.post(reverse('upload'), {
            'name': 'Кофейня', 'business_type': 'retail', 'region': 'Астана',
            'lead_time_weeks': 2, 'file': csv,
        })
        dataset = Dataset.objects.get()
        self.assertRedirects(response, reverse('dashboard', args=[dataset.id]))
        self.assertEqual(dataset.records.count(), 28)
        self.assertEqual(dataset.business.region, 'Астана')

    def test_upload_with_bad_file_shows_error(self):
        csv = SimpleUploadedFile('bad.csv', b'foo,bar\n1,2\n', content_type='text/csv')
        response = self.client.post(reverse('upload'), {
            'name': 'X', 'business_type': 'retail', 'region': 'Y', 'lead_time_weeks': 1, 'file': csv,
        })
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'В файле нет колонок', status_code=400)
        self.assertFalse(Dataset.objects.exists())

    def test_sample_csv_downloads(self):
        response = self.client.get(reverse('sample_csv'))
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(response.content.decode().startswith('date,category,quantity'))

    def test_failed_import_does_not_leave_an_empty_business(self):
        for route in ('upload', 'demo'):
            with self.subTest(route=route):
                payload = {}
                if route == 'upload':
                    payload = {
                        'name': 'Кофейня', 'business_type': 'retail', 'region': 'Алматы',
                        'lead_time_weeks': 2,
                        'file': SimpleUploadedFile('sales.csv', b'date,category,quantity\n2026-01-01,Coffee,25\n'),
                    }
                with mock.patch('forecast.views.services.create_dataset', side_effect=RuntimeError('Import failed')):
                    with self.assertRaises(RuntimeError):
                        self.client.post(reverse(route), payload)
                self.assertFalse(Business.objects.exists())
                self.assertFalse(Dataset.objects.exists())

    @mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': '', 'ANTHROPIC_AUTH_TOKEN': ''})
    def test_recommend_without_key_falls_back_to_rules_with_note(self):
        self.client.post(reverse('demo'))
        dataset = Dataset.objects.get()
        response = self.client.post(reverse('recommend', args=[dataset.id]), follow=True)
        dataset.refresh_from_db()
        self.assertEqual(dataset.recommendations_source, Dataset.SOURCE_RULES)
        self.assertContains(response, 'ANTHROPIC_API_KEY')

    def test_recommend_with_claude(self):
        self.client.post(reverse('demo'))
        dataset = Dataset.objects.get()
        answer = AiAnswer(summary='Готовьтесь к зиме.', recommendations=[AiRecommendation(
            category='Зимние шины', action='prepare_peak', title='Закажите зимние шины',
            reason='Пик в ноябре.', deadline='2026-10-11', confidence='high',
        )])
        with mock.patch('forecast.ai.anthropic.Anthropic') as client_cls, \
                mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test'}):
            client_cls.return_value.messages.parse.return_value = mock.Mock(
                stop_reason='end_turn', parsed_output=answer,
            )
            response = self.client.post(reverse('recommend', args=[dataset.id]), follow=True)
        dataset.refresh_from_db()
        self.assertEqual(dataset.recommendations_source, Dataset.SOURCE_AI)
        self.assertContains(response, 'Готовьтесь к зиме.')
        self.assertContains(response, 'Ответ ИИ')
