from django.db.models import Q
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
            return queryset.filter(
                Q(primary_category=category) | Q(categories=category))


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'created_at', 'uuid')

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

admin.site.register(Post, PostAdmin)
admin.site.register(Category, CategoryAdmin)
