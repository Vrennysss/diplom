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

## API

Все методы начинаются с `/api/v1/`, данные передаются в теле запроса.

| Метод | Адрес | Описание |
|---|---|---|
| POST | `user/register` | Регистрация (`first_name`, `last_name`, `email`, `password`, `company`, `position`, `type`); токен подтверждения приходит на email |
| POST | `user/register/confirm` | Подтверждение email (`email`, `token`) |
| POST | `user/login` | Вход (`email`, `password`), возвращает токен авторизации |
| POST | `user/password_reset` | Запрос сброса пароля (`email`) |
| POST | `user/password_reset/confirm` | Новый пароль (`email`, `token`, `password`) |
| GET | `categories` | Список категорий |
| GET | `shops` | Магазины, принимающие заказы |
| GET | `products` | Список товаров; фильтры `shop_id`, `category_id`, `search` |
| GET | `products/<id>` | Карточка товара с характеристиками |
| GET, POST, PUT, DELETE | `user/contact` | Адреса доставки (нужна авторизация); в DELETE передаётся `items` со списком id |
| GET, POST, PUT, DELETE | `basket` | Корзина (нужна авторизация); в теле `items`: `[{"product_info": id, "quantity": n}]`, для DELETE — список id позиций |
| GET, POST | `order` | GET — список заказов; POST — подтверждение корзины (`contact` — id адреса), клиенту уходит подтверждение, администратору накладная |
| GET | `order/<id>` | Детали заказа |
| POST | `partner/update` | Поставщик: загрузка прайса, YAML-файл в поле `file` (multipart) |
| GET, POST | `partner/state` | Поставщик: статус приёма заказов, в POST — `state` (true/false) |
| GET | `partner/orders` | Поставщик: заказы с его товарами |
| PUT | `partner/orders/<id>` | Поставщик: смена статуса заказа (`state`: confirmed, assembled, sent, delivered, canceled) |

Авторизованные запросы отправляются с заголовком `Authorization: Token <токен>`.
