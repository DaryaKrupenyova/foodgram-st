from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class LimitedPageNumberPagination(PageNumberPagination):
    page_size = settings.PAGINATOR_PAGE_SIZE
    page_size_query_param = 'limit'
