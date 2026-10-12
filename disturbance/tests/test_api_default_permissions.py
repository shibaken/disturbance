from django.test import SimpleTestCase
from django.urls import URLPattern, URLResolver, get_resolver, resolve
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.settings import api_settings
from rest_framework.views import APIView

# '<module>.<ClassName>' of DRF views that are intentionally public. Each entry needs a justification.
PUBLIC_DRF_VIEWS = set()

PUBLIC_PAGE_URLS = ['/', '/contact/', '/further_info/']


def _iter_patterns(patterns, prefix=''):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _iter_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern):
            yield prefix + str(pattern.pattern), pattern.callback


def _routed_drf_views():
    for route, callback in _iter_patterns(get_resolver().url_patterns):
        cls = getattr(callback, 'cls', None)
        if isinstance(cls, type) and issubclass(cls, APIView):
            yield route, cls, getattr(callback, 'actions', None) or {}


class DrfDefaultPermissionTests(SimpleTestCase):
    def test_default_permission_is_is_authenticated(self):
        self.assertEqual(list(api_settings.DEFAULT_PERMISSION_CLASSES), [IsAuthenticated])

    def test_no_routed_drf_view_is_public(self):
        for route, cls, actions in _routed_drf_views():
            name = f'{cls.__module__}.{cls.__name__}'
            if name in PUBLIC_DRF_VIEWS:
                continue
            checks = [('class', cls.permission_classes)]
            for action in set(actions.values()):
                kwargs = getattr(getattr(cls, action, None), 'kwargs', None) or {}
                if 'permission_classes' in kwargs:
                    checks.append((action, kwargs['permission_classes']))
            for where, perms in checks:
                with self.subTest(view=name, route=route, where=where):
                    self.assertTrue(perms, 'empty permission_classes makes the view public')
                    self.assertNotIn(AllowAny, perms)

    def test_public_pages_are_not_drf_views(self):
        # The DRF default can't affect these pages as long as they stay plain Django views.
        for url in PUBLIC_PAGE_URLS:
            with self.subTest(url=url):
                callback = resolve(url).func
                self.assertFalse(hasattr(callback, 'cls'), f'{url} is served by a DRF view')
