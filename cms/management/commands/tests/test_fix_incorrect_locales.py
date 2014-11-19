from django.core.management import call_command

from cms.models import Post, Category, Localisation
from cms.tests.base import BaseCmsTestCase

from unicore.content import models as eg_models


class TestFixIncorrectLocales(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()

        self.workspace.setup_custom_mapping(eg_models.Category, {
            'properties': {
                'language': {
                    'type': 'string',
                    'index': 'not_analyzed',
                }
            }
        })
        self.workspace.setup_custom_mapping(eg_models.Page, {
            'properties': {
                'language': {
                    'type': 'string',
                    'index': 'not_analyzed',
                }
            }
        })

    def create_django_categories(self, locale='eng_GB', count=2):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            for i in range(count):
                Category.objects.create(
                    title=u'Test category %s' % (i,),
                    localisation=Localisation._for(locale))

    def create_django_posts(self, locale='eng_GB', count=2):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            for i in range(count):
                Post.objects.create(
                    title=u'Test category %s' % (i,),
                    content=u'Sample content for page %s' % (i,),
                    localisation=Localisation._for(locale))

    def test_command(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            self.create_django_categories(locale='eng_UK', count=3)
            self.create_django_categories(locale='swh_TZ', count=3)
            self.create_django_categories(locale='swh_KE', count=3)
            self.create_django_posts(locale='eng_UK', count=3)
            self.create_django_posts(locale='swh_TZ', count=3)
            self.create_django_posts(locale='swh_KE', count=3)

            self.workspace.refresh_index()

            pages = self.workspace.S(eg_models.Page).filter(language='eng_UK')
            self.assertEqual(len(pages), 3)
            pages = self.workspace.S(eg_models.Page).filter(language='eng_GB')
            self.assertEqual(len(pages), 0)

            pages = self.workspace.S(eg_models.Page).filter(language='swh_TZ')
            self.assertEqual(len(pages), 3)
            pages = self.workspace.S(eg_models.Page).filter(language='swa_TZ')
            self.assertEqual(len(pages), 0)

            pages = self.workspace.S(eg_models.Page).filter(language='swh_KE')
            self.assertEqual(len(pages), 3)
            pages = self.workspace.S(eg_models.Page).filter(language='swa_KE')
            self.assertEqual(len(pages), 0)

            self.assertEquals(Category.objects.filter(
                localisation__country_code='UK').count(), 3)
            self.assertEquals(Category.objects.filter(
                localisation__country_code='GB').count(), 0)

            self.assertEquals(Category.objects.filter(
                localisation__language_code='swh').count(), 6)
            self.assertEquals(Category.objects.filter(
                localisation__language_code='swa').count(), 0)

            self.assertEquals(Post.objects.filter(
                localisation__country_code='UK').count(), 3)
            self.assertEquals(Post.objects.filter(
                localisation__country_code='GB').count(), 0)

            self.assertEquals(Post.objects.filter(
                localisation__language_code='swh').count(), 6)
            self.assertEquals(Post.objects.filter(
                localisation__language_code='swa').count(), 0)

            call_command('fix_incorrect_locales')

            self.workspace.refresh_index()

            self.assertEquals(Category.objects.filter(
                localisation__country_code='UK').count(), 0)
            self.assertEquals(Category.objects.filter(
                localisation__country_code='GB').count(), 3)

            self.assertEquals(Category.objects.filter(
                localisation__language_code='swh').count(), 0)
            self.assertEquals(Category.objects.filter(
                localisation__language_code='swa').count(), 6)

            self.assertEquals(Post.objects.filter(
                localisation__country_code='UK').count(), 0)
            self.assertEquals(Post.objects.filter(
                localisation__country_code='GB').count(), 3)

            self.assertEquals(Post.objects.filter(
                localisation__language_code='swh').count(), 0)
            self.assertEquals(Post.objects.filter(
                localisation__language_code='swa').count(), 6)

            pages = self.workspace.S(eg_models.Page).filter(language='eng_UK')
            self.assertEqual(len(pages), 0)
            pages = self.workspace.S(eg_models.Page).filter(language='eng_GB')
            self.assertEqual(len(pages), 3)

            pages = self.workspace.S(eg_models.Page).filter(language='swh_TZ')
            self.assertEqual(len(pages), 0)
            pages = self.workspace.S(eg_models.Page).filter(language='swa_TZ')
            self.assertEqual(len(pages), 3)

            pages = self.workspace.S(eg_models.Page).filter(language='swh_KE')
            self.assertEqual(len(pages), 0)
            pages = self.workspace.S(eg_models.Page).filter(language='swa_KE')
            self.assertEqual(len(pages), 3)
