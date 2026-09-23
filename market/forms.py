from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import LedgerEntry, Observation, Product, Profile, Review
from .imports import parse_product_history
from forecast.csv_import import CsvImportError


class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(label='Я хочу пользоваться как', choices=Profile.Role.choices)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ['username', 'role']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'kind', 'description', 'region', 'price', 'stock', 'unit', 'lead_days', 'is_published']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}
        help_texts = {'stock': 'Оставьте пустым, если остаток неизвестен.',
                      'price': 'Все суммы в тенге. Для опта укажите цену одной выбранной единицы.'}


class ObservationForm(forms.ModelForm):
    class Meta:
        model = Observation
        fields = ['date', 'price', 'sold']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}
        help_texts = {'sold': 'Укажите 0, если продаж не было. Пропущенный день не считается нулевым.'}

    def clean_date(self):
        day = self.cleaned_data['date']
        if day > timezone.localdate():
            raise forms.ValidationError('Укажите сегодняшний или прошедший день.')
        return day


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(label='Оценка', choices=[(i, f'{i} из 5') for i in range(5, 0, -1)], coerce=int)

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Что понравилось? Какие недостатки вы заметили?'})}


class LedgerForm(forms.ModelForm):
    class Meta:
        model = LedgerEntry
        fields = ['direction', 'amount', 'date', 'category', 'note']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def clean_date(self):
        if self.cleaned_data['date'] > timezone.localdate():
            raise forms.ValidationError('Здесь учитываются уже совершённые операции.')
        return self.cleaned_data['date']


class DateRangeForm(forms.Form):
    start = forms.DateField(label='С', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(label='По', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError('Начало периода должно быть раньше окончания.')
        return data


class SupportForm(forms.Form):
    message = forms.CharField(label='Ваш вопрос', max_length=1200, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Например: как понять, хватит ли запасов?'}))


class HistoryImportForm(forms.Form):
    file = forms.FileField(label='Excel или CSV', widget=forms.FileInput(attrs={'accept': '.xlsx,.csv'}),
        help_text='Первый лист: дата, цена, продано. До 5 МБ и 2000 дней. Даты, которые уже есть в истории, будут обновлены.')

    def clean_file(self):
        upload = self.cleaned_data['file']
        try:
            self.rows = parse_product_history(upload)
        except CsvImportError as error:
            raise forms.ValidationError(str(error)) from None
        return upload
