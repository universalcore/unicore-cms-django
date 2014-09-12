import shutil

from django.test import TestCase

from cms.models import Post, GitPage
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
            content='sample content')
        p.save()
        self.assertTrue(Post.objects.all(), 1)
        self.assertEquals(len(list(GitPage.model(self.repo).all())), 1)

        p = Post.objects.get(pk=p.pk)
        p.title = 'changed title'
        p.save()

        self.assertEquals(len(list(GitPage.model(self.repo).all())), 1)
        git_page = GitPage.model(self.repo).all()[0]
        self.assertEquals(git_page.title, 'changed title')
        self.assertEquals(git_page.id, p.uuid)
        p = Post.objects.get(pk=p.id)
