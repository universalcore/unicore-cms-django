import os

from cms.tests.base import BaseCmsTestCase
from cms.models import ContentRepository
from django.conf import settings
from cms.git import workspace


class TestContentRepository(BaseCmsTestCase):

    def test_get_license(self):
        repo = ContentRepository(existing_license='CC-BY-4.0')
        text = repo.get_license_text().strip()
        self.assertTrue(
            text.startswith('Attribution 4.0 International'))
        self.assertTrue(
            text.endswith(
                'Creative Commons may be contacted at creativecommons.org.'))

    def test_write_license_file(self):
        repo = ContentRepository(existing_license='CC-BY-4.0')
        repo.save()
        file_path = os.path.join(settings.GIT_REPO_PATH, 'LICENSE')
        workspace.sync_repo_index()
        with open(file_path, 'r') as fp:
            license_text = fp.read()
        self.assertEqual(license_text, repo.get_license_text())

    def test_custom_license_text(self):
        repo = ContentRepository(custom_license='Foo')
        repo.save()
        self.assertEqual(repo.get_license_text(), 'Foo')
