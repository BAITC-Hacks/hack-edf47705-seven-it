from concurrent.futures import ThreadPoolExecutor
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from market.grocery_catalog import (
    DEMO_SELLER_NAME, DEMO_SELLER_USERNAME, DEMO_SHOP_NAME, GROCERIES, PHOTO_LICENSE,
)
from market.models import Product, Profile


class Command(BaseCommand):
    help = 'Добавляет 10 демо-продуктов магазина и отдельного вымышленного продавца.'

    def add_arguments(self, parser):
        parser.add_argument('--download-images', action='store_true',
                            help='Скачать отсутствующие фотографии из указанных источников Pexels.')

    def image_file(self, item):
        return settings.BASE_DIR / 'photo' / 'catalog' / (item['key'] + '.jpg')

    def download_image(self, item):
        path = self.image_file(item)
        if path.is_file():
            return
        request = Request(item['image_url'], headers={'User-Agent': 'Foresell-Demo/1.0'})
        try:
            with urlopen(request, timeout=35) as response:
                data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024 or not data.startswith(b'\xff\xd8\xff') or not data.endswith(b'\xff\xd9'):
                raise CommandError(f'Вместо JPEG получен неподходящий файл: {item["key"]}')
            path.write_bytes(data)
        except (URLError, OSError) as exc:
            raise CommandError(f'Не удалось скачать {item["key"]}: {exc}') from exc

    def handle(self, *args, **options):
        if options['download_images']:
            self.image_file(GROCERIES[0]).parent.mkdir(parents=True, exist_ok=True)
            with ThreadPoolExecutor(max_workers=4) as pool:
                # Consume every result so network failures cannot be hidden.
                list(pool.map(self.download_image, GROCERIES))
        for item in GROCERIES:
            path = self.image_file(item)
            if not path.is_file() or not path.read_bytes().startswith(b'\xff\xd8\xff'):
                raise CommandError(f'Нет корректного фото {path.name}. Добавьте --download-images.')
        with transaction.atomic():
            User = get_user_model()
            seller, created = User.objects.get_or_create(username=DEMO_SELLER_USERNAME, defaults={
                'first_name': DEMO_SELLER_NAME, 'last_name': DEMO_SHOP_NAME,
                'is_active': False, 'is_staff': False,
            })
            if created:
                seller.set_unusable_password()
                seller.save(update_fields=['password'])
                Profile.objects.create(user=seller, role=Profile.Role.SELLER)
            elif seller.is_active or seller.has_usable_password() or seller.is_staff or seller.is_superuser or seller.first_name != DEMO_SELLER_NAME or seller.last_name != DEMO_SHOP_NAME:
                raise CommandError('Имя демо-продавца занято другим аккаунтом. Его данные не изменены.')
            count = 0
            for item in GROCERIES:
                brief = {
                    'specifications': item['specifications'], 'pros': item['pros'], 'cons': item['cons'],
                    'identification': 'Демонстрационное предложение. Фото иллюстрирует вид продукта; фасовка и цена вымышлены.',
                    'verdict': 'Сравните фасовку, состав и цену. Диаграмма показывает вымышленную историю покупок.',
                    'basis': 'Фото из Pexels; продавец, предложение и история спроса созданы для презентации.',
                    'reviewed_at': '23.09.2026', 'demo_shop': DEMO_SHOP_NAME,
                    'sources': [{'title': f'Фото: {item["photographer"]} / Pexels', 'url': item['photo_url']},
                                {'title': 'Условия использования фото Pexels', 'url': PHOTO_LICENSE}],
                }
                product, added = Product.objects.get_or_create(demo_key=item['key'], defaults={
                    'seller': seller, 'title': item['title'], 'kind': Product.Kind.FOOD,
                    'description': item['description'], 'region': 'Алматы',
                    'price': item['price'], 'stock': item['stock'], 'unit': item['unit'],
                    'lead_days': 2, 'is_demo': True, 'is_published': True,
                    'image_path': 'catalog-photos/' + item['key'] + '.jpg', 'brief': brief,
                })
                if added:
                    product.full_clean()
                    count += 1
                elif not product.is_demo or product.seller_id != seller.pk:
                    raise CommandError(f'Ключ {item["key"]} занят другим товаром. Запись не изменена.')
                elif product.brief.get('sources') != brief['sources']:
                    # Keep attribution current without replacing edited offer details.
                    product.brief = {**product.brief, 'sources': brief['sources']}
                    product.save(update_fields=['brief'])
        self.stdout.write(self.style.SUCCESS(f'Добавлено продуктов: {count}. Уже были: {len(GROCERIES) - count}. Продавец: {DEMO_SELLER_NAME} · {DEMO_SHOP_NAME} (демо).'))
