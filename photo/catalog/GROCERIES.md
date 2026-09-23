# Фотографии продуктов

Фотографии загружены из Pexels 23.09.2026 и сохранены локально как JPEG шириной
1000 пикселей. [Лицензия Pexels](https://www.pexels.com/license/).
Фото иллюстрируют вид продукта, а не упаковку или ассортимент реального продавца.
«Алихан · Ainala Market», фасовки, цены, остатки, отзывы и история покупок — демо.

| Локальный файл | Автор | Исходная страница |
|---|---|---|
| grocery-milk.jpg | Ann H | [Молоко](https://www.pexels.com/photo/bottle-and-glasses-on-white-background-14127931/) |
| grocery-bread.jpg | Noemí Jiménez | [Хлеб](https://www.pexels.com/photo/loaf-of-bread-10075983/) |
| grocery-eggs.jpg | Klaus Nielsen | [Яйца](https://www.pexels.com/photo/set-of-chicken-eggs-in-carton-box-6294168/) |
| grocery-apples.jpg | Evgeniy Alekseyev | [Яблоки](https://www.pexels.com/photo/ripe-red-apples-in-bowl-on-white-background-7333128/) |
| grocery-bananas.jpg | Renata Brant | [Бананы](https://www.pexels.com/photo/ripe-bananas-2116020/) |
| grocery-tomatoes.jpg | Andre Taissin | [Помидоры](https://www.pexels.com/photo/close-up-shot-of-fresh-tomatoes-6060902/) |
| grocery-rice.jpg | MART PRODUCTION | [Рис](https://www.pexels.com/photo/uncooked-rice-on-white-surface-8108170/) |
| grocery-pasta.jpg | Klaus Nielsen | [Макароны](https://www.pexels.com/photo/pack-of-dry-raw-farfalle-pasta-placed-on-table-6287549/) |
| grocery-cheese.jpg | Polina Tankilevitch | [Сыр](https://www.pexels.com/photo/cheese-in-close-up-photography-4187780/) |
| grocery-yogurt.jpg | Cats Coming | [Йогурт](https://www.pexels.com/photo/jar-with-delicious-plain-yogurt-and-wooden-spoon-on-saucer-4428349/) |

## Добавить предложения в локальную базу

```powershell
.\.venv\Scripts\python.exe manage.py seed_grocery_catalog
```

Если фотографий нет, добавьте `--download-images`. Загрузка касается только
десяти известных публичных URL из `market/grocery_catalog.py`.
Отдельного API-ключа или аккаунта Pexels не требуется.
