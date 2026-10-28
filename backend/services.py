import yaml
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from backend.models import (
    Category, Parameter, Product, ProductInfo, ProductParameter, Shop,
)


@transaction.atomic
def import_shop_data(data, user=None):
    """Загружает прайс магазина из словаря, заменяя прежние предложения."""
    shop, _ = Shop.objects.get_or_create(
        name=data['shop'], defaults={'user': user}
    )
    if user is not None and shop.user_id not in (None, user.id):
        raise ValueError('Магазин принадлежит другому пользователю')

    for item in data['categories']:
        category, _ = Category.objects.get_or_create(
            id=item['id'], defaults={'name': item['name']}
        )
        category.shops.add(shop)

    ProductInfo.objects.filter(shop=shop).delete()

    for item in data['goods']:
        product, _ = Product.objects.get_or_create(
            name=item['name'], category_id=item['category']
        )
        product_info = ProductInfo.objects.create(
            product=product,
            shop=shop,
            external_id=item['id'],
            model=item.get('model', ''),
            price=item['price'],
            price_rrc=item['price_rrc'],
            quantity=item['quantity'],
        )
        for name, value in item.get('parameters', {}).items():
            parameter, _ = Parameter.objects.get_or_create(name=name)
            ProductParameter.objects.create(
                product_info=product_info, parameter=parameter, value=value
            )
    return shop


def import_shop_file(path, user=None):
    with open(path, encoding='utf-8') as file:
        data = yaml.safe_load(file)
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
