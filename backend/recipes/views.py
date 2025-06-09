from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from recipes.models import ShortLink


class ShortLinkRedirectView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        short_link = get_object_or_404(ShortLink, slug=slug)
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        return HttpResponseRedirect(
            f'{frontend_url}/recipes/{short_link.recipe.id}/'
        )
