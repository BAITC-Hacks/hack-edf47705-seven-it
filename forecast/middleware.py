from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class SeparateAdminSessionMiddleware(SessionMiddleware):
    """Use independent browser sessions for the site and the Django admin."""

    def process_request(self, request):
        request.is_admin_area = request.path_info.startswith(reverse('admin:index'))
        request._original_session_cookies = request.COOKIES
        if request.is_admin_area:
            cookies = request.COOKIES.copy()
            cookies.pop(settings.SESSION_COOKIE_NAME, None)
            key = cookies.get(settings.ADMIN_SESSION_COOKIE_NAME)
            if key:
                cookies[settings.SESSION_COOKIE_NAME] = key
            request.COOKIES = cookies
        super().process_request(request)

    def process_response(self, request, response):
        response = super().process_response(request, response)
        if getattr(request, 'is_admin_area', False):
            cookie = response.cookies.pop(settings.SESSION_COOKIE_NAME, None)
            if cookie is not None:
                response.cookies[settings.ADMIN_SESSION_COOKIE_NAME] = cookie.value
                for attribute, value in cookie.items():
                    response.cookies[settings.ADMIN_SESSION_COOKIE_NAME][attribute] = value
                response.cookies[settings.ADMIN_SESSION_COOKIE_NAME]['path'] = reverse('admin:index')
        request.COOKIES = getattr(request, '_original_session_cookies', request.COOKIES)
        return response


class PublicIdentityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # A staff session must never become a customer identity, even if its
        # cookie is manually copied under the public session cookie name.
        if not request.is_admin_area and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                request.user = AnonymousUser()

                async def anonymous_user():
                    return request.user

                request.auser = anonymous_user
