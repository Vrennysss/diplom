import yaml
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from backend.models import (
    Category, Parameter, Product, ProductInfo, ProductParameter, Shop,
)


def get_shop_for_import(name, user):
    if user is None:
        shop, _ = Shop.objects.get_or_create(name=name)
        return shop

    own_shop = Shop.objects.filter(user=user).first()
    if own_shop is not None:
        if own_shop.name != name:
            raise ValueError('Название магазина в файле не совпадает с вашим')
        return own_shop

    shop, _ = Shop.objects.get_or_create(name=name)
    if shop.user_id is not None:
        raise ValueError('Магазин принадлежит другому пользователю')
    shop.user = user
    shop.save()
    return shop


@transaction.atomic
def import_shop_data(data, user=None):
    """Загружает прайс магазина из словаря, обновляя прежние предложения."""
    try:
        shop = get_shop_for_import(data['shop'], user)

        for item in data['categories']:
            category, _ = Category.objects.get_or_create(
                id=item['id'], defaults={'name': item['name']}
            )
            category.shops.add(shop)

        imported_ids = []
        for item in data['goods']:
            product, _ = Product.objects.get_or_create(
                name=item['name'], category_id=item['category']
            )
            product_info, _ = ProductInfo.objects.update_or_create(
                shop=shop,
                external_id=item['id'],
                defaults={
                    'product': product,
                    'model': item.get('model', ''),
                    'price': item['price'],
                    'price_rrc': item['price_rrc'],
                    'quantity': item['quantity'],
                },
            )
            imported_ids.append(item['id'])
            product_info.product_parameters.all().delete()
            for name, value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info=product_info, parameter=parameter,
                    value=value,
                )
    except (KeyError, TypeError, AttributeError):
        raise ValueError('Неверный формат файла')

    ProductInfo.objects.filter(shop=shop).exclude(
        external_id__in=imported_ids
    ).update(quantity=0)
    return shop


def import_shop_file(path, user=None):
    with open(path, encoding='utf-8') as file:
        return import_shop_stream(file, user)


def import_shop_stream(stream, user=None):
    try:
        data = yaml.safe_load(stream)
    except yaml.YAMLError:
        raise ValueError('Файл не является корректным YAML')
    return import_shop_data(data, user)


def build_order_text(order):
    lines = [f'Заказ №{order.id} от {order.dt:%d.%m.%Y %H:%M}']
    for item in order.ordered_items.select_related(
        'product_info__product', 'product_info__shop'
    ):
        info = item.product_info
        lines.append(
            f'{info.product.name} ({info.shop.name}): '
            f'{item.quantity} x {info.price} = {item.quantity * info.price}'
        )
    lines.append(f'Итого: {order.total_sum}')
    contact = order.contact
    lines.append(
        f'Доставка: {contact.city}, {contact.street}, д. {contact.house}, '
        f'кв. {contact.apartment}, тел. {contact.phone}'
    )
    return '\n'.join(lines)


def send_order_emails(order):
    text = build_order_text(order)
    send_mail(
        f'Заказ №{order.id} принят', text, settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
    )
    send_mail(
        f'Накладная по заказу №{order.id}', text, settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
    )
