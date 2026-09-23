from datetime import date
from types import SimpleNamespace
from unittest import mock

import anthropic
from django.test import SimpleTestCase

from forecast.ai import AiAnswer, AiRecommendation, AiUnavailable, ai_recommendations
from forecast.analytics import analyze_records
from forecast.demo_data import DEMO_BUSINESS, demo_rows
from forecast.recommendations import rule_recommendations

BUSINESS = SimpleNamespace(**DEMO_BUSINESS)


def demo_report():
    return analyze_records(demo_rows(), BUSINESS.lead_time_weeks)


def fake_client(answer=None, stop_reason='end_turn', error=None):
    client = mock.Mock()
    if error:
        client.messages.parse.side_effect = error
    else:
        client.messages.parse.return_value = SimpleNamespace(stop_reason=stop_reason, parsed_output=answer)
    return client


class RuleRecommendationsTests(SimpleTestCase):
    def test_demo_data_gives_peak_preparation_with_dates(self):
        result = rule_recommendations(demo_report(), BUSINESS)
        peaks = [r for r in result['items'] if r['action'] == 'prepare_peak']
        self.assertIn('Зимние шины', [r['category'] for r in peaks])
        winter = next(r for r in peaks if r['category'] == 'Зимние шины')
        self.assertEqual(winter['deadline'], '2026-10-11')
        self.assertIn('11.10.2026', winter['reason'])

    def test_deadlines_come_first(self):
        items = rule_recommendations(demo_report(), BUSINESS)['items']
        seen_undated = False
        for item in items:
            if item['deadline'] is None:
                seen_undated = True
            else:
                self.assertFalse(seen_undated, 'dated item after an undated one')

    def test_falling_category_gets_decrease(self):
        items = rule_recommendations(demo_report(), BUSINESS)['items']
        summer = next(r for r in items if r['category'] == 'Летние шины')
        self.assertEqual(summer['action'], 'decrease')

    def test_services_wording_talks_about_shifts(self):
        services = SimpleNamespace(**{**DEMO_BUSINESS, 'business_type': 'services'})
        items = rule_recommendations(demo_report(), services)['items']
        self.assertTrue(any('смен' in r['title'] or 'смен' in r['reason'] for r in items))


class AiRecommendationsTests(SimpleTestCase):
    def answer(self, *recs):
        return AiAnswer(summary='Итог', recommendations=list(recs))

    def rec(self, category, deadline=None, action='prepare_peak'):
        return AiRecommendation(
            category=category, action=action, title='t', reason='r', deadline=deadline, confidence='high',
        )

    def test_unknown_categories_are_dropped_and_deadlines_come_from_analytics(self):
        answer = self.answer(
            self.rec('Зимние шины', deadline='2030-01-01'),  # invented date must be replaced
            self.rec('Снегоходы'),  # not in the data
            self.rec('Летние шины', action='decrease'),
        )
        result = ai_recommendations(demo_report(), BUSINESS, client=fake_client(answer))
        self.assertEqual([i['category'] for i in result['items']], ['Зимние шины', 'Летние шины'])
        self.assertEqual(result['items'][0]['deadline'], '2026-10-11')
        self.assertIsNone(result['items'][1]['deadline'])
        # Confidence always comes from our analytics, not from the model.
        self.assertEqual(result['items'][0]['confidence'], 'medium')

    def test_prompt_contains_only_computed_numbers(self):
        client = fake_client(self.answer(self.rec('Зимние шины')))
        ai_recommendations(demo_report(), BUSINESS, client=client)
        kwargs = client.messages.parse.call_args.kwargs
        self.assertEqual(kwargs['output_format'], AiAnswer)
        content = kwargs['messages'][0]['content']
        self.assertIn('"order_by": "2026-10-11"', content)
        self.assertIn('Алматы', content)

    def test_refusal_raises_unavailable(self):
        with self.assertRaises(AiUnavailable):
            ai_recommendations(demo_report(), BUSINESS, client=fake_client(None, stop_reason='refusal'))

    def test_only_unknown_categories_raises_unavailable(self):
        with self.assertRaises(AiUnavailable):
            ai_recommendations(demo_report(), BUSINESS, client=fake_client(self.answer(self.rec('Нет такой'))))

    def test_connection_error_raises_unavailable(self):
        error = anthropic.APIConnectionError(request=mock.Mock())
        with self.assertRaisesMessage(AiUnavailable, 'соединения'):
            ai_recommendations(demo_report(), BUSINESS, client=fake_client(error=error))

    @mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': '', 'ANTHROPIC_AUTH_TOKEN': ''})
    def test_missing_key_raises_unavailable(self):
        with self.assertRaisesMessage(AiUnavailable, 'ANTHROPIC_API_KEY'):
            ai_recommendations(demo_report(), BUSINESS)


class DemoReportTests(SimpleTestCase):
    def test_demo_data_ends_at_expected_date(self):
        self.assertEqual(demo_report().as_of, date(2026, 8, 31))
