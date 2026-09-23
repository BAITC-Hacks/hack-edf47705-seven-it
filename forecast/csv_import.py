"""Parse a sales / bookings history CSV exported from a till, 1C or Excel."""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

MAX_ROWS = 200_000
MAX_SKIPPED_SHARE = 0.2
MAX_REPORTED_ERRORS = 10

COLUMN_ALIASES = {
    'date': {'date', 'day', 'дата', 'день'},
    'category': {'category', 'product', 'service', 'item', 'категория', 'товар', 'услуга', 'группа'},
    'quantity': {
        'quantity', 'qty', 'sales', 'bookings', 'count',
        'количество', 'кол-во', 'продажи', 'записи', 'шт',
    },
}
COLUMN_NAMES_RU = {'date': 'дата', 'category': 'категория', 'quantity': 'количество'}
DATE_FORMATS = ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d.%m.%y')


class CsvImportError(ValueError):
    pass


@dataclass
class ParseResult:
    rows: list[tuple[date, str, float]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    skipped_count: int = 0


def _decode(data: bytes) -> str:
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1251')


def _parse_date(value: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f'не распознана дата «{value}»')


def _parse_quantity(value: str) -> float:
    cleaned = value.strip().replace(' ', '').replace(' ', '').replace(',', '.')
    try:
        quantity = float(cleaned)
    except ValueError:
        raise ValueError(f'не число «{value}»') from None
    if quantity < 0:
        raise ValueError('отрицательное количество')
    return quantity


def _find_columns(header):
    normalized = [h.strip().lower() for h in header]
    positions = {}
    for key, aliases in COLUMN_ALIASES.items():
        for i, name in enumerate(normalized):
            if name in aliases:
                positions[key] = i
                break
    missing = [COLUMN_NAMES_RU[k] for k in COLUMN_ALIASES if k not in positions]
    if missing:
        raise CsvImportError(
            'В файле нет колонок: ' + ', '.join(missing)
            + '. Нужны колонки «дата», «категория», «количество» (или date, category, quantity).'
        )
    return positions


def parse_csv(data: bytes) -> ParseResult:
    text = _decode(data)
    first_line = text.split('\n', 1)[0]
    delimiter = max(',;\t', key=first_line.count)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    header = next(reader, None)
    if not header:
        raise CsvImportError('Файл пустой.')
    columns = _find_columns(header)

    result = ParseResult()
    total = 0
    for line_number, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        total += 1
        if total > MAX_ROWS:
            raise CsvImportError(f'Слишком большой файл: больше {MAX_ROWS} строк.')
        try:
            if len(row) <= max(columns.values()):
                raise ValueError('не хватает значений')
            category = row[columns['category']].strip()
            if not category:
                raise ValueError('пустая категория')
            result.rows.append((
                _parse_date(row[columns['date']]),
                category,
                _parse_quantity(row[columns['quantity']]),
            ))
        except ValueError as error:
            result.skipped_count += 1
            if len(result.skipped) < MAX_REPORTED_ERRORS:
                result.skipped.append(f'строка {line_number}: {error}')

    if not result.rows:
        raise CsvImportError('В файле нет ни одной корректной строки с данными.')
    if result.skipped_count / total > MAX_SKIPPED_SHARE:
        raise CsvImportError(
            f'Слишком много ошибок: {result.skipped_count} из {total} строк не распознаны. '
            'Например, ' + '; '.join(result.skipped[:3]) + '.'
        )
    return result
