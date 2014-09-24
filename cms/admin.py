import pygit2
from datetime import datetime

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.shortcuts import render
from django.conf import settings
from django.contrib.admin.util import unquote
from django.contrib.admin import helpers
from django.http import Http404
from django.utils.html import escape
from django.core.exceptions import PermissionDenied

from cms.models import Post, Category
from cms.git import repo


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
            category = Category.objects.get(slug=self.value())
            return queryset.filter(primary_category=category)


class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'subtitle', 'primary_category', 'created_at', 'language',
        'source', '_derivatives', 'uuid')

    list_filter = ('created_at', 'language', CategoriesListFilter,)
    search_fields = ('title', 'description', 'content')
    raw_id_fields = ('source', 'owner')
    fieldsets = (
        (None, {'fields': ('title', 'subtitle', 'description', 'content', )}),
        ('Meta',
            {'fields': (
                'primary_category', 'owner', 'created_at', 'source',
                'language')})
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
        return super(PostAdmin, self).add_view(
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
        return super(PostAdmin, self).change_view(
            request, object_id, form_url, extra_context)


class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', 'subtitle', 'uuid')

    def save_model(self, request, obj, form, change):
        obj.last_author = request.user
        super(CategoryAdmin, self).save_model(request, obj, form, change)


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


admin.site.register(Post, PostAdmin)
admin.site.register(Category, CategoryAdmin)
