import shutil

from django.test import TestCase

from cms.models import Post, Category
from cms.git.models import GitPage, GitCategory
from cms.utils import init_repository


class PostTestCase(TestCase):

    def delete_repo(self):
        try:
            shutil.rmtree(self.repo.path)
        except:
            pass

    def setUp(self):
        self.delete_repo()
        self.repo = init_repository()

    def tearDown(self):
        self.delete_repo()

    def test_create_post(self):
        p = Post(
            title='sample title',
            description='description',
            subtitle='subtitle',
            content='sample content')
        p.save()
        self.assertEquals(Post.objects.all().count(), 1)
        self.assertEquals(len(list(GitPage.model(self.repo).all())), 1)

        p = Post.objects.get(pk=p.pk)
        p.title = 'changed title'
        p.save()

        self.assertEquals(len(list(GitPage.model(self.repo).all())), 1)
        git_page = GitPage.model(self.repo).all()[0]
        self.assertEquals(git_page.title, 'changed title')
        self.assertEquals(git_page.uuid, p.uuid)
        self.assertEquals(git_page.subtitle, 'subtitle')
        self.assertEquals(git_page.description, 'description')
        self.assertTrue(git_page.created_at is not None)
        self.assertTrue(git_page.modified_at is not None)

        p.delete()
        self.assertEquals(Post.objects.all().count(), 0)
        self.assertEquals(len(list(GitPage.model(self.repo).all())), 0)

    def test_create_category(self):
        c = Category(
            title='sample title',
            subtitle='subtitle',
            slug='sample-title')
        c.save()
        self.assertEquals(Category.objects.all().count(), 1)
        self.assertEquals(len(list(GitCategory.model(self.repo).all())), 1)

        c = Category.objects.get(pk=c.pk)
        c.title = 'changed title'
        c.save()

        self.assertEquals(len(list(GitCategory.model(self.repo).all())), 1)
        git_cat = GitCategory.model(self.repo).all()[0]
        self.assertEquals(git_cat.title, 'changed title')
        self.assertEquals(git_cat.uuid, c.uuid)
        self.assertEquals(git_cat.subtitle, 'subtitle')

        c.delete()
        self.assertEquals(Category.objects.all().count(), 0)
        self.assertEquals(len(list(GitCategory.model(self.repo).all())), 0)
