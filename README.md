# Автоматизация закупок

Backend сервиса закупок для розничной сети (Django, Django REST Framework).

## Запуск

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Сервис доступен на http://127.0.0.1:8000/.

Письма в режиме разработки выводятся в консоль.

## Импорт товаров

Прайсы лежат в папке `data` в формате YAML. Загрузка всех файлов:

```bash
python manage.py import_products
```

Или конкретных файлов: `python manage.py import_products data/shop1.yaml`.
При повторной загрузке предложения магазина заменяются новыми.

## Тесты

```bash
python manage.py test
```
