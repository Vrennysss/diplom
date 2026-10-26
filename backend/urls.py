from django.urls import path

from backend.views import (
    CategoryListView, ConfirmEmailView, LoginView, PasswordResetConfirmView,
    PasswordResetView, ProductDetailView, ProductListView, RegisterView,
    ShopListView,
)

app_name = 'backend'

urlpatterns = [
    path('user/register', RegisterView.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmEmailView.as_view(),
         name='user-register-confirm'),
    path('user/login', LoginView.as_view(), name='user-login'),
    path('user/password_reset', PasswordResetView.as_view(),
         name='password-reset'),
    path('user/password_reset/confirm', PasswordResetConfirmView.as_view(),
         name='password-reset-confirm'),
    path('categories', CategoryListView.as_view(), name='categories'),
    path('shops', ShopListView.as_view(), name='shops'),
    path('products', ProductListView.as_view(), name='products'),
    path('products/<int:pk>', ProductDetailView.as_view(),
         name='product-detail'),
]
