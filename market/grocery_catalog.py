"""Fictional grocery offers with credited, locally stored Pexels photographs."""

DEMO_SELLER_USERNAME = 'foresell_demo_ainala'
DEMO_SELLER_NAME = 'Алихан'
DEMO_SHOP_NAME = 'Ainala Market'
PHOTO_LICENSE = 'https://www.pexels.com/license/'


def grocery(key, title, description, amount, category, price, stock, photo_id,
            photo_slug, photographer, story, plus, caution, *, unit='уп.', form='Упаковка'):
    return {
        'key': 'grocery-' + key, 'title': title, 'description': description,
        'specifications': {'Фасовка': amount, 'Категория': category, 'Формат': form},
        'price': price, 'stock': stock, 'unit': unit, 'story': story,
        'pros': [plus, 'Можно добавить к обычной продуктовой корзине.'],
        'cons': [caution, 'Состав и срок годности уточняются по этикетке конкретной упаковки.'],
        'photo_url': f'https://www.pexels.com/photo/{photo_slug}-{photo_id}/',
        'image_url': f'https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?fm=jpg&w=1000&q=85',
        'photographer': photographer,
    }


GROCERIES = [
    grocery('milk', 'Молоко · 1 л', 'Молоко для каши, кофе и домашней выпечки.',
            '1 л', 'Молочные продукты', 620, 85, 14127931,
            'bottle-and-glasses-on-white-background', 'Ann H', 'quiet',
            'Удобный объём для завтраков и готовки.', 'Важно соблюдать условия хранения на упаковке.'),
    grocery('bread', 'Хлеб пшеничный · 500 г', 'Пшеничный хлеб для тостов, бутербродов и семейного стола.',
            '500 г', 'Хлеб и выпечка', 480, 42, 10075983,
            'loaf-of-bread', 'Noemí Jiménez', 'surge',
            'Подойдёт и к завтраку, и к основному блюду.', 'Большой запас хлеба может остаться невостребованным.', unit='шт.'),
    grocery('eggs', 'Яйца куриные · 6 шт.', 'Небольшая упаковка яиц для завтраков и выпечки.',
            '6 шт.', 'Яйца', 690, 64, 6294168,
            'set-of-chicken-eggs-in-carton-box', 'Klaus Nielsen', 'peak_drop',
            'Небольшую упаковку удобно брать для одного-двух человек.', 'Перед покупкой нужно осмотреть целостность скорлупы.'),
    grocery('apples', 'Яблоки красные · 1 кг', 'Яблоки для перекуса, компота и домашнего пирога.',
            '1 кг', 'Фрукты', 890, 120, 7333128,
            'ripe-red-apples-in-bowl-on-white-background', 'Evgeniy Alekseyev', 'rebound',
            'Можно есть отдельно или использовать в готовке.', 'Сорт и степень зрелости могут отличаться от фотографии.', unit='кг', form='На развес'),
    grocery('bananas', 'Бананы · 1 кг', 'Бананы для перекуса, каши и смузи.',
            '1 кг', 'Фрукты', 1150, 95, 2116020,
            'ripe-bananas', 'Renata Brant', 'launch',
            'Удобный перекус, который легко взять с собой.', 'Зрелые плоды не стоит закупать слишком большим запасом.', unit='кг', form='На развес'),
    grocery('tomatoes', 'Помидоры · 1 кг', 'Помидоры для салатов, соусов и горячих блюд.',
            '1 кг', 'Овощи', 1090, 76, 6060902,
            'close-up-shot-of-fresh-tomatoes', 'Andre Taissin', 'flash_drop',
            'Один продукт для свежих салатов и горячих блюд.', 'Крупную закупку стоит соотнести с темпом продаж.', unit='кг', form='На развес'),
    grocery('rice', 'Рис белый · 900 г', 'Белый рис для гарниров и повседневных блюд.',
            '900 г', 'Крупы', 940, 150, 8108170,
            'uncooked-rice-on-white-surface', 'MART PRODUCTION', 'plateau',
            'Универсальная основа для разных гарниров.', 'Время приготовления зависит от сорта и указаний на упаковке.'),
    grocery('pasta', 'Макароны «Бантики» · 500 г', 'Фигурные макароны для гарнира, салата или блюда с соусом.',
            '500 г', 'Макароны', 650, 180, 6287549,
            'pack-of-dry-raw-farfalle-pasta-placed-on-table', 'Klaus Nielsen', 'slowdown',
            'Форма «бантики» подходит для соусов и салатов.', 'Состав конкретной упаковки нужно уточнить перед выбором.'),
    grocery('cheese', 'Сыр с голубой плесенью · 200 г', 'Сыр для сырной тарелки, соуса или небольшого перекуса.',
            '200 г', 'Сыры', 1890, 35, 4187780,
            'cheese-in-close-up-photography', 'Polina Tankilevitch', 'quiet',
            'Можно использовать небольшими порциями в разных блюдах.', 'Выраженный вкус подходит не всем.'),
    grocery('yogurt', 'Йогурт натуральный · 150 г', 'Порционный йогурт для завтрака, фруктов и мюсли.',
            '150 г', 'Молочные продукты', 390, 110, 4428349,
            'jar-with-delicious-plain-yogurt-and-wooden-spoon-on-saucer', 'Cats Coming', 'rebound',
            'Небольшая порция удобна для одного завтрака.', 'Проверьте состав и срок годности на этикетке.'),
]

GROCERY_BY_KEY = {item['key']: item for item in GROCERIES}
