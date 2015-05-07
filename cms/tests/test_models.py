import os

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.test.utils import override_settings

from cms.tests.base import BaseCmsTestCase
from cms.models import (
    ContentRepository, PublishingTarget, CUSTOM_REPO_LICENSE_TYPE,
    Post, get_author_info)
from cms.admin import ContentRepositoryAdmin


class TestHelpers(BaseCmsTestCase):

    def test_get_author_info_none(self):
        self.assertEqual(None, get_author_info(None))

    def test_get_author_info_fallbacks(self):
        user = User.objects.create_user('foo', None, 'bar')
        self.assertEqual(
            (user.username, settings.DEFAULT_FROM_EMAIL),
            get_author_info(user))

    def test_get_author_info(self):
        user = User.objects.create_user('foo', 'foo@example.org', 'bar')
        user.first_name = 'Foo'
        user.last_name = 'Bar'
        user.save()
        self.assertEqual(
            ('Foo Bar', 'foo@example.org'),
            get_author_info(user))


@override_settings(GIT_REPO_URL='git@host.com/foo.git',
                   DEFAULT_TARGET_NAME='The Target')
class TestContentRepository(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_default_license(self):
        repo = ContentRepository.objects.create()
        self.assertTrue(repo.get_license_text())

    def test_get_license(self):
        repo = ContentRepository.objects.create(license='CC-BY-4.0')
        text = repo.get_license_text().strip()
        self.assertTrue(
            text.startswith('Attribution 4.0 International'))
        self.assertTrue(
            text.endswith(
                'Creative Commons may be contacted at creativecommons.org.'))

    def test_write_license_file(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
            repo = ContentRepository(license='CC-BY-4.0')
            repo.save()
            file_path = os.path.join(settings.GIT_REPO_PATH, 'LICENSE')
            with open(file_path, 'r') as fp:
                license_text = fp.read()
            self.assertEqual(license_text, repo.get_license_text())

    def test_custom_license_text(self):
        repo = ContentRepository(
            license=CUSTOM_REPO_LICENSE_TYPE,
            custom_license_name='Foo',
            custom_license_text='Bar')
        repo.save()
        self.assertEqual(repo.get_license_text(), 'Bar')
        self.assertEqual(unicode(repo), 'Foo (Custom license)')

    def test_validation(self):
        self.assertRaises(
            forms.ValidationError,
            ContentRepository(license=CUSTOM_REPO_LICENSE_TYPE).full_clean)
        self.assertRaises(
            forms.ValidationError,
            ContentRepository(
                license=CUSTOM_REPO_LICENSE_TYPE,
                custom_license_name='Foo').full_clean)
        self.assertRaises(
            forms.ValidationError,
            ContentRepository(
                license=CUSTOM_REPO_LICENSE_TYPE,
                custom_license_text='Bar').full_clean)

    def test_setting_of_target_fields(self):
        cr = ContentRepository(license='CC-BY-4.0')
        cr.save()
        self.assertEqual(cr.url, 'git@host.com/foo.git')
        self.assertEqual(cr.name, 'foo')
        self.assertFalse(cr.targets.exists())
        self.assertEqual(PublishingTarget.objects.count(), 0)

        model_admin = ContentRepositoryAdmin(ContentRepository, admin)
        obj = model_admin.get_object(None, cr.pk)
        self.assertEqual(obj.url, 'git@host.com/foo.git')
        self.assertEqual(obj.name, 'foo')
        self.assertEqual(PublishingTarget.objects.count(), 1)
        [target] = obj.targets.all()
        self.assertEqual(target.name, 'The Target')

    def test_linked_pages_asymmetry(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            post1 = Post.objects.create(title='post 1')
            post2 = Post.objects.create(title='post 2')
            post2.related_posts.add(post1)
            post2.save()
            self.assertEqual(post2.related_posts.count(), 1)
            self.assertEqual(post1.related_posts.count(), 0)


class TestPublishingTarget(BaseCmsTestCase):

    def test_get_default_target(self):
        self.assertFalse(PublishingTarget.objects.exists())
        default_target = PublishingTarget.get_default_target()
        self.assertEqual(default_target.name, settings.DEFAULT_TARGET_NAME)
        self.assertTrue(PublishingTarget.objects.exists())
