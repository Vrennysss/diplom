from django.urls import path

from backend.views import (
    ConfirmEmailView, LoginView, PasswordResetConfirmView, PasswordResetView,
    RegisterView,
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
]
