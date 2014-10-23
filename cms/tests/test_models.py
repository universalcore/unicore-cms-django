import os

from django import forms
from django.conf import settings
from django.contrib import admin
from django.test.utils import override_settings

from cms.tests.base import BaseCmsTestCase
from cms.models import (
    ContentRepository, PublishingTarget, CUSTOM_REPO_LICENSE_TYPE)
from cms.admin import ContentRepositoryAdmin

from cms.git import workspace


@override_settings(GIT_REPO_URL='git@host.com/foo.git',
                   DEFAULT_TARGET_NAME='The Target')
class TestContentRepository(BaseCmsTestCase):

    def test_get_license(self):
        repo = ContentRepository(license='CC-BY-4.0')
        text = repo.get_license_text().strip()
        self.assertTrue(
            text.startswith('Attribution 4.0 International'))
        self.assertTrue(
            text.endswith(
                'Creative Commons may be contacted at creativecommons.org.'))

    def test_write_license_file(self):
        repo = ContentRepository(license='CC-BY-4.0')
        repo.save()
        file_path = os.path.join(settings.GIT_REPO_PATH, 'LICENSE')
        workspace.sync_repo_index()
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
