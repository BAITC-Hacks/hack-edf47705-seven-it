from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    class Role(models.TextChoices):
        BUYER = 'buyer', 'Покупатель'
        SELLER = 'seller', 'Продавец'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='market_profile')
    role = models.CharField('Роль', max_length=10, choices=Role.choices, default=Role.BUYER)

    def __str__(self):
        return f'{self.user} — {self.get_role_display()}'


class Product(models.Model):
    class Kind(models.TextChoices):
        HOME = 'home', 'Недвижимость'
        CAR = 'car', 'Автомобили'
        FOOD = 'food', 'Продукты'
        GOODS = 'goods', 'Товары и опт'
        ELECTRONICS = 'electronics', 'Электроника'

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='products', verbose_name='Продавец')
    title = models.CharField('Название', max_length=160)
    kind = models.CharField('Категория', max_length=12, choices=Kind.choices)
    description = models.TextField('Описание', max_length=5000)
    region = models.CharField('Город или регион', max_length=100)
    price = models.DecimalField('Цена за единицу, ₸', max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.PositiveIntegerField('Остаток, единиц', null=True, blank=True, validators=[MaxValueValidator(10000000)])
    unit = models.CharField('Единица измерения', max_length=20, default='шт.')
    lead_days = models.PositiveSmallIntegerField('Срок пополнения, дней', default=7, validators=[MaxValueValidator(365)])
    is_published = models.BooleanField('Опубликован', default=True)
    is_demo = models.BooleanField('Демонстрационный пример', default=False)
    demo_key = models.CharField(max_length=40, unique=True, null=True, blank=True, editable=False)
    is_reference = models.BooleanField('Обзорная карточка', default=False)
    photo_key = models.CharField(max_length=60, unique=True, null=True, blank=True, editable=False)
    image_path = models.CharField('Фото из каталога', max_length=250, blank=True,
        validators=[RegexValidator(r'^catalog-photos/[a-z0-9-]+\.jpg$', 'Укажите файл catalog-photos/имя.jpg.')])
    brief = models.JSONField('Характеристики и разбор', default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Товар или объект'
        verbose_name_plural = 'Товары и объекты'
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name='market_positive_price')]

    def __str__(self):
        return self.title


class Observation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='observations')
    date = models.DateField('Дата', default=timezone.localdate)
    price = models.DecimalField('Цена за единицу, ₸', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    sold = models.PositiveIntegerField('Продано за день', default=0, validators=[MaxValueValidator(10000000)])

    class Meta:
        ordering = ['date']
        constraints = [
            models.UniqueConstraint(fields=['product', 'date'], name='market_one_observation_daily'),
            models.CheckConstraint(condition=models.Q(price__gt=0), name='market_observation_positive_price'),
        ]
        verbose_name = 'День продаж'
        verbose_name_plural = 'История цен и продаж'


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField('Оценка', validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField('Ваш опыт использования', max_length=2000)
    is_hidden = models.BooleanField('Скрыт модератором', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['product', 'author'], name='market_one_review_per_user'),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='market_valid_rating'),
        ]
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorites')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='market_unique_favorite')]


class LedgerEntry(models.Model):
    class Direction(models.TextChoices):
        INCOME = 'income', 'Доход'
        EXPENSE = 'expense', 'Расход'

    CATEGORIES = [('sales', 'Продажи'), ('purchase', 'Покупки'), ('advertising', 'Реклама'),
                  ('delivery', 'Доставка'), ('rent', 'Аренда'), ('salary', 'Зарплата'), ('other', 'Другое')]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ledger_entries')
    date = models.DateField('Дата', default=timezone.localdate)
    direction = models.CharField('Тип операции', max_length=10, choices=Direction.choices)
    amount = models.DecimalField('Сумма, ₸', max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    category = models.CharField('Категория', max_length=20, choices=CATEGORIES, default='other')
    note = models.CharField('Описание', max_length=250)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='market_positive_amount')]
        verbose_name = 'Денежная операция'
        verbose_name_plural = 'Доходы и расходы'


class SupportMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_messages')
    role = models.CharField(max_length=10, choices=[('user', 'Пользователь'), ('assistant', 'Помощник')])
    content = models.TextField(max_length=6000)
    source = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
