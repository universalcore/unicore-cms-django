from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

from adminplus.sites import AdminSitePlus

admin.site = AdminSitePlus()
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(
        r'^github/import/clone/$',
        'cms.views.import_clone_repo', name='import_clone_repo'),
    url(
        r'^github/import/do/$',
        'cms.views.import_repo', name='import_repo'),
    url(r'^admin/', RedirectView.as_view(url='/')),
    url(r'^login/$', 'django_cas_ng.views.login'),
    url(r'^logout/$', 'django_cas_ng.views.logout'),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'', include('taggit_live.urls')),
    url(r'^', include(admin.site.urls)),
)
