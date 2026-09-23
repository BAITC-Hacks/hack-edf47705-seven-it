from django import forms

from .csv_import import CsvImportError, parse_csv
from .models import Business

MAX_FILE_SIZE = 5 * 1024 * 1024


class UploadForm(forms.ModelForm):
    file = forms.FileField(
        label='Файл Excel или CSV',
        help_text='Колонки: дата, категория, количество. Подойдёт выгрузка из кассы, 1С или Excel.',
        widget=forms.FileInput(attrs={'accept': '.csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}),
    )

    class Meta:
        model = Business
        fields = ['name', 'business_type', 'region', 'lead_time_weeks']
        labels = {
            'name': 'Название бизнеса',
            'business_type': 'Чем вы занимаетесь?',
            'region': 'Город или регион',
            'lead_time_weeks': 'Доставка или подготовка, недель',
        }
        help_texts = {
            'lead_time_weeks': 'Сколько времени нужно, чтобы пополнить запас.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Например, «Автозапчасти на Абая»'}),
            'region': forms.TextInput(attrs={'placeholder': 'Например, Алматы'}),
            'lead_time_weeks': forms.NumberInput(attrs={'min': 0, 'max': 52}),
        }

    def clean_lead_time_weeks(self):
        value = self.cleaned_data['lead_time_weeks']
        if value > 52:
            raise forms.ValidationError('Не больше 52 недель.')
        return value

    def clean_file(self):
        upload = self.cleaned_data['file']
        if upload.size > MAX_FILE_SIZE:
            raise forms.ValidationError('Файл больше 5 МБ.')
        try:
            if upload.name.lower().endswith('.xlsx'):
                from market.excel import parse_sales_xlsx
                self.parsed = parse_sales_xlsx(upload.read())
            elif upload.name.lower().endswith('.csv'):
                self.parsed = parse_csv(upload.read())
            else:
                raise CsvImportError('Выберите файл .xlsx или .csv.')
        except CsvImportError as error:
            raise forms.ValidationError(str(error)) from None
        return upload
