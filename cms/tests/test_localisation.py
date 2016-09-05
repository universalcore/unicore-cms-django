import os
import mock

from PIL import Image

from django.core.files.images import ImageFile
from django.conf import settings

from cms.constants import LANGUAGES
from cms.models import Localisation
from cms.tests.base import BaseCmsTestCase

from unicore.content import models as eg_models

from pycountry import languages

Image.init()
CURRENT_DIR = os.path.abspath(os.path.split(__file__)[0])
IMAGE_DIR = os.path.join(CURRENT_DIR, "images")


class MockedGetResponse:
    status_code = 200

    def __init__(self, url):
        """Retrieve the file on the filesytem according to the name. """
        basename = os.path.basename(url)
        filename = os.path.join(IMAGE_DIR, basename)
        if not os.path.exists(filename):
            self.status_code = 404
        else:
            self.content = open(filename, "r").read()


class MockedPostResponse:
    headers = {}


class LocalisationTestCase(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.workspace.setup_custom_mapping(eg_models.Localisation, {
            'properties': {
                'locale': {
                    'type': 'string',
                    'index': 'not_analyzed',
                }
            }
        })

    def test_create_localisation(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            l = Localisation._for('spa_ES')
            l.save()
            self.assertEquals(l.language_code, 'spa')
            self.assertEquals(l.country_code, 'ES')
            self.assertEquals(Localisation.objects.all().count(), 1)
            self.assertEquals(
                self.workspace.S(eg_models.Localisation).count(), 1)

            [eg_local] = self.workspace.S(eg_models.Localisation).everything()
            self.assertEquals(eg_local.locale, 'spa_ES')

            l.delete()
            self.assertEquals(
                self.workspace.S(eg_models.Localisation).count(), 0)

    def test_post_image(self):
        def mocked_thumbor_post_response(url, data, headers):
            response = MockedPostResponse()
            response.headers["location"] = (
                "/image/oooooo32chars_random_idooooooooo/%s" % headers["Slug"])
            return response

        def mocked_thumbor_get_response(url):
            response = MockedGetResponse(url)
            return response

        post_mock = mock.patch('django_thumborstorage.storages.requests.post')
        MockPostClass = post_mock.start()
        MockPostClass.side_effect = mocked_thumbor_post_response

        get_mock = mock.patch('django_thumborstorage.storages.requests.get')
        MockGetClass = get_mock.start()
        MockGetClass.side_effect = mocked_thumbor_get_response

        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            l = Localisation._for('spa_ES')
            content = ImageFile(open(os.path.join(IMAGE_DIR, 'gnu.png')))
            l.image.save('gnu.png', content)
            content.seek(0)
            l.logo_image.save('gnu.png', content)
            l.save()

        self.assertEqual(l.image_uuid(), 'oooooo32chars_random_idooooooooo')
        self.assertEqual(
            l.image.url,
            'http://localhost:8888/'
            'J1ZrJaChK4mv90JF9fNutNcYJ1U=/oooooo32chars_random_idooooooooo')
        self.assertEqual(
            l.logo_image_uuid(), 'oooooo32chars_random_idooooooooo')
        self.assertEqual(
            l.logo_image.url,
            'http://localhost:8888/'
            'J1ZrJaChK4mv90JF9fNutNcYJ1U=/oooooo32chars_random_idooooooooo')

        [eg_locale] = self.workspace.S(
            eg_models.Localisation).filter(locale=l.get_code())
        self.assertEquals(eg_locale.locale, 'spa_ES')
        self.assertEquals(eg_locale.image, 'oooooo32chars_random_idooooooooo')
        self.assertEquals(eg_locale.image_host, 'http://localhost:8888')
        self.assertEquals(
            eg_locale.logo_image, 'oooooo32chars_random_idooooooooo')
        self.assertEquals(eg_locale.logo_image_host, 'http://localhost:8888')

        MockPostClass.assert_called_with(
            "%s/image" % settings.THUMBOR_RW_SERVER,
            data=content.file.read(),
            headers={"Content-Type": "image/png", "Slug": 'locales/gnu.png'})

    def test_all_language_codes(self):
        for k, v in LANGUAGES.items():
            lang = languages.get(bibliographic=k)
            self.assertEqual(lang.bibliographic, k)
