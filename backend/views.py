from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.models import ConfirmEmailToken, User
from backend.serializers import (
    EmailConfirmSerializer, LoginSerializer, PasswordResetConfirmSerializer,
    PasswordResetSerializer, RegisterSerializer,
)


def error_response(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'status': False, 'error': message}, status=code)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        user = serializer.save()
        token = ConfirmEmailToken.objects.create(user=user)
        send_mail(
            'Подтверждение регистрации',
            f'Токен для подтверждения email: {token.key}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        return Response({'status': True}, status=status.HTTP_201_CREATED)


class ConfirmEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        token = ConfirmEmailToken.objects.filter(
            user__email=serializer.validated_data['email'],
            key=serializer.validated_data['token'],
        ).first()
        if token is None:
            return error_response('Неправильно указан токен или email')

        token.user.is_active = True
        token.user.save()
        token.delete()
        return Response({'status': True})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None or not user.is_active:
            return error_response('Не удалось авторизовать')

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'status': True, 'token': token.key})


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        user = User.objects.filter(
            email=serializer.validated_data['email'], is_active=True
        ).first()
        if user is not None:
            send_mail(
                'Сброс пароля',
                f'Токен для сброса пароля: {default_token_generator.make_token(user)}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
        return Response({'status': True})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        data = serializer.validated_data
        user = User.objects.filter(email=data['email'], is_active=True).first()
        if user is None or not default_token_generator.check_token(
            user, data['token']
        ):
            return error_response('Неправильно указан токен или email')

        try:
            validate_password(data['password'], user)
        except ValidationError as error:
            return error_response(list(error.messages))

        user.set_password(data['password'])
        user.save()
        Token.objects.filter(user=user).delete()
        return Response({'status': True})
