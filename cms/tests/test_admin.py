from django.contrib import admin
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.conf import settings

from cms.tests.base import BaseCmsTestCase
from cms.admin import (
    PostAdmin, CategoryAdmin, ContentRepositoryAdmin,
    CategoriesListFilter,
    PostSourceListFilter, CategorySourceListFilter)
from cms.models import Post, Category, ContentRepository, PublishingTarget


class BaseAdminTestCase(BaseCmsTestCase):

    def setUp(self):
        self.setUpWorkspace()

    def setUpWorkspace(self):
        self.workspace = self.mk_workspace()
        with self.active_workspace(self.workspace):
            self.category1 = Category.objects.create(title='category 1')
            self.category2 = Category.objects.create(title='category 2',
                                                     source=self.category1)
            self.category3 = Category.objects.create(title='category 3')

            self.post1 = Post.objects.create(title='post 1')
            self.post2 = Post.objects.create(title='post 2',
                                             primary_category=self.category1,
                                             source=self.post1)
            self.post3 = Post.objects.create(title='post 3',
                                             primary_category=self.category2)


class TestCategoriesListFilter(BaseAdminTestCase):

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


class TestPostSourceListFilter(BaseAdminTestCase):

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


class TestCategorySourceListFilter(BaseAdminTestCase):

    def test_filter_source_slug(self):
        filter = CategorySourceListFilter(None, {
            'source_slug': self.category1.slug,
        }, Category, CategoryAdmin)
        [category2] = filter.queryset(None, Category.objects.all())
        self.assertEqual(category2, self.category2)

    def test_filter_unknown_source(self):
        filter = CategorySourceListFilter(None, {
            'source_slug': 'foo',
        }, Category, CategoryAdmin)
        qs = filter.queryset(None, Category.objects.all())
        self.assertFalse(qs.exists())

    def test_filter_empty_source(self):
        filter = CategorySourceListFilter(None, {
            'source_slug': self.category2.slug,
        }, Category, CategoryAdmin)
        qs = filter.queryset(None, Category.objects.all())
        self.assertFalse(qs.exists())

    def test_lookups(self):
        filter = CategorySourceListFilter(None, {}, Category, CategoryAdmin)
        self.assertEqual([
            ('category-1', 'category 1'),
        ], list(filter.lookups(None, CategoryAdmin)))


class TestPostAdmin(BaseAdminTestCase):

    def test_derivatives(self):
        post_admin = PostAdmin(Post, admin)
        self.assertEqual(post_admin._derivatives(self.post1), 1)
        self.assertEqual(post_admin._derivatives(self.post2), 0)

    def test_save_model(self):
        user = User.objects.create_user('foo', 'bar')
        request = RequestFactory().get('/')
        request.user = user

        post_admin = PostAdmin(Post, admin)
        post_admin.save_model(request, self.post1, None, None)
        saved_post = Post.objects.get(pk=self.post1.pk)
        self.assertEqual(saved_post.owner, user)
        self.assertEqual(saved_post.last_author, user)


class TestCategoryAdmin(BaseAdminTestCase):

    def test_derivatives(self):
        category_admin = CategoryAdmin(Category, admin)
        self.assertEqual(category_admin._derivatives(self.category1), 1)
        self.assertEqual(category_admin._derivatives(self.category2), 0)

    def test_save_model(self):
        user = User.objects.create_user('foo', 'bar')
        request = RequestFactory().get('/')
        request.user = user

        category_admin = CategoryAdmin(Category, admin)
        category_admin.save_model(request, self.category1, None, None)
        saved_category = Category.objects.get(pk=self.category1.pk)
        self.assertEqual(saved_category.last_author, user)


class TestContentRepositoryAdmin(BaseAdminTestCase):

    def test_get_object_side_effects(self):
        """
        NOTE: What we're testing here is that for any content repository
              we're always adding the default target if the Admin
              receives a `content repository` object to display
        """
        request = RequestFactory().get('/')

        repo_admin = ContentRepositoryAdmin(ContentRepository, admin)
        content_repo = ContentRepository.objects.create(name='the repo')
        self.assertFalse(content_repo.targets.exists())
        repo_admin.get_object(request, content_repo.pk)
        [target] = content_repo.targets.all()
        self.assertEqual(target, PublishingTarget.get_default_target())

    def test_has_add_permission(self):
        repo_admin = ContentRepositoryAdmin(ContentRepository, admin)
        self.assertTrue(repo_admin.has_add_permission())
        ContentRepository.objects.create(name='the repo')
        self.assertFalse(repo_admin.has_add_permission())


class PublishingTargetAdmin(BaseAdminTestCase):
    def test_get_object_side_effects(self):
        """
        NOTE: What we're testing here is that for any Publishing Target
              activity in the admin the default target should always be
              created
        """
        self.assertFalse(PublishingTarget.objects.exists())
        default_target = PublishingTarget.get_default_target()
        self.assertEqual(default_target.name, settings.DEFAULT_TARGET_NAME)
        self.assertTrue(PublishingTarget.objects.exists())
