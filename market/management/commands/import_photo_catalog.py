from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from market.models import Product
from market.photo_catalog import PHOTO_PRODUCTS


class Command(BaseCommand):
    help = 'Добавляет обзорные карточки из photo/catalog без вымышленных цен, продаж или отзывов.'

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        for item in PHOTO_PRODUCTS:
            image_path = settings.BASE_DIR / 'photo' / 'catalog' / item['image']
            if not image_path.is_file() or image_path.read_bytes()[:3] != b'\xff\xd8\xff':
                raise CommandError(f'Отсутствует или повреждено фото: {image_path.name}')
            brief = {key: value for key, value in item.items()
                     if key not in ('key', 'title', 'kind', 'description', 'image')}
            product, created = Product.objects.get_or_create(photo_key=item['key'], defaults={
                'title': item['title'], 'kind': item['kind'], 'description': item['description'],
                'region': 'Не указан', 'price': None, 'stock': None,
                'unit': 'объект' if item['kind'] == 'home' else 'авто' if item['kind'] == 'car' else 'шт.',
                'image_path': 'catalog-photos/' + item['image'], 'is_reference': True, 'brief': brief,
            })
            if created:
                product.full_clean()
                created_count += 1
        self.stdout.write(self.style.SUCCESS(
            f'Добавлено карточек: {created_count}. Уже существовали: {len(PHOTO_PRODUCTS) - created_count}.'))
