from django.db import models


class Business(models.Model):
    """A business that uploads its own history to get demand forecasts."""

    TYPE_RETAIL = 'retail'
    TYPE_SERVICES = 'services'
    TYPE_CHOICES = [
        (TYPE_RETAIL, 'Торговля (продажи товаров)'),
        (TYPE_SERVICES, 'Услуги (записи клиентов)'),
    ]

    name = models.CharField('Название', max_length=200)
    business_type = models.CharField('Тип бизнеса', max_length=20, choices=TYPE_CHOICES, default=TYPE_RETAIL)
    region = models.CharField('Регион', max_length=100)
    lead_time_weeks = models.PositiveSmallIntegerField(
        'Срок подготовки, недель',
        default=3,
        help_text='Сколько недель занимает поставка товара или подготовка смен.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.region})'


class Dataset(models.Model):
    """One uploaded history file (sales or bookings) and its cached recommendations."""

    SOURCE_AI = 'ai'
    SOURCE_RULES = 'rules'
    SOURCE_CHOICES = [(SOURCE_AI, 'ИИ (Claude)'), (SOURCE_RULES, 'Правила')]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='datasets')
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    recommendations = models.JSONField(default=dict, blank=True)
    recommendations_source = models.CharField(max_length=10, choices=SOURCE_CHOICES, blank=True)
    recommendations_note = models.CharField(max_length=300, blank=True)
    recommendations_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Record(models.Model):
    """One observation: how many units were sold (or bookings made) in a category on a date."""

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='records')
    date = models.DateField()
    category = models.CharField(max_length=120)
    quantity = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=['dataset', 'category', 'date'])]
