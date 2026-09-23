from django.db import models
from django.conf import settings


class Business(models.Model):
    """A business that uploads its own history to get demand forecasts."""

    TYPE_RETAIL = 'retail'
    TYPE_SERVICES = 'services'
    TYPE_CHOICES = [
        (TYPE_RETAIL, 'Торговля (продажи товаров)'),
        (TYPE_SERVICES, 'Услуги (записи клиентов)'),
    ]

    name = models.CharField('Название', max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='businesses', verbose_name='Владелец')
    business_type = models.CharField('Тип бизнеса', max_length=20, choices=TYPE_CHOICES, default=TYPE_RETAIL)
    region = models.CharField('Регион', max_length=100)
    lead_time_weeks = models.PositiveSmallIntegerField(
        'Срок подготовки, недель',
        default=3,
        help_text='Сколько недель занимает поставка товара или подготовка смен.',
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Бизнес-профиль'
        verbose_name_plural = 'Бизнес-профили'

    def __str__(self):
        return f'{self.name} ({self.region})'


class Dataset(models.Model):
    """One uploaded history file (sales or bookings) and its cached recommendations."""

    SOURCE_AI = 'ai'
    SOURCE_RULES = 'rules'
    SOURCE_CHOICES = [(SOURCE_AI, 'ИИ (Claude)'), (SOURCE_RULES, 'Правила')]

    business = models.ForeignKey(Business, verbose_name='Бизнес-профиль', on_delete=models.CASCADE, related_name='datasets')
    name = models.CharField('Название', max_length=200)
    is_demo = models.BooleanField('Открытый демонстрационный набор', default=False)
    created_at = models.DateTimeField('Дата загрузки', auto_now_add=True)
    recommendations = models.JSONField('Рекомендации', default=dict, blank=True)
    recommendations_source = models.CharField('Источник рекомендаций', max_length=10, choices=SOURCE_CHOICES, blank=True)
    recommendations_note = models.CharField('Примечание', max_length=300, blank=True)
    recommendations_at = models.DateTimeField('Дата расчёта рекомендаций', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Набор данных'
        verbose_name_plural = 'Наборы данных и рекомендации'

    def __str__(self):
        return self.name


class Record(models.Model):
    """One observation: how many units were sold (or bookings made) in a category on a date."""

    dataset = models.ForeignKey(Dataset, verbose_name='Набор данных', on_delete=models.CASCADE, related_name='records')
    date = models.DateField('Дата')
    category = models.CharField('Категория', max_length=120)
    quantity = models.FloatField('Количество')

    class Meta:
        indexes = [models.Index(fields=['dataset', 'category', 'date'])]
        verbose_name = 'Запись продаж или бронирований'
        verbose_name_plural = 'История продаж и бронирований'

    def __str__(self):
        return f'{self.category} — {self.date}'
