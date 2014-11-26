from StringIO import StringIO

from cms.tests.base import BaseCmsTestCase
from cms.management.commands import eg_resync


class TestEGResync(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.command = eg_resync.Command()
        self.command.stdout = StringIO()

    def test_resync(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            self.create_categories(self.workspace, count=2)
            self.create_pages(self.workspace, count=2)
            # run the command
            self.command.handle()
            self.assertEquals(
                self.command.stdout.getvalue(),
                ('unicore.content.models.Page: 2 updated, 0 removed.\n'
                 'unicore.content.models.Category: 2 updated, 0 removed.\n')
            )
