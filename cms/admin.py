from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from cms.models import Post, Category


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
    list_display = ('title', 'subtitle', 'primary_category', 'created_at', 'uuid')

    list_filter = ('created_at', CategoriesListFilter,)
    search_fields = ('title', 'description', 'content')
    fieldsets = (
        (None, {'fields': ('title', 'subtitle', 'description', 'content', )}),
        ('Meta', {'fields': ('primary_category', 'owner', 'created_at')})
    )

    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user

        super(PostAdmin, self).save_model(
            request,
            obj,
            form,
            change
        )


class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', 'subtitle', 'uuid')

from django.shortcuts import render
from django.conf import settings
from cms import utils
from datetime import datetime
import pygit2


@admin.site.register_view('github/', 'Github Configuration')
def my_view(request, *args, **kwargs):
    repo = utils.init_repository()
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
