from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test.client import Client

from cms.tests.base import BaseCmsTestCase

from unicore.content import models as eg_models


class TestCustomAdminViews(BaseCmsTestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            'testuser', 'test@email.com', password='test')
        self.client = Client()
        self.client.login(username='testuser', password='test')

        self.workspace = self.mk_workspace()
        self.remote_workspace = self.mk_workspace(
            name='%s_remote' % (self.workspace.index_prefix,),
            index_prefix='%s_remote' % (self.workspace.index_prefix,))

        self.create_localisation(self.workspace)
        self.create_categories(self.workspace)
        self.create_pages(self.workspace)

        # create content for source repo
        self.create_localisation(self.remote_workspace, locale='spa_ES')
        self.create_categories(self.remote_workspace, locale='spa_ES')
        self.create_pages(self.remote_workspace, locale='spa_ES')

        self.create_localisation(self.remote_workspace, locale='fre_FR')
        self.create_categories(self.remote_workspace, locale='fre_FR')
        self.create_pages(self.remote_workspace, locale='fre_FR')

    def test_import_repo(self):
        self.workspace.refresh_index()
        self.remote_workspace.refresh_index()

        with self.settings(IMPORT_CLONE_REPO_PATH='.test_repos/',
                           GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            resp = self.client.get(reverse('import_repo'))
            self.assertEquals(resp.status_code, 302)

            self.assertEquals(
                self.workspace.S(eg_models.Localisation).everything().count, 1)
            self.assertEquals(
                self.workspace.S(eg_models.Category).everything().count, 2)
            self.assertEquals(
                self.workspace.S(eg_models.Page).everything().count, 2)

            data = {
                'index_prefix': self.remote_workspace.index_prefix,
                'locales[]': ['spa_ES']}
            resp = self.client.post(
                reverse('import_repo'), data,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

            self.workspace.refresh_index()

            self.assertEquals(
                self.workspace.S(eg_models.Localisation).everything().count, 2)
            self.assertEquals(
                self.workspace.S(eg_models.Category).everything().count, 4)
            self.assertEquals(
                self.workspace.S(eg_models.Page).everything().count, 4)

            # ensure the workspace is destroyed after importing
            self.assertFalse(self.remote_workspace.exists())
