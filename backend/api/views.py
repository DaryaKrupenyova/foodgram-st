import random
import string

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .pagination import LimitedPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    FavoriteSerializer, IngredientSerializer,
    RecipeCreateSerializer, RecipeSerializer,
    ShoppingCartSerializer, ImprovedUserCreateSerializer,
    ImprovedUserSerializer, AvatarUploadSerializer,
    PasswordResetSerializer, SubscriptionSerializer,
    SubscriptionCreateSerializer
)
from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    ShoppingCart, ShortLink
)


User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filterset_class = IngredientFilter
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = LimitedPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': self.request}
        )
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer=serializer)
        instance_serializer = RecipeSerializer(
            instance,
            context={'request': self.request}
        )
        return Response(
            data=instance_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def perform_update(self, serializer):
        return serializer.save(author=self.request.user)

    def update(self, request, pk=None, *args, **kwargs):
        self.get_object()
        serializer = self.get_serializer(
            data=request.data,
            context={'request': self.request}
        )
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer=serializer)
        instance_serializer = RecipeSerializer(
            instance,
            context={'request': self.request}
        )
        return Response(
            data=instance_serializer.data,
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self._handle_recipe_action(
            request, pk, Favorite, FavoriteSerializer
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_recipe_action(
            request, pk, ShoppingCart, ShoppingCartSerializer
        )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='get-link'
    )
    def short_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        short_link, created = ShortLink.objects.get_or_create(
            recipe=recipe,
            defaults={'slug': self._generate_deterministic_string(recipe.id)}
        )
        protocol = 'https' if request.is_secure() else 'http'
        domain = request.get_host()
        return Response({
            'short-link': f'{protocol}://{domain}/s/{short_link.slug}/'
        })

    def _generate_deterministic_string(
        self,
        seed: int,
        length: int = 12
    ) -> str:
        random.seed(seed)
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))

    def _handle_recipe_action(self, request, pk, model, serializer_class):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт уже добавлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = serializer_class(
                data={'user': user.id, 'recipe': recipe.id}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(data={
                'id': recipe.id,
                'name': recipe.name,
                'image': str(recipe.image.url),
                'cooking_time': recipe.cooking_time
            }, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт не найден'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        shopping_list = ['Список покупок:\n']
        for ingredient in ingredients:
            shopping_list.append(
                f'{ingredient["ingredient__name"]} - '
                f'{ingredient["amount"]} '
                f'{ingredient["ingredient__measurement_unit"]}\n'
            )

        response = HttpResponse(
            ''.join(shopping_list),
            content_type='text/plain'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class ImprovedUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = ImprovedUserSerializer
    pagination_class = LimitedPageNumberPagination
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in [
            'me', 'subscribe', 'subscriptions', 'upload_avatar'
        ]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ImprovedUserCreateSerializer
        if self.action == 'subscribe':
            return SubscriptionCreateSerializer
        if self.action == 'subscriptions':
            return SubscriptionSerializer
        return ImprovedUserSerializer

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            serializer = self.get_serializer(
                author,
                data={'id': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            user.follower.create(author=author)
            recipes_limit = request.query_params.get('recipes_limit')
            response_serializer = SubscriptionSerializer(
                author,
                context={
                    'recipes_limit': recipes_limit,
                    'request': request
                }
            )
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            if not user.follower.filter(author=author).exists():
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.follower.filter(author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        recipes_limit = request.query_params.get('recipes_limit')
        pages = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            pages,
            many=True,
            context={
                'recipes_limit': recipes_limit,
                'request': request
            }
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def upload_avatar(self, request):
        if request.method == 'DELETE':
            request.user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarUploadSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = PasswordResetSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
