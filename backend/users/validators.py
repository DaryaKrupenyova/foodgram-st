from django.core.validators import RegexValidator


def get_username_style_validator():
    return RegexValidator(
        regex=r'^[\w.@+-]+$',
        message='Имя пользователя может содержать только'
                ' буквы, цифры и символы @/./+/-/_'
    )
