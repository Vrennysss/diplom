from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from backend.models import (
    ORDER_STATE_CHOICES, Category, Contact, Order, OrderItem, ProductInfo, ProductParameter, Shop,
    User,
)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'password', 'company',
            'position', 'type',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        user = User(**{key: value for key, value in attrs.items()
                       if key != 'password'})
        validate_password(attrs['password'], user)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class EmailConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    password = serializers.CharField()


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')


class ProductInfoSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='product.name')
    category = serializers.CharField(source='product.category.name')
    shop = serializers.StringRelatedField()
    product_parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = (
            'id', 'name', 'category', 'shop', 'model', 'quantity', 'price',
            'price_rrc', 'product_parameters',
        )


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id', 'city', 'street', 'house', 'structure', 'building',
            'apartment', 'phone',
        )


class OrderItemCreateSerializer(serializers.Serializer):
    product_info = serializers.PrimaryKeyRelatedField(
        queryset=ProductInfo.objects.filter(shop__state=True)
    )
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs['quantity'] > attrs['product_info'].quantity:
            raise serializers.ValidationError(
                'Недостаточно товара на складе'
            )
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity')


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    total_sum = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'state', 'dt', 'contact', 'ordered_items', 'total_sum',
        )


class OrderConfirmSerializer(serializers.Serializer):
    contact = serializers.IntegerField()


class ShopStateSerializer(serializers.Serializer):
    state = serializers.BooleanField()


class PartnerOrderSerializer(serializers.ModelSerializer):
    ordered_items = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id', 'state', 'dt', 'contact', 'ordered_items', 'total_sum',
        )

    def get_shop_items(self, order):
        shop = self.context['shop']
        return [
            item for item in order.ordered_items.all()
            if item.product_info.shop_id == shop.id
        ]

    def get_ordered_items(self, order):
        return OrderItemSerializer(self.get_shop_items(order), many=True).data

    def get_total_sum(self, order):
        return sum(
            item.quantity * item.product_info.price
            for item in self.get_shop_items(order)
        )


class OrderStateSerializer(serializers.Serializer):
    state = serializers.ChoiceField(
        choices=[
            choice for choice in ORDER_STATE_CHOICES
            if choice[0] not in ('basket', 'new')
        ]
    )
