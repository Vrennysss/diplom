from django.conf import settings
from django.test import TestCase

from backend.models import Category, ProductInfo, ProductParameter, Shop
from backend.services import import_shop_file


class ImportTest(TestCase):
    path = settings.BASE_DIR / 'data' / 'shop1.yaml'

    def test_import_creates_objects(self):
        shop = import_shop_file(self.path)
        self.assertEqual(shop.name, 'Связной')
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(ProductInfo.objects.filter(shop=shop).count(), 14)
        self.assertTrue(ProductParameter.objects.exists())

    def test_repeated_import_does_not_duplicate(self):
        import_shop_file(self.path)
        import_shop_file(self.path)
        self.assertEqual(Shop.objects.count(), 1)
        self.assertEqual(ProductInfo.objects.count(), 14)
