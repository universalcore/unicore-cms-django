from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^', include(admin.site.urls)),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^ckeditor/', include('ckeditor.urls')),
)
