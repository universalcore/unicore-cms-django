import re
import uuid
from StringIO import StringIO

from django.core.management import call_command
from django.core.files.base import ContentFile

import mock
import responses

from cms.models import Post, Category, Localisation
from cms.tests.base import BaseCmsTestCase
from cms.management.commands import import_from_git

from unicore.content import models as eg_models


class TestImportFromGit(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def mock_get_image_response(self, host, status=200, body='',
                                content_type='image/png'):
        responses.add(
            responses.GET,
            re.compile(r'%s/image/\w{32}' % host),
            body=body,
            status=status,
            content_type=content_type)

    def mock_get_on_redirect_image_response(self, host, status=200, body='',
                                            content_type='image/png'):
        responses.add(
            responses.GET,
            re.compile(
                r'%s/image/\w{32}/(locales|posts|categories)/.+' % host),
            body=body,
            status=status,
            content_type=content_type)

    def mock_create_image_response(self, host, status=201):
        def callback(request):
            return (status, {
                'Location': '/image/%s/%s' %
                    (uuid.uuid4().hex, request.headers['Slug'])}, '')

        responses.add_callback(
            responses.POST, '%s/image' % host, callback=callback)

    @mock.patch.object(import_from_git.Command, 'set_image_field')
    @mock.patch.object(import_from_git.Command, 'commit_image_field')
    def test_command(self, mock_set_image_field, mock_commit_image_field):
        mock_set_image_field.return_value = True
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            lang1 = eg_models.Localisation({'locale': 'spa_ES'})
            lang2 = eg_models.Localisation({
                'locale': 'fre_FR',
                'image': uuid.uuid4().hex,
                'image_host': 'http://localhost:8888',
                'logo_image': uuid.uuid4().hex,
                'logo_image_host': 'http://localhost:8888',
                'logo_text': 'text foo',
                'logo_description': 'description foo'})
            self.workspace.save(lang1, 'Added spanish language')
            self.workspace.save(lang2, 'Added french language')

            cat1, cat2 = self.create_categories(self.workspace, position=3)
            self.workspace.save(cat1.update({
                'source': cat2.uuid,
                'position': 4,
            }), 'Added source to category.')

            pages = self.create_pages(self.workspace, count=10)
            for page in pages[:8]:
                up = page.update({
                    'primary_category': cat1.uuid,
                    'author_tags': ['foo', 'bar', 'baz'],
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
            self.assertEquals(
                set(p.author_tags.names()),
                set(['foo', 'bar', 'baz']))

            self.assertEquals(Localisation.objects.all().count(), 3)
            self.assertEquals(mock_set_image_field.call_count, 16)
            self.assertEquals(mock_commit_image_field.call_count, 16)
            l = Localisation.objects.get(
                language_code='fre', country_code='FR')
            self.assertEquals(lang2.logo_text, l.logo_text)
            self.assertEquals(lang2.logo_description, l.logo_description)

    def test_get_input_data(self):

        self.captured_message = None

        def patched_input_func(message):
            self.captured_message = message
            return 'y'

        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            command = import_from_git.Command()
            command.stdout = StringIO()
            command.input_func = patched_input_func
            command.handle(quiet=False)

        self.assertEquals(
            self.captured_message,
            'Do you want to delete existing data? Y/n: ')
        self.assertEquals(command.stdout.getvalue(), (
            'deleting existing content..'
            'creating localisations..'
            'creating categories..'
            'creating pages..'
            'done.'))

    def test_get_input_data_with_default(self):

        self.captured_message = None

        def patched_input_func(message):
            self.captured_message = message
            return ''

        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            command = import_from_git.Command()
            command.stdout = StringIO()
            command.input_func = patched_input_func
            command.handle(quiet=False)

        self.assertEquals(
            self.captured_message,
            'Do you want to delete existing data? Y/n: ')
        self.assertEquals(command.stdout.getvalue(), (
            'deleting existing content..'
            'creating localisations..'
            'creating categories..'
            'creating pages..'
            'done.'))

    def test_get_input_data_with_quiet_set(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            command = import_from_git.Command()
            command.stdout = StringIO()
            command.handle(quiet=True)
            self.assertEquals(command.stdout.getvalue(), '')

    @responses.activate
    def test_get_thumbor_image_file(self):
        host = 'http://localhost:8888'
        key = uuid.uuid4().hex
        command = import_from_git.Command()
        self.mock_get_image_response(host=host)

        file_obj, content_type = command.get_thumbor_image_file(
            host=host, uuid=key)
        self.assertIsInstance(file_obj, ContentFile)
        self.assertEqual(content_type, 'image/png')

        responses.reset()
        self.mock_get_image_response(host=host, status=404)

        file_obj, content_type = command.get_thumbor_image_file(
            host=host, uuid=key)
        self.assertIs(file_obj, None)
        self.assertIs(file_obj, None)

    @responses.activate
    def test_set_image_field(self):
        command = import_from_git.Command()
        command.stdout = StringIO()
        command.quiet = False
        command.disconnect_signals()

        host = 'http://localhost:8888'
        # 1 x 1 bitmap image
        body = 'BM:\x00\x00\x00\x00\x00\x00\x006\x00\x00\x00(\x00\x00\x00' \
               '\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00' \
               '\x00\x00\x04\x00\x00\x00\x13\x0b\x00\x00\x13\x0b\x00\x00' \
               '\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\x00'
        content_type = 'image/x-ms-bmp'
        self.mock_get_image_response(
            host=host, content_type=content_type, body=body)
        self.mock_get_on_redirect_image_response(
            host=host, content_type=content_type, body=body)
        self.mock_create_image_response(host=host)

        eg_obj = eg_models.Localisation({
            'locale': 'fre_FR',
            'image': uuid.uuid4().hex,
            'image_host': host})
        # set image dimensions to make sure we reassign them
        db_obj = Localisation.objects.create(
            language_code='fre', country_code='FR',
            image_width=5, image_height=5)

        # image exists and is on same server
        with self.settings(THUMBOR_SERVER=host):
            self.assertFalse(command.set_image_field(eg_obj, db_obj, 'image'))
        db_obj = Localisation.objects.get(
            language_code='fre', country_code='FR')
        self.assertEqual(command.stdout.getvalue(), '')
        self.assertTrue(
            re.match(r'/image/\w{32}/locales/image.bmp', db_obj.image.name))
        self.assertEqual(db_obj.image_width, 1)
        self.assertEqual(db_obj.image_height, 1)

        command.stdout = StringIO()
        db_obj.image = None
        db_obj.save()

        # image exists but it's on another server
        with self.settings(THUMBOR_SERVER='another-server.com'):
            self.assertTrue(command.set_image_field(eg_obj, db_obj, 'image'))
        self.assertEqual(command.stdout.getvalue(), '')
        self.assertTrue(
            re.match(r'/image/\w{32}/locales/image.bmp', db_obj.image.name))
        self.assertEqual(db_obj.image_width, 1)
        self.assertEqual(db_obj.image_height, 1)

        responses.reset()
        self.mock_get_image_response(host=host, status=404)
        command.stdout = StringIO()

        # image does not exist on server
        self.assertFalse(command.set_image_field(eg_obj, db_obj, 'image'))
        self.assertTrue(command.stdout.getvalue().startswith('WARNING: image'))

        # no image set in Git
        command.stdout = StringIO()
        self.assertFalse(command.set_image_field(eg_obj, db_obj, 'logo_image'))
        self.assertFalse(db_obj.logo_image)

        responses.reset()
        self.mock_get_image_response(host=host, content_type='.bmp')

        # check that mimetype/extension mixup gets handled
        with  \
                mock.patch.object(db_obj.image, 'save') as mock_save_image, \
                self.settings(THUMBOR_SERVER='another-server.com'):
            self.assertTrue(command.set_image_field(eg_obj, db_obj, 'image'))
            file_name = mock_save_image.call_args[0][0]
            self.assertTrue(file_name.endswith('.bmp'))

        command.reconnect_signals()

    def test_commit_image_field(self):
        command = import_from_git.Command()
        command.stdout = StringIO()
        command.quiet = False
        command.disconnect_signals()

        eg_obj = self.create_localisation(
            self.workspace,
            locale='fre_FR',
            image=uuid.uuid4().hex,
            image_host='another-server.com')
        new_uuid = uuid.uuid4().hex
        db_obj = Localisation.objects.create(
            language_code='fre', country_code='FR',
            image_width=5, image_height=5,
            image='/image/%s/locales/image.bmp' % (new_uuid,))

        with self.settings(THUMBOR_SERVER='http://localhost:8888'):
            command.commit_image_field(self.workspace, eg_obj, db_obj, 'image')
        self.workspace.refresh_index()
        [eg_obj] = self.workspace.S(
            eg_models.Localisation).filter(uuid=eg_obj.uuid)
        self.assertEqual(eg_obj.image, new_uuid)
        self.assertEqual(eg_obj.image_host, 'http://localhost:8888')

        command.reconnect_signals()
