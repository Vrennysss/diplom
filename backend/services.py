import yaml
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
