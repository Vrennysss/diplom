from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.models import (
    Category, ConfirmEmailToken, Contact, Order, OrderItem, Parameter,
    Product, ProductInfo, ProductParameter, Shop, User,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'type', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Личная информация', {
            'fields': ('first_name', 'last_name', 'company', 'position'),
        }),
        ('Права', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'groups',
                'user_permissions',
            ),
        }),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop', 'price', 'quantity')
    inlines = [ProductParameterInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'dt', 'state')
    list_filter = ('state',)
    inlines = [OrderItemInline]


admin.site.register(Shop)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Parameter)
admin.site.register(Contact)
admin.site.register(ConfirmEmailToken)
