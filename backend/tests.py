from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from backend.models import (
    Category, ConfirmEmailToken, Contact, Order, OrderItem, ProductInfo,
    ProductParameter, Shop, User,
)
from backend.services import import_shop_data, import_shop_file


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


class AuthTest(APITestCase):
    user_data = {
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'email': 'ivan@example.com',
        'password': 'Str0ng-pass-123',
        'company': 'ООО Ромашка',
        'position': 'Менеджер',
    }

    def register(self):
        return self.client.post(
            reverse('backend:user-register'), self.user_data
        )

    def confirm(self):
        token = ConfirmEmailToken.objects.get(
            user__email=self.user_data['email']
        )
        return self.client.post(
            reverse('backend:user-register-confirm'),
            {'email': self.user_data['email'], 'token': token.key},
        )

    def login(self):
        return self.client.post(
            reverse('backend:user-login'),
            {'email': self.user_data['email'],
             'password': self.user_data['password']},
        )

    def test_register_sends_email(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(User.objects.get().is_active)

    def test_register_weak_password(self):
        self.user_data['password'] = '123'
        self.assertEqual(self.register().status_code, 400)

    def test_login_requires_confirmation(self):
        self.register()
        self.assertEqual(self.login().status_code, 400)
        self.confirm()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())

    def test_confirm_with_wrong_token(self):
        self.register()
        response = self.client.post(
            reverse('backend:user-register-confirm'),
            {'email': self.user_data['email'], 'token': 'wrong'},
        )
        self.assertEqual(response.status_code, 400)

    def test_password_reset(self):
        self.register()
        self.confirm()
        user = User.objects.get()
        self.client.post(
            reverse('backend:password-reset'), {'email': user.email}
        )
        self.assertEqual(len(mail.outbox), 2)
        response = self.client.post(
            reverse('backend:password-reset-confirm'),
            {
                'email': user.email,
                'token': default_token_generator.make_token(user),
                'password': 'An0ther-pass-456',
            },
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password('An0ther-pass-456'))


class ProductTest(APITestCase):
    def setUp(self):
        import_shop_file(settings.BASE_DIR / 'data' / 'shop1.yaml')

    def test_product_list(self):
        response = self.client.get(reverse('backend:products'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 14)

    def test_product_list_filter_by_category(self):
        category = Category.objects.get(name='Смартфоны')
        response = self.client.get(
            reverse('backend:products'), {'category_id': category.id}
        )
        self.assertTrue(response.json())
        self.assertTrue(
            all(item['category'] == 'Смартфоны'
                for item in response.json())
        )

    def test_product_list_hides_closed_shop(self):
        Shop.objects.update(state=False)
        response = self.client.get(reverse('backend:products'))
        self.assertEqual(response.json(), [])

    def test_product_detail(self):
        product_info = ProductInfo.objects.first()
        response = self.client.get(
            reverse('backend:product-detail', args=[product_info.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('product_parameters', response.json())


class BasketTest(APITestCase):
    def setUp(self):
        import_shop_file(settings.BASE_DIR / 'data' / 'shop1.yaml')
        self.user = User.objects.create_user(
            email='buyer@example.com', password='Str0ng-pass-123',
            is_active=True,
        )
        self.client.force_authenticate(self.user)
        self.product_info = ProductInfo.objects.first()

    def add_to_basket(self, quantity=1):
        return self.client.post(
            reverse('backend:basket'),
            {'items': [{'product_info': self.product_info.id,
                        'quantity': quantity}]},
            format='json',
        )

    def test_basket_requires_auth(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse('backend:basket'))
        self.assertEqual(response.status_code, 401)

    def test_add_to_basket(self):
        self.assertEqual(self.add_to_basket(2).status_code, 201)
        response = self.client.get(reverse('backend:basket'))
        self.assertEqual(len(response.json()['ordered_items']), 1)
        self.assertEqual(
            response.json()['total_sum'], self.product_info.price * 2
        )

    def test_add_more_than_in_stock(self):
        response = self.add_to_basket(self.product_info.quantity + 1)
        self.assertEqual(response.status_code, 400)

    def test_update_and_delete_items(self):
        self.add_to_basket(1)
        self.client.put(
            reverse('backend:basket'),
            {'items': [{'product_info': self.product_info.id,
                        'quantity': 3}]},
            format='json',
        )
        item = OrderItem.objects.get()
        self.assertEqual(item.quantity, 3)
        response = self.client.delete(
            reverse('backend:basket'), {'items': [item.id]}, format='json'
        )
        self.assertEqual(response.json()['deleted'], 1)
        self.assertFalse(OrderItem.objects.exists())

    def test_contacts(self):
        data = {'city': 'Москва', 'street': 'Тверская', 'house': '1',
                'phone': '+79990000000'}
        response = self.client.post(reverse('backend:user-contact'), data)
        self.assertEqual(response.status_code, 201)
        contact = Contact.objects.get()
        self.client.put(
            reverse('backend:user-contact'), {'id': contact.id, 'house': '2'}
        )
        contact.refresh_from_db()
        self.assertEqual(contact.house, '2')
        response = self.client.delete(
            reverse('backend:user-contact'), {'items': [contact.id]},
            format='json',
        )
        self.assertEqual(response.json()['deleted'], 1)


class OrderTest(APITestCase):
    def setUp(self):
        import_shop_file(settings.BASE_DIR / 'data' / 'shop1.yaml')
        self.user = User.objects.create_user(
            email='buyer@example.com', password='Str0ng-pass-123',
            is_active=True,
        )
        self.client.force_authenticate(self.user)
        self.product_info = ProductInfo.objects.first()
        self.contact = Contact.objects.create(
            user=self.user, city='Москва', street='Тверская', house='1',
            apartment='5', phone='+79990000000',
        )

    def add_to_basket(self, quantity=1):
        self.client.post(
            reverse('backend:basket'),
            {'items': [{'product_info': self.product_info.id,
                        'quantity': quantity}]},
            format='json',
        )

    def confirm_order(self, contact_id=None):
        return self.client.post(
            reverse('backend:order'),
            {'contact': contact_id or self.contact.id},
        )

    def test_confirm_order(self):
        self.add_to_basket(2)
        stock = self.product_info.quantity
        mail.outbox.clear()
        response = self.confirm_order()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(mail.outbox[1].to, [settings.ADMIN_EMAIL])
        self.assertEqual(Order.objects.get().state, 'new')
        self.product_info.refresh_from_db()
        self.assertEqual(self.product_info.quantity, stock - 2)

    def test_confirm_empty_basket(self):
        self.assertEqual(self.confirm_order().status_code, 400)

    def test_confirm_foreign_contact(self):
        self.add_to_basket()
        other = User.objects.create_user(
            email='other@example.com', password='x'
        )
        contact = Contact.objects.create(
            user=other, city='Казань', street='Баумана', phone='1'
        )
        self.assertEqual(self.confirm_order(contact.id).status_code, 400)

    def test_order_list_and_detail(self):
        self.add_to_basket()
        order_id = self.confirm_order().json()['order']
        response = self.client.get(reverse('backend:order'))
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(
            reverse('backend:order-detail', args=[order_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['contact']['city'], 'Москва')

    def test_detail_of_foreign_order_not_found(self):
        self.add_to_basket()
        order_id = self.confirm_order().json()['order']
        other = User.objects.create_user(
            email='other@example.com', password='x', is_active=True
        )
        self.client.force_authenticate(other)
        response = self.client.get(
            reverse('backend:order-detail', args=[order_id])
        )
        self.assertEqual(response.status_code, 404)


class PartnerTest(APITestCase):
    def setUp(self):
        self.partner = User.objects.create_user(
            email='shop@example.com', password='Str0ng-pass-123',
            is_active=True, type='shop',
        )
        self.client.force_authenticate(self.partner)

    def upload(self):
        with open(settings.BASE_DIR / 'data' / 'shop1.yaml', 'rb') as file:
            return self.client.post(
                reverse('backend:partner-update'), {'file': file},
                format='multipart',
            )

    def test_buyer_has_no_access(self):
        buyer = User.objects.create_user(
            email='buyer@example.com', password='x', is_active=True
        )
        self.client.force_authenticate(buyer)
        response = self.client.get(reverse('backend:partner-state'))
        self.assertEqual(response.status_code, 403)

    def test_update_price(self):
        self.assertEqual(self.upload().status_code, 200)
        shop = Shop.objects.get()
        self.assertEqual(shop.user, self.partner)
        self.assertEqual(shop.product_infos.count(), 14)

    def test_update_with_invalid_file(self):
        response = self.client.post(
            reverse('backend:partner-update'),
            {'file': SimpleUploadedFile('bad.yaml', b'shop: x')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    def test_reimport_keeps_ordered_items(self):
        self.upload()
        buyer = User.objects.create_user(
            email='buyer@example.com', password='x', is_active=True
        )
        order = Order.objects.create(user=buyer, state='new')
        OrderItem.objects.create(
            order=order, product_info=ProductInfo.objects.first(), quantity=1
        )
        self.upload()
        self.assertEqual(OrderItem.objects.count(), 1)

    def test_change_state(self):
        self.upload()
        url = reverse('backend:partner-state')
        self.client.post(url, {'state': False}, format='json')
        self.assertFalse(self.client.get(url).json()['state'])

    def test_orders_and_status_change(self):
        self.upload()
        buyer = User.objects.create_user(
            email='buyer@example.com', password='x', is_active=True
        )
        order = Order.objects.create(user=buyer, state='new')
        OrderItem.objects.create(
            order=order, product_info=ProductInfo.objects.first(), quantity=2
        )
        response = self.client.get(reverse('backend:partner-orders'))
        self.assertEqual(len(response.json()), 1)
        response = self.client.put(
            reverse('backend:partner-order-state', args=[order.id]),
            {'state': 'sent'}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.state, 'sent')

    def test_state_without_shop(self):
        self.upload()
        other = User.objects.create_user(
            email='other@example.com', password='x', is_active=True,
            type='shop',
        )
        self.client.force_authenticate(other)
        self.client.post(
            reverse('backend:partner-state'), {'state': True}, format='json'
        )
        response = self.client.get(reverse('backend:partner-state'))
        self.assertEqual(response.status_code, 404)


class ScenarioTest(APITestCase):
    def test_full_scenario(self):
        import_shop_file(settings.BASE_DIR / 'data' / 'shop1.yaml')
        import_shop_data({
            'shop': 'Второй магазин',
            'categories': [{'id': 224, 'name': 'Смартфоны'}],
            'goods': [{
                'id': 1, 'category': 224, 'model': 'test/model',
                'name': 'Тестовый смартфон', 'price': 1000,
                'price_rrc': 1200, 'quantity': 5, 'parameters': {},
            }],
        })
        email, password = 'client@example.com', 'Str0ng-pass-123'

        self.client.post(reverse('backend:user-register'), {
            'first_name': 'Пётр', 'last_name': 'Петров', 'email': email,
            'password': password,
        })
        key = ConfirmEmailToken.objects.get().key
        self.client.post(
            reverse('backend:user-register-confirm'),
            {'email': email, 'token': key},
        )
        token = self.client.post(
            reverse('backend:user-login'),
            {'email': email, 'password': password},
        ).json()['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        products = self.client.get(reverse('backend:products')).json()
        shops = {product['shop'] for product in products}
        self.assertEqual(len(shops), 2)
        items = [
            {'product_info': next(
                p['id'] for p in products if p['shop'] == shop), 'quantity': 1}
            for shop in shops
        ]
        self.client.post(
            reverse('backend:basket'), {'items': items}, format='json'
        )
        contact = self.client.post(reverse('backend:user-contact'), {
            'city': 'Москва', 'street': 'Тверская', 'house': '1',
            'phone': '+79990000000',
        })
        self.assertEqual(contact.status_code, 201)
        contact_id = self.client.get(
            reverse('backend:user-contact')
        ).json()[0]['id']

        mail.outbox.clear()
        response = self.client.post(
            reverse('backend:order'), {'contact': contact_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

        orders = self.client.get(reverse('backend:order')).json()
        self.assertEqual(len(orders), 1)
        self.assertEqual(len(orders[0]['ordered_items']), 2)
