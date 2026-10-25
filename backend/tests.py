from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from backend.models import (
    Category, ConfirmEmailToken, ProductInfo, ProductParameter, Shop, User,
)
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
        return self.client.post(reverse('backend:user-register'), self.user_data)

    def confirm(self):
        token = ConfirmEmailToken.objects.get(user__email=self.user_data['email'])
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
