from StringIO import StringIO

from cms.tests.base import BaseCmsTestCase
from cms.management.commands import db_resync
from cms.models import Category, Post


class TestDBResync(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.command = db_resync.Command()
        self.command.stdout = StringIO()

    def test_resync_empty_db(self):
        category1, category2 = self.create_categories(self.workspace)
        page1, page2 = self.create_pages(self.workspace)

        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            # run the command
            self.command.handle()
            output = self.command.stdout.getvalue()

        self.assertTrue(
            'Deleted unicore.content.models.Page: %s' % (page1.uuid,)
            in output)
        self.assertTrue(
            'Deleted unicore.content.models.Page: %s' % (page2.uuid,)
            in output)
        self.assertTrue(
            'Deleted unicore.content.models.Category: %s' % (category1.uuid,)
            in output)
        self.assertTrue(
            'Deleted unicore.content.models.Category: %s' % (category2.uuid,)
            in output)

    def test_resync_full_db(self):

        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            # write & reload to get UUID written by signal handler
            django_cat1 = Category.objects.create(title='foo')
            django_cat1 = Category.objects.get(pk=django_cat1.pk)

            # write & reload to get UUID written by signal handler
            django_post1 = Post.objects.create(title='bar')
            django_post1 = Post.objects.get(pk=django_post1.pk)

            # run the command
            self.command.handle()
            output = self.command.stdout.getvalue()
            self.assertEqual(output.strip(), '\n'.join([
                'Kept unicore.content.models.Page: %s.' % (
                    django_post1.uuid,),
                'Kept unicore.content.models.Category: %s.' % (
                    django_cat1.uuid,),
            ]))