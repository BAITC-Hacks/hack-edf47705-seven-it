from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from market.models import Observation, Product


class Command(BaseCommand):
    help = 'Добавляет помеченные демонстрационные товары и синтетическую историю. Без пользовательских аккаунтов.'

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        samples = [
            ('apartments', 'ЖК «Самал» · двухкомнатные квартиры', 'home', 'Алматы', 38000000, 8, 'квартира', 90,
             'Вымышленный жилой комплекс для демонстрации истории цен. Данные не относятся к реальному объекту недвижимости.', 9000, 1),
            ('crossover', 'Кроссовер Terra X · 2025', 'car', 'Астана', 12500000, 12, 'авто', 30,
             'Вымышленная модель автомобиля. Пример карточки продавца с историей продаж и остатками.', 2500, 1),
            ('coffee', 'Кофе в зерне · оптовая упаковка', 'food', 'Алматы', 6800, 140, 'кг', 7,
             'Синтетический пример оптового продукта. У реального товара продавец должен указать состав, сроки годности и условия хранения.', 5, 13),
            ('rice', 'Рис · мешок 25 кг', 'food', 'Шымкент', 12900, 250, 'мешок', 5,
             'Пример товара со стабильной ценой и спросом. Все цифры демонстрационные.', 0, 7),
            ('paper', 'Бумага А4 · коробка 5 пачек', 'goods', 'Астана', 9900, 80, 'коробка', 10,
             'Пример оптового товара с растущим спросом. Показывает расчёт остатка и срок пополнения.', 7, 10),
            ('sedan', 'Седан City S · 2024', 'car', 'Караганда', 8900000, 20, 'авто', 21,
             'Вымышленный автомобиль. Пример снижения цены; модель не оценивает техническое состояние.', -1800, 2),
        ]
        created_count = 0
        for key, title, kind, region, price, stock, unit, lead, description, slope, daily in samples:
            product, created = Product.objects.get_or_create(demo_key=key, defaults={
                'title': title, 'kind': kind, 'region': region, 'price': price, 'stock': stock,
                'unit': unit, 'lead_days': lead, 'description': description, 'is_demo': True,
            })
            if not created:
                continue
            created_count += 1
            history = []
            for ago in range(59, -1, -1):
                sold = daily + (daily // 2 + 1 if ago < 30 and slope > 0 else 0)
                if kind in ('car', 'home'):
                    sold = sold if ago % 3 == 0 else 0
                history.append(Observation(product=product, date=today - timedelta(days=ago),
                    price=Decimal(price - slope * ago), sold=sold))
            Observation.objects.bulk_create(history)
        self.stdout.write(self.style.SUCCESS(f'Создано демонстрационных карточек: {created_count}.'))
