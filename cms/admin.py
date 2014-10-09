import json
import pygit2
from datetime import datetime

# ensure celery autodiscovery runs
from djcelery import admin as celery_admin

from djcelery.models import (
    TaskState, WorkerState, PeriodicTask, IntervalSchedule, CrontabSchedule)

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.shortcuts import render
from django.conf import settings
from django.contrib.admin.util import unquote
from django.contrib.admin import helpers
from django.http import Http404, HttpResponse
from django.utils.html import escape
from django.core.exceptions import PermissionDenied

from cms.models import Post, Category, Localisation
from cms.forms import PostForm
from cms.git import repo
from cms import utils, tasks


class CategoriesListFilter(SimpleListFilter):
    title = "categories"
    parameter_name = "category_slug"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return Category.objects.values_list('slug', 'title')

    def queryset(self, request, queryset):
        """
        Returns queryset filtered on categories and primary_category.
        """
        if self.value():
            return queryset.filter(primary_category__slug=self.value())


class PostSourceListFilter(SimpleListFilter):
    title = "sources"
    parameter_name = "source_slug"

    def lookups(self, request, model_admin):
        return Post.objects.filter(
            post__isnull=False).values_list('slug', 'title')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source__slug=self.value())


class CategorySourceListFilter(SimpleListFilter):
    title = "sources"
    parameter_name = "source_slug"

    def lookups(self, request, model_admin):
        return Category.objects.filter(
            category__isnull=False).distinct().values_list('slug', 'title')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source__slug=self.value())


class TranslatableModelAdmin(admin.ModelAdmin):

    def add_view(self, request, form_url='', extra_context=None):
        object_id = request.GET.get('source', '')
        extra_context = extra_context or {}
        obj = self.get_object(request, unquote(object_id))

        if obj is not None:
            ModelForm = self.get_form(request, obj)
            form = ModelForm(instance=obj)
            extra_context['sourceform'] = helpers.AdminForm(
                form, self.get_fieldsets(request, obj),
                self.get_prepopulated_fields(request, obj),
                self.get_readonly_fields(request, obj),
                model_admin=self)
        return super(TranslatableModelAdmin, self).add_view(
            request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(
                'Post object with primary key %(key)r does not exist.' %
                {'key': escape(object_id)})

        if obj.source:
            ModelForm = self.get_form(request, obj.source)
            form = ModelForm(instance=obj.source)
            extra_context['sourceform'] = helpers.AdminForm(
                form, self.get_fieldsets(request, obj.source),
                self.get_prepopulated_fields(request, obj.source),
                self.get_readonly_fields(request, obj.source),
                model_admin=self)
        return super(TranslatableModelAdmin, self).change_view(
            request, object_id, form_url, extra_context)


class PostAdmin(TranslatableModelAdmin):
    form = PostForm

    list_display = (
        'title', 'subtitle', 'primary_category', 'created_at', 'localisation',
        'source', '_derivatives', 'uuid', 'featured_in_category', 'featured')

    list_filter = (
        'featured_in_category', 'featured', 'created_at', 'localisation',
        CategoriesListFilter, PostSourceListFilter
    )
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title', 'description', 'content')
    raw_id_fields = ('owner', 'source')
    fieldsets = (
        (None, {'fields': (
            'title', 'slug', 'subtitle', 'description', 'content', )}),
        (None, {'fields': (
            'primary_category',
            'localisation',
            'featured_in_category',
            'featured',
            'related_posts',
        )}),
        ('Meta', {
            'fields': ('owner', 'created_at', 'source'),
            'classes': ('grp-collapse grp-closed',)})
    )

    def _derivatives(self, post):
        return len(post.post_set.all())
    _derivatives.short_description = 'Derivatives'
    _derivatives.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user
        obj.last_author = request.user

        super(PostAdmin, self).save_model(
            request,
            obj,
            form,
            change
        )


class CategoryAdmin(TranslatableModelAdmin):
    list_filter = ('localisation', CategorySourceListFilter)
    list_display = (
        'title', 'subtitle', 'localisation', 'featured_in_navbar', 'source',
        '_derivatives', 'uuid',)

    raw_id_fields = ('source', )
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'subtitle')}),
        (None, {'fields': ('localisation', 'featured_in_navbar',)}),
        ('Meta', {
            'fields': ('source', ),
            'classes': ('grp-collapse grp-closed', )})
    )

    def _derivatives(self, category):
        return len(category.category_set.all())
    _derivatives.short_description = 'Derivatives'
    _derivatives.allow_tags = True

    def save_model(self, request, obj, form, change):
        obj.last_author = request.user
        super(CategoryAdmin, self).save_model(request, obj, form, change)


class CategoryInline(admin.StackedInline):
    model = Category
    extra = 0
    sortable_field_name = 'position'
    sortable_excludes = ('localisation',)
    raw_id_fields = ('source', 'last_author')


class LocalisationAdmin(admin.ModelAdmin):
    inlines = (CategoryInline,)


@admin.site.register_view('github/', 'Github Configuration')
def my_view(request, *args, **kwargs):
    branch = repo.lookup_branch(repo.head.shorthand)
    last = repo[branch.target]
    commits = []
    for commit in repo.walk(last.id, pygit2.GIT_SORT_TIME):
        commits.append(commit)

    context = {
        'github_url': settings.GIT_REPO_URL,
        'repo': repo,
        'commits': [
            {
                'message': c.message,
                'author': c.author.name,
                'commit_time': datetime.fromtimestamp(c.commit_time)
            }
            for c in commits
        ]
    }
    return render(request, 'cms/admin/github.html', context)


@admin.site.register_view('github/push/', 'Push to github')
def push_to_github(request, *args, **kwargs):
    if hasattr(settings, 'SSH_PUBKEY_PATH') and hasattr(
            settings, 'SSH_PRIVKEY_PATH'):
        utils.sync_repo()
        tasks.push_to_git.delay(
            settings.GIT_REPO_PATH,
            settings.SSH_PUBKEY_PATH,
            settings.SSH_PRIVKEY_PATH,
            settings.SSH_PASSPHRASE)

    return HttpResponse(
        json.dumps({'success': True}),
        mimetype='application/json')


admin.site.register(Post, PostAdmin)
admin.site.register(Category, CategoryAdmin)

# remove celery from admin
admin.site.unregister(TaskState)
admin.site.unregister(WorkerState)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(PeriodicTask)

admin.site.register(Localisation, LocalisationAdmin)
