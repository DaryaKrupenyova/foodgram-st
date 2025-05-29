from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User
from .fields import Base64ImageField


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    username = serializers.CharField(
        max_length=150,
        validators=[
            UniqueValidator(queryset=User.objects.all()),
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Имя пользователя может содержать только буквы,'
                        ' цифры и символы @/./+/-/_'
            )
        ]
    )
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True, 'write_only': True}
        }

    def validate(self, data):
        if not data.get('email'):
            raise serializers.ValidationError('Email is required')
        if not data.get('username'):
            raise serializers.ValidationError('Username is required')
        if len(data.get('username', '')) > 150:
            raise serializers.ValidationError('Username must be no more'
                                              ' than 150 characters')
        if not data.get('first_name'):
            raise serializers.ValidationError('First name is required')
        if not data.get('last_name'):
            raise serializers.ValidationError('Last name is required')
        if not data.get('password'):
            raise serializers.ValidationError('Password is required')
        return data

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.follower.filter(author=obj).exists()


class AvatarUploadSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)
        extra_kwargs = {
            'avatar': {'required': True}
        }

    def validate(self, data):
        if not data:
            raise serializers.ValidationError('Аватар не может быть пустым')
        return data


class PasswordResetSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Неверный текущий пароль'}
            )
        try:
            validate_password(data['new_password'], user)
        except Exception as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
