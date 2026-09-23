"""Compact product views and an isolated, deterministic presentation scenario.

Demo people, purchases, prices and unconfirmed specifications are fictional.
Nothing in this module writes to users, reviews, observations or accounting.
"""
from datetime import timedelta
from hashlib import sha256

from django.utils import timezone

from .grocery_catalog import GROCERY_BY_KEY


# Invented names for the presentation; they do not identify the photographed ЖК.
DEMO_HOME_NAMES = {
    'residence-corner': 'ЖК «Auralis»',
    'residence-boulevard': 'ЖК «Qala Botanica»',
    'residence-stone': 'ЖК «Tumar Loft»',
    'residence-color-blocks': 'ЖК «Terra Mosaic»',
    'residence-courtyard': 'ЖК «Sfera Gardens»',
    'residence-evening': 'ЖК «Aspan Noir»',
    'apartments': 'ЖК «Lumière Park»',
}

# Irregular weekly paths. The signal is computed from the values, never from
# the product's position in the catalogue. A reload preserves the same story.
SALES_STORIES = {
    'surge': ('Покупают чаще, с небольшими колебаниями', [6, 9, 7, 11, 12, 19, 15, 23]),
    'quiet': ('Спрос держится примерно на одном уровне', [11, 10, 12, 11, 12, 10, 11, 12]),
    'peak_drop': ('После высокого пика — резкое падение', [8, 12, 27, 42, 31, 10, 4, 2]),
    'rebound': ('После спада покупатели возвращаются', [18, 10, 5, 8, 9, 17, 22, 26]),
    'plateau': ('Небольшие колебания без заметного роста', [12, 15, 16, 14, 14, 16, 15, 13]),
    'slowdown': ('Продажи постепенно замедляются', [24, 21, 25, 19, 16, 10, 12, 8]),
    'launch': ('Быстрый рост, затем откат от пика', [3, 6, 8, 10, 16, 24, 34, 19]),
    'flash_drop': ('Короткий всплеск и резкий спад', [10, 16, 48, 40, 12, 9, 7, 11]),
}

PRODUCT_STORIES = {
    'residence-corner': 'surge', 'residence-boulevard': 'rebound',
    'residence-stone': 'quiet', 'residence-color-blocks': 'peak_drop',
    'residence-courtyard': 'plateau', 'residence-evening': 'launch',
    'xiaomi-15-ultra': 'launch', 'realme-smartphones': 'surge',
    'honor-smartphone': 'slowdown', 'huawei-pura-80-ultra': 'flash_drop',
    'samsung-smartphone': 'quiet', 'jac-t8-pro': 'peak_drop',
    'volkswagen-passat': 'plateau', 'volkswagen-bora': 'rebound',
    'bmw-3-series': 'surge', 'apartments': 'flash_drop',
    'crossover': 'surge', 'coffee': 'rebound', 'rice': 'quiet',
    'paper': 'plateau', 'sedan': 'slowdown',
}


def demo_title(product):
    key = product.photo_key or product.demo_key
    return DEMO_HOME_NAMES.get(key, product.title) if product.kind == 'home' else product.title


SIGNALS = {
    'up': {'label': 'Спрос растёт', 'symbol': '↗', 'hint': 'Покупают всё чаще'},
    'steady': {'label': 'Стабильный спрос', 'symbol': '→', 'hint': 'Покупают в обычном темпе'},
    'down': {'label': 'Спрос падает', 'symbol': '↘', 'hint': 'Покупают всё реже'},
    'unknown': {'label': 'Спрос пока неизвестен', 'symbol': '—', 'hint': 'Нужна история продаж'},
}

PHOTO_ORDER = [
    'residence-corner', 'residence-boulevard', 'residence-stone',
    'residence-color-blocks', 'residence-courtyard', 'residence-evening',
    'xiaomi-15-ultra', 'realme-smartphones', 'honor-smartphone',
    'huawei-pura-80-ultra', 'samsung-smartphone', 'jac-t8-pro',
    'volkswagen-passat', 'volkswagen-bora', 'bmw-3-series',
]

PEOPLE = ['Алия', 'Данияр', 'Мадина', 'Арман', 'Аружан',
          'Тимур', 'Диана', 'Ерлан', 'Айгерим', 'Азамат']

# These are scripted opinions, not statements by registered users or owners.
DEMO_COMMENTS = {
    'food': [
        'Удобная фасовка для обычной продуктовой корзины.',
        'Беру понемногу, чтобы дома всегда был запас.',
        'Добавила к еженедельной закупке.',
        'Подходит для повседневного меню.',
        'Небольшую упаковку удобно взять на пробу.',
        'Сравниваю цену с похожими продуктами.',
        'Перед покупкой посмотрю состав на этикетке.',
        'Для меня важны дата производства и условия доставки.',
        'По этой цене пока дороговато для регулярных покупок.',
        'У меня уже есть запас, сейчас докупать не планирую.',
    ],
    'home': [
        'Для семьи подходит: две отдельные комнаты и удобная планировка.',
        'Понравился двор. Рассматриваю такой вариант для переезда.',
        'Мне важно, чтобы рядом было место для прогулок. Здесь это выглядит удачно.',
        'Большие окна — то, что хочется видеть в новой квартире.',
        'По площади подходит, хотелось бы посмотреть планировку вживую.',
        'Сравниваю несколько квартир. Эта пока в избранном.',
        'Внешне нравится, но сначала уточню шумоизоляцию.',
        'Для меня важнее дорога до работы. Расположение ещё нужно сравнить.',
        'Цена выше моего бюджета, поэтому пока отложила.',
        'Без понятных расходов на содержание я бы не торопился.',
    ],
    'car': [
        'Нравится внешний вид. Для моих ежедневных поездок формат подходит.',
        'Рассматриваю для поездок с семьёй. Салон хотелось бы посмотреть лично.',
        'Сохранила в избранное, буду сравнивать комплектации.',
        'Для меня хороший вариант, если обслуживание укладывается в бюджет.',
        'Интересная машина, хочу записаться на тест-драйв.',
        'Всё решит итоговая цена и гарантия.',
        'Для моего двора может оказаться крупноватой.',
        'До выбора нужно посчитать страховку и обслуживание.',
        'На данный момент дорого. Посмотрю более доступные варианты.',
        'Покупку отложил: нужна полная история и диагностика.',
    ],
    'electronics': [
        'Для фото и обычных приложений такой вариант мне интересен.',
        'Нравится дизайн. Объёма памяти в примере мне достаточно.',
        'Искала телефон с большим экраном — добавила в избранное.',
        'Хочу сравнить камеру с моим старым телефоном.',
        'По характеристикам подходит. Уточню региональную версию.',
        'Выбираю между несколькими моделями, пока без окончательного решения.',
        'Для моих задач много лишних возможностей.',
        'Перед покупкой важно проверить работу привычных приложений.',
        'Сейчас выходит за мой бюджет, дождусь другого предложения.',
        'Мне нужен вариант проще и дешевле, поэтому пропущу.',
    ],
    'other': [
        'Мне подходит для регулярных закупок.', 'Добавил в избранное, удобно сравнивать.',
        'Интересное предложение, уточню доставку.', 'Планирую взять небольшую партию.',
        'Хочу сначала попробовать и оценить качество.', 'Сравниваю цену с другими предложениями.',
        'Нужно уточнить условия хранения.', 'Для меня важнее сроки доставки.',
        'Пока выходит дорого, отложила покупку.', 'У меня уже есть запас, докупать не планирую.',
    ],
}


def compact_facts(product):
    """Show important facts immediately; never infer hidden specs from a photo."""
    specs = (product.brief or {}).get('specifications', {})
    key = product.photo_key
    if product.demo_key in GROCERY_BY_KEY:
        return list(GROCERY_BY_KEY[product.demo_key]['specifications'].items())
    if product.kind == 'home':
        return [('Комнаты', 'Уточняются'), ('Площадь', 'Уточняется'),
                ('Расположение', product.region if product.region and product.region != 'Не указан' else 'Уточняется')]
    if product.kind == 'electronics':
        if key == 'xiaomi-15-ultra':
            return [('Процессор', 'Snapdragon 8 Elite'), ('Память / ОЗУ', 'Уточнить версию'), ('Экран', '6,73″ · 120 Гц')]
        if key == 'huawei-pura-80-ultra':
            return [('Процессор', 'Уточняется'), ('Память', '512 ГБ'), ('ОЗУ', '16 ГБ')]
        return [('Процессор', 'Уточняется'), ('Память', 'Уточняется'), ('ОЗУ', 'Уточняется')]
    if product.kind == 'car':
        if key == 'jac-t8-pro':
            return [('Двигатель', '2,4T · 204 л.с.'), ('Коробка', 'Механика · 6 ст.'), ('Привод', 'Подключаемый полный')]
        return [('Кузов', specs.get('Кузов', 'Уточняется')),
                ('Двигатель', specs.get('Двигатель в каталоге KZ', 'Уточняется')),
                ('Мощность', specs.get('Мощность этой версии', 'Уточняется'))]
    return [('Категория', product.get_kind_display()), ('Единица', product.unit),
            ('В наличии', f'{product.stock} {product.unit}' if product.stock is not None else 'Уточняется')]


def demo_scenario(product):
    key = product.photo_key or product.demo_key or f'product-{product.pk}'
    fingerprint = int.from_bytes(sha256(key.encode('utf-8')).digest()[:4], 'big')
    index = PHOTO_ORDER.index(product.photo_key) if product.photo_key in PHOTO_ORDER else fingerprint % 15
    grocery = GROCERY_BY_KEY.get(product.demo_key)
    story_key = grocery['story'] if grocery else PRODUCT_STORIES.get(key, tuple(SALES_STORIES)[fingerprint % len(SALES_STORIES)])
    story_label, series = SALES_STORIES[story_key]
    # Two complete four-week windows, scaled by category; the chart and signal
    # use exactly the same counts. No random values or external market claims.
    scale = {'home': 1, 'car': 2, 'electronics': 7}.get(product.kind, 10)
    if grocery:
        scale = 3 + fingerprint % 8
    values = [value * scale for value in series]
    previous, total = sum(values[:4]), sum(values[4:])
    trend = round((total / previous - 1) * 100, 1)
    state = 'up' if trend >= 10 else 'down' if trend <= -10 else 'steady'
    # Complete weeks ending on the most recent Sunday.
    today = timezone.localdate()
    end = today - timedelta(days=today.weekday() + 1)
    peak = max(values)
    peak_index = values.index(peak)
    fall_index = min(range(1, len(values)), key=lambda i: values[i] / values[i - 1])
    sharp_fall = values[fall_index] / values[fall_index - 1] <= .65
    weeks = []
    for offset, value in enumerate(values):
        last = end - timedelta(weeks=7 - offset)
        first = last - timedelta(days=6)
        weeks.append({'label': first.strftime('%d.%m'),
                      'period': f'{first:%d.%m}–{last:%d.%m}', 'count': value,
                      'height': round(value / peak * 100), 'current': offset >= 4,
                      'peak': sharp_fall and offset == peak_index,
                      'drop': sharp_fall and offset == fall_index})
    facts = compact_facts(product)
    if product.kind == 'home':
        rooms = 2 + index % 2
        facts = [('Комнаты', str(rooms)), ('Площадь', f'{64 + index * 3} м²'),
                 ('Расположение', ('Алматы · Бостандыкский', 'Астана · Есиль')[index % 2])]
    elif product.kind == 'electronics' and product.photo_key not in ('xiaomi-15-ultra', 'huawei-pura-80-ultra'):
        facts = [('Процессор', '8 ядер · пример'), ('Память', '256 ГБ'), ('ОЗУ', '8 ГБ')]
    elif product.kind == 'electronics' and product.photo_key == 'xiaomi-15-ultra':
        facts = [('Процессор', 'Snapdragon 8 Elite'), ('Память', '512 ГБ'), ('ОЗУ', '16 ГБ')]
    if product.kind == 'car' and product.photo_key not in ('jac-t8-pro', 'volkswagen-bora', 'volkswagen-passat'):
        facts = [('Двигатель', '2,0 л · пример'), ('Коробка', 'Автомат'), ('Пробег', '18 000 км')]
    price = {'home': 38400000 + index * 850000, 'car': 12500000 + index * 420000,
             'electronics': 249990 + index * 17000}.get(product.kind, 14900)
    if grocery:
        price = grocery['price']
    texts = DEMO_COMMENTS.get(product.kind, DEMO_COMMENTS['other'])
    ratings = {'up': [5, 5, 4, 5, 4, 5, 5, 4, 5, 5],
               'steady': [4, 3, 4, 4, 3, 3, 3, 4, 4, 3],
               'down': [2, 2, 3, 2, 1, 3, 2, 3, 2, 2]}[state]
    # Give all ten fictional participants a distinct line for the pitch.
    extras = {
        'up': ['По моим требованиям это один из самых интересных вариантов.',
               'Нравится сочетание внешнего вида и возможностей.',
               'После сравнения похожих предложений этот вариант остался первым.',
               'Рассматриваю всерьёз, осталось обсудить условия с продавцом.',
               'Сохранил, чтобы показать семье и выбрать вместе.'],
        'steady': ['Есть интересные стороны, но решение пока не принял.',
                   'Для меня всё зависит от итоговых условий.',
                   'Вернусь к этому варианту после сравнения.'],
        'down': ['За эту цену мне сложно решиться.',
                 'Пока не вижу причины менять то, чем пользуюсь сейчас.',
                 'Сначала посмотрю альтернативы в своём бюджете.',
                 'Не совсем подходит под мои повседневные задачи.',
                 'Подожду, сейчас покупка не в приоритете.'],
    }
    if state == 'up':
        selected_texts = texts[:5] + extras[state]
    elif state == 'steady':
        selected_texts = [texts[item] for item in [2, 5, 4, 3, 6, 7, 1]] + extras[state]
    else:
        selected_texts = [texts[item] for item in [8, 9, 6, 7, 5]] + extras[state]
    if product.kind == 'food' and state == 'down':
        selected_texts[-4:] = ['Дома пока хватает, дополнительная закупка не нужна.',
                              'Сначала сравню стоимость такой же фасовки в других магазинах.',
                              'Большую партию не возьму, начну с одной упаковки.',
                              'Подожду скидку, сейчас покупка не в приоритете.']
    comments = [{'name': name, 'initial': name[0], 'text': selected_texts[i],
                 'rating': ratings[i], 'stars': '★' * ratings[i] + '☆' * (5 - ratings[i]),
                 'day': f'{i + 1} дн. назад'} for i, name in enumerate(PEOPLE)]
    # Keep the property example consistent when the scripted review says two rooms.
    if product.kind == 'home' and facts[0][1] == '3':
        for comment in comments:
            comment['text'] = comment['text'].replace('две отдельные комнаты', 'три отдельные комнаты')
    return {'state': state, 'weeks': weeks, 'total': total, 'previous': previous,
            'trend': trend, 'trend_label': f'{trend:+.1f}%'.replace('.', ',') if trend else '0%',
            'facts': facts, 'price': price, 'comments': comments,
            'rating': round(sum(ratings) / len(ratings), 1), 'count': len(comments),
            'period': f'{weeks[4]["label"]} — {end:%d.%m}',
            'unit': grocery['unit'] if grocery else {'home': 'квартир', 'car': 'авто'}.get(product.kind, 'шт.'),
            'story': story_label, 'sharp_fall': sharp_fall,
            'fall_from': values[fall_index - 1], 'fall_to': values[fall_index],
            'fall_date': weeks[fall_index]['label']}


def product_presentation(product, insight, *, demo=False):
    sample = demo_scenario(product) if demo else None
    trend = sample['trend'] if sample else insight['trend']
    state = ('unknown' if trend is None else 'up' if trend >= 10 else 'down' if trend <= -10 else 'steady')
    signal = {'state': state, **SIGNALS[state]}
    brief = product.brief or {}
    pros, cons = brief.get('pros', []), brief.get('cons', [])
    if sample:
        positive = f'За последние 4 недели купили {sample["total"]} {sample["unit"]}'
        negative = 'Покупки за последние 4 недели сократились'
    else:
        positive = 'Продажи растут по истории продавца'
        negative = 'Продажи снижаются по истории продавца'
    if state == 'up':
        points = [{'symbol': '+', 'text': positive}, {'symbol': '+', 'text': pros[0] if pros else 'Текущий спрос выше предыдущего периода'}]
        heading = 'Почему стоит присмотреться'
    elif state == 'down':
        points = [{'symbol': '!', 'text': negative}, {'symbol': '!', 'text': cons[0] if cons else 'Стоит сравнить цену и условия с другими предложениями'}]
        heading = 'На что обратить внимание'
    elif state == 'steady':
        points = [{'symbol': '+', 'text': pros[0] if pros else 'Продажи держатся на прежнем уровне'},
                  {'symbol': '!', 'text': cons[0] if cons else 'Сравните цену и условия перед выбором'}]
        heading = 'Коротко о выборе'
    else:
        points = [{'symbol': '+', 'text': pros[0]}] if pros else []
        heading = 'Что может понравиться'
    short_descriptions = {
        'home': 'Квартира для жизни. Главное — планировка, площадь и район.',
        'car': 'Для ежедневных поездок. Сравните двигатель, оснащение и расходы.',
        'electronics': 'Для связи, фото и повседневных задач.',
    }
    facts = sample['facts'] if sample else compact_facts(product)
    if product.kind == 'home':
        preview = f'{facts[0][1]} комн. · {facts[1][1]}' if sample else 'Квартира · параметры уточняются'
    elif product.kind == 'electronics':
        if product.photo_key == 'xiaomi-15-ultra':
            preview = 'Snapdragon 8 Elite · 6,73″'
        elif sample or product.photo_key == 'huawei-pura-80-ultra':
            preview = f'{facts[1][1]} · ОЗУ {facts[2][1]}'
        else:
            preview = 'Модель и память уточняются'
    elif product.kind == 'car':
        preview = ' · '.join(value for _, value in facts[:2] if value != 'Уточняется') or 'Комплектация уточняется'
    elif product.demo_key in GROCERY_BY_KEY:
        preview = ' · '.join(value for _, value in facts[:2])
    else:
        preview = product.get_kind_display()
    seller = product.seller
    seller_name = (seller.get_full_name() or seller.username) if seller else ''
    if seller and brief.get('demo_shop'):
        seller_name = f'{seller.first_name} · {brief["demo_shop"]}'
    return {'signal': signal, 'demo': sample, 'facts': facts, 'preview': preview,
            'title': demo_title(product) if demo else product.title,
            'seller_name': seller_name, 'demo_seller': bool(brief.get('demo_shop')),
            'price': sample['price'] if sample else product.price,
            'summary': short_descriptions.get(product.kind, product.description[:140]),
            'points': points, 'points_heading': heading}
