from cms.tests.base import BaseCmsTestCase
from cms.models import ContentRepository


class TestContentRepository(BaseCmsTestCase):

    def test_get_license(self):
        repo = ContentRepository(
            license='CC-BY-4.0')
        text = repo.get_license_text().strip()
        self.assertTrue(
            text.startswith('Attribution 4.0 International'))
        self.assertTrue(
            text.endswith(
                'Creative Commons may be contacted at creativecommons.org.'))
