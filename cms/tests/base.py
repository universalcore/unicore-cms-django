import os
from datetime import datetime

from django.test import TestCase
from django.conf import settings

from elasticgit import EG

from slugify import slugify

from unicore.content.models import Page, Category


class BaseCmsTestCase(TestCase):

    destroy = 'KEEP_REPO' not in os.environ

    def mk_workspace(self, working_dir='.test_repos/',
                     name=None,
                     url='https://localhost',
                     index_prefix=None,
                     auto_destroy=None,
                     author_name='Test Kees',
                     author_email='kees@example.org'):
        name = name or self.id()
        index_prefix = (
            index_prefix or
            settings.ELASTIC_GIT_INDEX_PREFIX or
            name.lower().replace('.', '-'))
        auto_destroy = auto_destroy or self.destroy
        workspace = EG.workspace(os.path.join(working_dir, name), es={
            'urls': [url],
        }, index_prefix=index_prefix)
        if auto_destroy:
            self.addCleanup(workspace.destroy)

        workspace.setup(author_name, author_email)
        while not workspace.index_ready():
            pass

        return workspace

    def create_categories(
            self, workspace, count=2, locale='eng_UK', **kwargs):
        categories = []
        for i in range(count):
            data = {}
            data.update({
                'title': u'Test Category %s' % (i,),
                'language': locale
            })
            data.update(kwargs)
            data.update({
                'slug': slugify(data['title'])
            })

            category = Category(data)
            workspace.save(
                category, u'Added category %s.' % (i,))
            categories.append(category)

        workspace.refresh_index()
        return categories

    def create_pages(
            self, workspace, count=2, timestamp_cb=None, locale='eng_UK',
            **kwargs):
        timestamp_cb = (
            timestamp_cb or (lambda i: datetime.utcnow().isoformat()))
        pages = []
        for i in range(count):
            data = {}
            data.update({
                'title': u'Test Page %s' % (i,),
                'content': u'this is sample content for pg %s' % (i,),
                'modified_at': timestamp_cb(i),
                'language': locale
            })
            data.update(kwargs)
            data.update({
                'slug': slugify(data['title'])
            })
            page = Page(data)
            workspace.save(page, message=u'Added page %s.' % (i,))
            pages.append(page)

        workspace.refresh_index()
        return pages

    def active_workspace(self, workspace):
        return self.settings(
            GIT_REPO_PATH=workspace.working_dir,
            ELASTIC_GIT_INDEX_PREFIX=workspace.index_prefix)


class OldBaseCmsTestCase(TestCase):

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
