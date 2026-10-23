import secrets

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models import F, Sum

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

ORDER_STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'

    email = models.EmailField('Email', unique=True)
    company = models.CharField('Компания', max_length=40, blank=True)
    position = models.CharField('Должность', max_length=40, blank=True)
    username = models.CharField(
        'Имя пользователя',
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        blank=True,
    )
    is_active = models.BooleanField('Активен', default=False)
    type = models.CharField(
        'Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5,
        default='buyer',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('email',)

    def __str__(self):
        return self.email


class Shop(models.Model):
    name = models.CharField('Название', max_length=50)
    url = models.URLField('Ссылка', null=True, blank=True)
    user = models.OneToOneField(
        User, verbose_name='Пользователь', null=True, blank=True,
        on_delete=models.CASCADE,
    )
    state = models.BooleanField('Прием заказов', default=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField('Название', max_length=40)
    shops = models.ManyToManyField(
        Shop, verbose_name='Магазины', related_name='categories', blank=True
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('Название', max_length=80)
    category = models.ForeignKey(
        Category, verbose_name='Категория', related_name='products',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    model = models.CharField('Модель', max_length=80, blank=True)
    external_id = models.PositiveIntegerField('Внешний ИД')
    product = models.ForeignKey(
        Product, verbose_name='Продукт', related_name='product_infos',
        on_delete=models.CASCADE,
    )
    shop = models.ForeignKey(
        Shop, verbose_name='Магазин', related_name='product_infos',
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField('Количество')
    price = models.PositiveIntegerField('Цена')
    price_rrc = models.PositiveIntegerField('Рекомендуемая розничная цена')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = 'Информация о продуктах'
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'shop', 'external_id'],
                name='unique_product_info',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} ({self.shop.name})'


class Parameter(models.Model):
    name = models.CharField('Название', max_length=40)

    class Meta:
        verbose_name = 'Имя параметра'
        verbose_name_plural = 'Имена параметров'
        ordering = ('name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(
        ProductInfo, verbose_name='Информация о продукте',
        related_name='product_parameters', on_delete=models.CASCADE,
    )
    parameter = models.ForeignKey(
        Parameter, verbose_name='Параметр', related_name='product_parameters',
        on_delete=models.CASCADE,
    )
    value = models.CharField('Значение', max_length=100)

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'
        constraints = [
            models.UniqueConstraint(
                fields=['product_info', 'parameter'],
                name='unique_product_parameter',
            ),
        ]

    def __str__(self):
        return f'{self.parameter.name}: {self.value}'


class Contact(models.Model):
    user = models.ForeignKey(
        User, verbose_name='Пользователь', related_name='contacts',
        on_delete=models.CASCADE,
    )
    city = models.CharField('Город', max_length=50)
    street = models.CharField('Улица', max_length=100)
    house = models.CharField('Дом', max_length=15, blank=True)
    structure = models.CharField('Корпус', max_length=15, blank=True)
    building = models.CharField('Строение', max_length=15, blank=True)
    apartment = models.CharField('Квартира', max_length=15, blank=True)
    phone = models.CharField('Телефон', max_length=20)

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = 'Список контактов пользователя'

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'


class Order(models.Model):
    user = models.ForeignKey(
        User, verbose_name='Пользователь', related_name='orders',
        on_delete=models.CASCADE,
    )
    dt = models.DateTimeField('Дата', auto_now_add=True)
    state = models.CharField(
        'Статус', choices=ORDER_STATE_CHOICES, max_length=15
    )
    contact = models.ForeignKey(
        Contact, verbose_name='Контакт', null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Список заказов'
        ordering = ('-dt',)

    def __str__(self):
        return f'Заказ {self.pk} от {self.dt:%d.%m.%Y}'

    @property
    def total_sum(self):
        return self.ordered_items.aggregate(
            total=Sum(F('quantity') * F('product_info__price'))
        )['total'] or 0


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, verbose_name='Заказ', related_name='ordered_items',
        on_delete=models.CASCADE,
    )
    product_info = models.ForeignKey(
        ProductInfo, verbose_name='Информация о продукте',
        related_name='ordered_items', on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField('Количество')

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = 'Список заказанных позиций'
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product_info'], name='unique_order_item'
            ),
        ]


class ConfirmEmailToken(models.Model):
    user = models.ForeignKey(
        User, verbose_name='Пользователь', related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
    )
    key = models.CharField('Ключ', max_length=64, unique=True)
    created_at = models.DateTimeField('Когда создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Токен для {self.user}'
