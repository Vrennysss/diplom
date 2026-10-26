from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from backend.models import Category, ProductInfo, ProductParameter, Shop, User


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
