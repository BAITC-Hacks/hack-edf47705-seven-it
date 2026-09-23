"""Claude turns the computed analytics into plain-language recommendations.

Claude only sees numbers computed in analytics.py and is told not to add outside facts. Its answer
is then checked in code: unknown categories are dropped and deadlines always come from our own
calculation, never from the model.
"""

import json
import logging
import os
from typing import Literal

import anthropic
from django.conf import settings
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — аналитик спроса для малого бизнеса. Владелец загрузил историю продаж или записей, \
а система уже посчитала по каждой категории тренд, сезонность, прогноз на 3 месяца и дату, \
до которой нужно подготовиться к сезонному пику (order_by).

Твоя задача — превратить эти цифры в понятные решения: что заказать больше, что сократить, \
когда готовить дополнительные смены.

Правила:
- Опирайся только на цифры из данных. Не придумывай внешних причин: погоду, новости, праздники, \
действия конкурентов, цены. Если причина неизвестна, просто опиши изменение.
- Каждая рекомендация — про одну категорию; поле category копируй в точности как в данных.
- В reason приводи конкретные числа из данных (проценты, прогноз в единицах, месяц пика, дату order_by).
- deadline указывай только если у категории есть order_by, и ровно эту дату; иначе null.
- confidence бери из данных категории. Если уверенность низкая, прямо скажи об этом в reason.
- Для услуг говори о сменах и мастерах, для торговли — о закупке и запасах.
- Стабильные категории без пика не включай. Дай от 3 до 7 рекомендаций, самые срочные — первыми.
- summary — 2–3 предложения для владельца: главное, что происходит со спросом.
- Пиши по-русски, коротко и по делу."""


class AiRecommendation(BaseModel):
    category: str
    action: Literal['increase', 'decrease', 'prepare_peak', 'hold']
    title: str
    reason: str
    deadline: str | None
    confidence: Literal['high', 'medium', 'low']


class AiAnswer(BaseModel):
    summary: str
    recommendations: list[AiRecommendation]


class AiUnavailable(Exception):
    """Claude could not produce recommendations; the caller falls back to rules."""


def build_payload(report, business):
    return {
        'business': {
            'name': business.name,
            'type': 'торговля (продажи товаров, шт.)' if business.business_type == 'retail'
                    else 'услуги (записи клиентов)',
            'region': business.region,
            'lead_time_weeks': business.lead_time_weeks,
        },
        'data_until': report.as_of.isoformat(),
        'categories': [
            {**insight.to_dict(), 'last_12_months': [
                {'month': m, 'value': v} for m, v in insight.history[-12:]
            ]}
            for insight in report.insights
        ],
    }


def _validated_items(answer, report):
    insights = {i.category: i for i in report.insights}
    items = []
    for rec in answer.recommendations:
        insight = insights.get(rec.category)
        if insight is None:
            logger.warning('Claude returned unknown category %r, dropped', rec.category)
            continue
        deadline = insight.order_by.isoformat() if rec.deadline and insight.order_by else None
        items.append({
            'category': rec.category,
            'action': rec.action,
            'title': rec.title,
            'reason': rec.reason,
            'deadline': deadline,
            'confidence': insight.confidence,
        })
    return items


def ai_recommendations(report, business, client=None):
    """Ask Claude for recommendations. Raises AiUnavailable on any failure."""
    if client is None and not (os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_AUTH_TOKEN')):
        raise AiUnavailable('Claude не настроен: задайте ANTHROPIC_API_KEY в файле .env.')
    try:
        client = client or anthropic.Anthropic()
        response = client.messages.parse(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{
                'role': 'user',
                'content': 'Данные для анализа (JSON):\n'
                           + json.dumps(build_payload(report, business), ensure_ascii=False),
            }],
            output_config={'effort': 'medium'},
            output_format=AiAnswer,
        )
    except anthropic.AuthenticationError as error:
        raise AiUnavailable('Неверный ключ ANTHROPIC_API_KEY.') from error
    except anthropic.RateLimitError as error:
        raise AiUnavailable('Превышен лимит запросов к Claude, попробуйте через минуту.') from error
    except anthropic.APIStatusError as error:
        logger.warning('Claude API request failed (HTTP %s)', error.status_code)
        raise AiUnavailable(f'Ошибка Claude API ({error.status_code}).') from error
    except anthropic.APIConnectionError as error:
        raise AiUnavailable('Нет соединения с Claude API.') from error
    except (anthropic.AnthropicError, ValidationError) as error:
        logger.warning('Claude request failed (%s)', type(error).__name__)
        raise AiUnavailable('Не удалось получить ответ Claude.') from error

    if response.stop_reason == 'refusal':
        raise AiUnavailable('Claude отказался отвечать на этот запрос.')
    if response.stop_reason == 'max_tokens' or response.parsed_output is None:
        raise AiUnavailable('Claude вернул неполный ответ.')

    answer = response.parsed_output
    items = _validated_items(answer, report)
    if not items:
        raise AiUnavailable('Claude не дал ни одной рекомендации по категориям из данных.')
    return {'summary': answer.summary, 'items': items}
