from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    email = models.EmailField(
        'Email',
        max_length=settings.MAX_LENGTH_USER_EMAIL,
        unique=True,
        error_messages={
            'unique': 'Пользователь с таким email уже существует.'
        },
        help_text='Введите email'
    )
    username = models.CharField(
        'Имя пользователя',
        max_length=settings.MAX_LENGTH_USER_USERNAME,
        unique=True,
        help_text='Введите имя пользователя',
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Имя пользователя может содержать только буквы,'
                        ' цифры и символы @/./+/-/_'
            )
        ],
        error_messages={
            'unique': 'Пользователь с таким именем уже существует.'
        }
    )
    first_name = models.CharField(
        'Имя',
        max_length=settings.MAX_LENGTH_USER_FIRST_NAME,
        help_text='Введите имя'
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=settings.MAX_LENGTH_USER_LAST_NAME,
        help_text='Введите фамилию'
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        null=True,
        blank=True,
        help_text='Загрузите аватар'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_follow'
            )
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
