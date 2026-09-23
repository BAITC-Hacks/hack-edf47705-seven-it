from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .excel import workbook_bytes
from .forms import DateRangeForm, HistoryImportForm, LedgerForm, ObservationForm, ProductForm, RegistrationForm, ReviewForm, SupportForm
from .insights import product_insights
from .models import Favorite, LedgerEntry, Observation, Product, Profile, Review, SupportMessage
from .support import FAQ, support_answer


def is_seller(user):
    return user.is_authenticated and (user.is_staff or Profile.objects.filter(user=user, role=Profile.Role.SELLER).exists())


def product_query():
    return Product.objects.select_related('seller').prefetch_related('observations', 'reviews')


def visible_products(user):
    query = product_query()
    return query.filter(Q(is_published=True) | Q(seller=user)) if user.is_authenticated else query.filter(is_published=True)


def register(request):
    if request.user.is_authenticated:
        return redirect('market:catalog')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Profile.objects.create(user=user, role=form.cleaned_data['role'])
        login(request, user)
        messages.success(request, 'Аккаунт создан. Добро пожаловать в Foresell!')
        return redirect('market:catalog')
    return render(request, 'market/form.html', {'form': form, 'title': 'Создать аккаунт', 'submit_label': 'Зарегистрироваться'})


def catalog_query(request):
    query = product_query().filter(is_published=True)
    search = request.GET.get('q', '').strip()[:160]
    kind = request.GET.get('kind', '')
    region = request.GET.get('region', '').strip()[:100]
    if search:
        query = query.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if kind in Product.Kind.values:
        query = query.filter(kind=kind)
    if region:
        query = query.filter(region__icontains=region)
    sort = request.GET.get('sort', '')
    if sort == 'price':
        query = query.order_by('price', 'pk')
    elif sort == 'rating':
        query = query.annotate(average_rating=Avg('reviews__rating', filter=Q(reviews__is_hidden=False))).order_by('-average_rating', '-pk')
    elif sort == 'interest':
        query = query.annotate(interest=Count('favorites', distinct=True)).order_by('-interest', '-pk')
    if request.GET.get('saved') and request.user.is_authenticated:
        query = query.filter(favorites__user=request.user)
    return query


def catalog(request):
    page = Paginator(catalog_query(request), 12).get_page(request.GET.get('page'))
    cards = [{'product': product, 'insight': product_insights(product)} for product in page]
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'market/catalog.html', {'cards': cards, 'page': page, 'kinds': Product.Kind.choices,
        'is_seller': is_seller(request.user), 'filters': request.GET, 'pagination_query': params.urlencode()})


def product_detail(request, pk):
    product = get_object_or_404(visible_products(request.user), pk=pk)
    existing = Review.objects.filter(product=product, author=request.user).first() if request.user.is_authenticated else None
    form = ReviewForm(request.POST or None, instance=existing)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('market:login')
        if product.seller_id == request.user.pk:
            raise PermissionDenied('Продавец не может оценивать свой товар.')
        if form.is_valid():
            Review.objects.update_or_create(product=product, author=request.user,
                defaults={'rating': form.cleaned_data['rating'], 'comment': form.cleaned_data['comment']})
            messages.success(request, 'Ваш отзыв сохранён.')
            return redirect('market:product', pk=pk)
    return render(request, 'market/product.html', {'product': product, 'insight': product_insights(product),
        'reviews': product.reviews.filter(is_hidden=False).select_related('author'), 'review_form': form,
        'favorite': request.user.is_authenticated and Favorite.objects.filter(user=request.user, product=product).exists(),
        'is_owner': request.user.is_authenticated and product.seller_id == request.user.pk,
        'observations': product.observations.order_by('-date')[:60]})


@login_required
@require_POST
def favorite(request, pk):
    product = get_object_or_404(Product, pk=pk, is_published=True)
    item, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
    return redirect('market:product', pk=pk)


@login_required
def seller_products(request):
    if not is_seller(request.user):
        raise PermissionDenied('Добавлять товары может аккаунт продавца.')
    return render(request, 'market/seller.html', {'products': Product.objects.filter(seller=request.user)})


@login_required
def product_edit(request, pk=None):
    if not is_seller(request.user):
        raise PermissionDenied('Добавлять товары может аккаунт продавца.')
    product = get_object_or_404(Product, pk=pk, seller=request.user) if pk else None
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.seller = request.user
        product.save()
        messages.success(request, 'Карточка сохранена. Добавьте историю продаж, чтобы увидеть прогноз.')
        return redirect('market:product', pk=product.pk)
    return render(request, 'market/form.html', {'form': form, 'title': 'Редактировать товар' if pk else 'Добавить товар или объект', 'submit_label': 'Сохранить'})


@login_required
def observation_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    form = ObservationForm(request.POST or None, initial={'price': product.price})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            Observation.objects.update_or_create(product=product, date=form.cleaned_data['date'],
                defaults={'price': form.cleaned_data['price'], 'sold': form.cleaned_data['sold']})
            latest = product.observations.order_by('-date').first()
            product.price = latest.price
            product.save(update_fields=['price'])
        messages.success(request, 'День сохранён. Прогноз обновлён. Остаток на складе меняется в карточке товара.')
        return redirect('market:product', pk=pk)
    return render(request, 'market/form.html', {'form': form, 'title': 'История: ' + product.title,
        'description': 'Добавьте цену и продажи за один день. Повторная дата обновляет существующую запись.', 'submit_label': 'Сохранить день'})


def ledger_query(request):
    filters = DateRangeForm(request.GET)
    query = LedgerEntry.objects.filter(owner=request.user, is_archived=False)
    if filters.is_valid():
        if filters.cleaned_data['start']:
            query = query.filter(date__gte=filters.cleaned_data['start'])
        if filters.cleaned_data['end']:
            query = query.filter(date__lte=filters.cleaned_data['end'])
    else:
        query = query.none()
    return query, filters


@login_required
def ledger(request):
    query, filters = ledger_query(request)
    totals = query.aggregate(income=Sum('amount', filter=Q(direction='income')), expense=Sum('amount', filter=Q(direction='expense')))
    income, expense = totals['income'] or Decimal('0'), totals['expense'] or Decimal('0')
    form = LedgerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.owner = request.user
        entry.save()
        return redirect('market:ledger')
    return render(request, 'market/ledger.html', {'entries': query[:200], 'entry_count': query.count(), 'form': form,
        'filters': filters, 'income': income, 'expense': expense, 'balance': income - expense,
        'export_query': request.GET.urlencode(), 'archived': LedgerEntry.objects.filter(owner=request.user, is_archived=True)[:20]})


@login_required
@require_POST
def ledger_archive(request, pk):
    entry = get_object_or_404(LedgerEntry, pk=pk, owner=request.user)
    entry.is_archived = not entry.is_archived
    entry.save(update_fields=['is_archived'])
    return redirect('market:ledger')


@login_required
def ledger_edit(request, pk):
    entry = get_object_or_404(LedgerEntry, pk=pk, owner=request.user, is_archived=False)
    form = LedgerForm(request.POST or None, instance=entry)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('market:ledger')
    return render(request, 'market/form.html', {'form': form, 'title': 'Изменить операцию', 'submit_label': 'Сохранить'})


@login_required
def history_import(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    form = HistoryImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=pk)
            Observation.objects.bulk_create([Observation(product=product, date=day, price=price, sold=sold)
                for day, price, sold in form.rows], update_conflicts=True,
                update_fields=['price', 'sold'], unique_fields=['product', 'date'])
            product.price = product.observations.order_by('-date').first().price
            product.save(update_fields=['price'])
        messages.success(request, f'Сохранено дней: {len(form.rows)}. Прогноз пересчитан.')
        return redirect('market:product', pk=pk)
    return render(request, 'market/form.html', {'form': form, 'title': 'Загрузить историю: ' + product.title,
        'description': 'Цена и продажи за каждый день. Остаток задаётся отдельно в карточке товара.', 'submit_label': 'Импортировать'})


@login_required
def support(request):
    form = SupportForm(request.POST or None)
    status = 200
    if request.method == 'POST' and form.is_valid():
        recent_count = SupportMessage.objects.filter(user=request.user, role='user', created_at__gte=timezone.now() - timedelta(minutes=1)).count()
        if recent_count >= 5:
            form.add_error('message', 'Слишком много вопросов. Подождите минуту.')
            status = 429
        else:
            history = list(SupportMessage.objects.filter(user=request.user).order_by('-pk')[:10])[::-1]
            answer, source = support_answer(form.cleaned_data['message'], history)
            with transaction.atomic():
                SupportMessage.objects.create(user=request.user, role='user', content=form.cleaned_data['message'])
                SupportMessage.objects.create(user=request.user, role='assistant', content=answer, source=source)
            return redirect('market:support')
    history = list(SupportMessage.objects.filter(user=request.user).order_by('-pk')[:50])[::-1]
    return render(request, 'market/support.html', {'form': form, 'history': history, 'faqs': FAQ}, status=status)


def excel_response(title, headers, rows, filename):
    response = HttpResponse(workbook_bytes(title, headers, rows), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def ledger_excel(request):
    query, filters = ledger_query(request)
    if not filters.is_valid():
        return HttpResponse('Некорректный период.', status=400)
    return excel_response('Доходы и расходы', ['Дата', 'Тип', 'Сумма, KZT', 'Категория', 'Описание'],
        [(row.date, row.get_direction_display(), row.amount, row.get_category_display(), row.note) for row in query], 'foresell-finances')


def catalog_excel(request):
    return excel_response('Каталог', ['Название', 'Категория', 'Регион', 'Цена, KZT', 'Остаток', 'Данные'],
        [(p.title, p.get_kind_display(), p.region, p.price, p.stock, 'Демонстрационные' if p.is_demo else 'Данные продавца') for p in catalog_query(request)], 'foresell-catalog')


def product_excel(request, pk):
    product = get_object_or_404(visible_products(request.user), pk=pk)
    return excel_response('История', ['Дата', 'Цена, KZT', 'Продано', 'Источник'],
        [(row.date, row.price, row.sold, 'Демо' if product.is_demo else 'Продавец') for row in product.observations.all()], 'foresell-history')
