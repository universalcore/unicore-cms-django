from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.http import HttpResponseRedirect
from adminplus.sites import AdminSitePlus

admin.site = AdminSitePlus()
admin.autodiscover()


def redirect_to_root(request):
    return HttpResponseRedirect('/')

urlpatterns = patterns(
    '',
    url(r'^admin/', redirect_to_root),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^', include(admin.site.urls)),
)
