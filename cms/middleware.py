from django.http import HttpResponseForbidden
from django_cas_ng.middleware import CASMiddleware
from django_cas_ng.views import login as cas_login, logout as cas_logout


class UnicoreCASMiddleware(CASMiddleware):

    def process_view(self, request, view_func, view_args, view_kwargs):

        if view_func == cas_login:
            return cas_login(request, *view_args, **view_kwargs)
        elif view_func == cas_logout:
            return cas_logout(request, *view_args, **view_kwargs)

        if request.user.is_authenticated():
            if request.user.is_staff:
                return None
            else:
                error = ('<h1>Forbidden</h1>'
                         '<p>You do not have access to this site.</p>')
                return HttpResponseForbidden(error)

        return super(UnicoreCASMiddleware, self).process_view(
            request, view_func, view_args, view_kwargs)
