from StringIO import StringIO

from django.core.management import call_command

from cms.models import Post, Category
from cms.tests.base import BaseCmsTestCase
from cms.management.commands import import_from_git

from unicore.content import models as eg_models


class TestImportFromGit(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_command(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            cat1, cat2 = self.create_categories(self.workspace, position=3)
            self.workspace.save(cat1.update({
                'source': cat2.uuid,
                'position': 4,
            }), 'Added source to category.')

            pages = self.create_pages(self.workspace, count=10)
            for page in pages[:8]:
                up = page.update({
                    'primary_category': cat1.uuid,
                })
                self.workspace.save(up, 'Added category.')

            [page0] = self.workspace.S(
                eg_models.Page).filter(uuid=pages[0].uuid)
            original = page0.get_object()
            updated = original.update({
                'linked_pages': [page.uuid for page in pages[:3]],
                'source': pages[4].uuid,
            })
            self.workspace.save(updated, 'Added related fields.')

            self.assertEquals(Category.objects.all().count(), 0)
            self.assertEquals(Post.objects.all().count(), 0)

            call_command('import_from_git', quiet=True)

            self.assertEquals(Category.objects.all().count(), 2)
            self.assertEquals(Post.objects.all().count(), 10)

            c = Category.objects.get(uuid=cat1.uuid)
            self.assertEquals(c.source.uuid, cat2.uuid)
            self.assertEquals(c.position, 4)

            p = Post.objects.get(uuid=page0.uuid)
            self.assertEquals(p.related_posts.count(), 3)
            self.assertEquals(p.primary_category.uuid, cat1.uuid)
            self.assertEquals(p.source.uuid, pages[4].uuid)

    def test_get_input_data(self):

        self.captured_message = None

        def patched_input_func(message):
            self.captured_message = message
            return 'y'

        command = import_from_git.Command()
        command.stdout = StringIO()
        command.input_func = patched_input_func
        command.handle(quiet=False)

        self.assertEquals(
            self.captured_message,
            'Do you want to delete existing data? Y/n: ')
        self.assertEquals(command.stdout.getvalue(), (
            'deleting existing content..'
            'creating categories..'
            'done.'))

    def test_get_input_data_with_default(self):

        self.captured_message = None

        def patched_input_func(message):
            self.captured_message = message
            return ''

        command = import_from_git.Command()
        command.stdout = StringIO()
        command.input_func = patched_input_func
        command.handle(quiet=False)

        self.assertEquals(
            self.captured_message,
            'Do you want to delete existing data? Y/n: ')
        self.assertEquals(command.stdout.getvalue(), (
            'deleting existing content..'
            'creating categories..'
            'done.'))

    def test_get_input_data_with_quiet_set(self):
        command = import_from_git.Command()
        command.stdout = StringIO()
        command.handle(quiet=True)
        self.assertEquals(command.stdout.getvalue(), '')
