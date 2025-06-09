from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    ShoppingCart
)
from users.validators import get_username_style_validator


User = get_user_model()


class ImprovedUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    username = serializers.CharField(
        max_length=settings.MAX_LENGTH_USER_USERNAME,
        validators=[
            UniqueValidator(queryset=User.objects.all()),
            get_username_style_validator()
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
        if len(data.get('username', '')) > settings.MAX_LENGTH_USER_USERNAME:
            raise serializers.ValidationError(
                f'Username must be no more than '
                f'{settings.MAX_LENGTH_USER_USERNAME} characters')
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


class ImprovedUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
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
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Неверный текущий пароль'}
            )
        try:
            validate_password(data['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError(
                {'new_password': list(e.messages)}
            )
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = ImprovedUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=obj).exists()


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(
        min_value=settings.MIN_VALUE_RECIPE_INGREDIENT_AMOUNT,
        max_value=settings.MAX_VALUE_RECIPE_INGREDIENT_AMOUNT
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(
        source='recipe_ingredients',
        many=True,
        required=True
    )
    author = ImprovedUserSerializer(read_only=True)
    image = Base64ImageField(
        required=True,
        allow_null=False,
        allow_empty_file=False
    )
    cooking_time = serializers.IntegerField(
        min_value=settings.MIN_VALUE_RECIPE_COOKING_TIME,
        max_value=settings.MAX_VALUE_RECIPE_COOKING_TIME
    )

    class Meta:
        model = Recipe
        exclude = ('pub_date', )

    def validate(self, data):
        if not data.get('recipe_ingredients'):
            raise serializers.ValidationError('Ingredients are required')
        if not data.get('image'):
            raise serializers.ValidationError('Image is required')
        if len(data.get('recipe_ingredients')) != len(set(
                ingredient['id'] for ingredient in data.get(
                    'recipe_ingredients'
                )
        )):
            raise serializers.ValidationError('Ingredients must be unique')
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        instance.ingredients.clear()
        self._create_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def _create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ])


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        extra_kwargs = {
            'user': {'write_only': True},
            'recipe': {'write_only': True},
        }
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном'
            )
        ]


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        extra_kwargs = {
            'user': {'write_only': True},
            'recipe': {'write_only': True},
        }
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в списке покупок'
            )
        ]


class SubscriptionSerializer(ImprovedUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count')

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes',
            'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        recipes_limit = self.context.get('recipes_limit')
        if recipes_limit:
            try:
                recipes_limit = int(recipes_limit)
                recipes = recipes[:recipes_limit]
            except (ValueError, TypeError):
                pass
        return CompactRecipeSerializer(
            recipes,
            many=True
        ).data


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id',)

    def validate(self, data):
        user = self.context['request'].user
        author = self.instance

        if user == author:
            raise serializers.ValidationError(
                {'error': 'Нельзя подписаться на самого себя'}
            )
        if user.follower.filter(author=author).exists():
            raise serializers.ValidationError(
                {'error': 'Вы уже подписаны на этого пользователя'}
            )
        return data


class CompactRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
