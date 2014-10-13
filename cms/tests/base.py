from django.test import TestCase

from cms.git.models import GitPage, GitCategory


class BaseCmsTestCase(TestCase):

    def clean_repo(self):
        for p in GitPage.all():
            GitPage.delete(p.uuid, True)
        for c in GitCategory.all():
            GitCategory.delete(c.uuid, True)

    def create_categories(
            self, names=[u'Diarrhoea', u'Hygiene'], locale='eng_UK',
            featured_in_navbar=False, position=0):
        categories = []
        for name in names:
            category = GitCategory(title=name, language=locale)
            category.position = position
            category.featured_in_navbar = featured_in_navbar
            category.slug = category.slugify(name)
            category.save(True, message=u'added %s Category' % (name,))
            categories.append(GitCategory.get(category.uuid))

        return categories

    def create_pages(self, count=2, locale='eng_UK'):
        pages = []
        for i in range(count):
            page = GitPage(
                title=u'Test Page %s' % (i,),
                content=u'this is sample content for pg %s' % (i,),
                language=locale)
            page.save(True, message=u'added page %s' % (i,))
            pages.append(GitPage.get(page.uuid))

        return pages
