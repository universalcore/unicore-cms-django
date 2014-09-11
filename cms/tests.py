import os
import pygit2

from django.test import TestCase
from django.conf import settings

from cms.models import Post, GitPage


class PostTestCase(TestCase):

    def delete_repo(self):
        try:
            shutil.rmtree(self.repo.path)
        except:
            pass

    def setup_repo(self):
        try:
            self.repo = pygit2.Repository(settings.GIT_REPO_PATH_TEST)
        except:
            self.repo = pygit2.init_repository(
                settings.GIT_REPO_PATH_TEST, False)

    def setUp(self):
        self.delete_repo()
        self.setup_repo()

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
