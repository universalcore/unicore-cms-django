from cms.tests.base import BaseCmsTestCase
from cms.admin import (
    PostAdmin, CategoriesListFilter, PostSourceListFilter)
from cms.models import Post, Category


class BaseAdminListFilterTestCase(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()
        with self.active_workspace(self.workspace):
            self.category1 = Category.objects.create(title='category 1')
            self.category2 = Category.objects.create(title='category 2')
            self.category3 = Category.objects.create(title='category 3')

            self.post1 = Post.objects.create(title='post 1')
            self.post2 = Post.objects.create(title='post 2',
                                             primary_category=self.category1,
                                             source=self.post1)
            self.post3 = Post.objects.create(title='post 3',
                                             primary_category=self.category2)


class TestCategoriesListFilter(BaseAdminListFilterTestCase):

    def test_filter_knowncategory(self):
        filter = CategoriesListFilter(None, {
            'category_slug': self.category1.slug,
        }, Post, PostAdmin)
        [post2] = filter.queryset(None, Post.objects.all())
        self.assertEqual(post2, self.post2)

    def test_filter_unknown_category(self):
        filter = CategoriesListFilter(None, {
            'category_slug': 'foo',
        }, Post, PostAdmin)
        qs = filter.queryset(None, Post.objects.all())
        self.assertFalse(qs.exists())

    def test_filter_empty_category(self):
        filter = CategoriesListFilter(None, {
            'category_slug': self.category3.slug,
        }, Post, PostAdmin)
        qs = filter.queryset(None, Post.objects.all())
        self.assertFalse(qs.exists())

    def test_lookups(self):
        filter = CategoriesListFilter(None, {}, Post, PostAdmin)
        self.assertEqual([
            ('category-1', 'category 1'),
            ('category-2', 'category 2'),
            ('category-3', 'category 3'),
        ], list(filter.lookups(None, PostAdmin)))


class TestPostSourceListFilter(BaseAdminListFilterTestCase):

    def test_filter_source_slug(self):
        filter = PostSourceListFilter(None, {
            'source_slug': self.post1.slug,
        }, Post, PostAdmin)
        [post2] = filter.queryset(None, Post.objects.all())
        self.assertEqual(post2, self.post2)

    def test_filter_unknown_source(self):
        filter = PostSourceListFilter(None, {
            'source_slug': 'foo',
        }, Post, PostAdmin)
        qs = filter.queryset(None, Post.objects.all())
        self.assertFalse(qs.exists())

    def test_filter_empty_source(self):
        filter = PostSourceListFilter(None, {
            'source_slug': self.post2.slug,
        }, Post, PostAdmin)
        qs = filter.queryset(None, Post.objects.all())
        self.assertFalse(qs.exists())

    def test_lookups(self):
        filter = PostSourceListFilter(None, {}, Post, PostAdmin)
        self.assertEqual([
            ('post-1', 'post 1'),
        ], list(filter.lookups(None, PostAdmin)))


class TestCategorySourceListFilter(BaseAdminListFilterTestCase):

    pass
