import csv
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.utils import timezone

from forecast.csv_import import CsvImportError, _parse_date
from .excel import xlsx_rows


def parse_product_history(upload):
    if upload.size > 5 * 1024 * 1024:
        raise CsvImportError('Файл больше 5 МБ.')
    raw = upload.read()
    if upload.name.lower().endswith('.xlsx'):
        rows = iter(xlsx_rows(raw))
    elif upload.name.lower().endswith('.csv'):
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp1251')
        first = text.split('\n', 1)[0]
        rows = csv.reader(StringIO(text), delimiter=max(',;\t', key=first.count))
    else:
        raise CsvImportError('Поддерживаются файлы .xlsx и .csv.')
    header = [str(value).strip().lower() for value in next(rows, [])]
    aliases = {'date': ('date', 'дата'), 'price': ('price', 'цена', 'цена, kzt'), 'sold': ('sold', 'продано', 'количество')}
    positions = {key: next((i for i, value in enumerate(header) if value in names), None) for key, names in aliases.items()}
    if any(value is None for value in positions.values()):
        raise CsvImportError('Нужны колонки «дата», «цена», «продано» (date, price, sold).')
    result, seen = [], set()
    for line, row in enumerate(rows, start=2):
        if not any(str(value).strip() for value in row):
            continue
        if len(result) >= 2000:
            raise CsvImportError('Не больше 2000 дней в одном файле.')
        try:
            day = _parse_date(str(row[positions['date']]))
            price = Decimal(str(row[positions['price']]).replace(' ', '').replace(',', '.'))
            sold = Decimal(str(row[positions['sold']]).replace(' ', '').replace(',', '.'))
            if day > timezone.localdate():
                raise ValueError('дата в будущем')
            if day in seen:
                raise ValueError('дата повторяется в файле')
            if not price.is_finite() or price <= 0 or price >= Decimal('1000000000000') or price != price.quantize(Decimal('.01')):
                raise ValueError('некорректная цена, максимум 2 знака после запятой')
            if not sold.is_finite() or sold < 0 or sold > 10000000 or sold != int(sold):
                raise ValueError('число продаж должно быть целым и неотрицательным')
            seen.add(day)
            result.append((day, price, int(sold)))
        except (ValueError, InvalidOperation, IndexError, OverflowError) as error:
            raise CsvImportError(f'Строка {line}: {error}. Файл не сохранён.') from error
    if not result:
        raise CsvImportError('В файле нет данных.')
    return result
