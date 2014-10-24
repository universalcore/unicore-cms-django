import os
from uuid import uuid4

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

    def create_category_data_iter(self, count=2, locale='eng_UK', **kwargs):
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
            yield data, i

    def create_categories(
            self, workspace, count=2, locale='eng_UK', **kwargs):
        categories = []
        for data, i in self.create_category_data_iter(
                count=2, locale=locale, **kwargs):
            category = Category(data)
            workspace.save(
                category, u'Added category %s.' % (i,))
            categories.append(category)

        workspace.refresh_index()
        return categories

    def create_page_data_iter(self, count=2, locale='eng_UK', **kwargs):
        for i in range(count):
            data = {}
            data.update({
                'title': u'Test Page %s' % (i,),
                'content': u'this is sample content for pg %s' % (i,),
                'language': locale
            })
            data.update(kwargs)
            data.update({
                'slug': slugify(data['title'])
            })
            yield data, i

    def create_pages(
            self, workspace, count=2, locale='eng_UK', **kwargs):
        pages = []
        for data, i in self.create_page_data_iter(
                count=count, locale=locale, **kwargs):
            page = Page(data)
            workspace.save(page, message=u'Added page %s.' % (i,))
            pages.append(page)

        workspace.refresh_index()
        return pages

    def active_workspace(self, workspace):
        return self.settings(
            GIT_REPO_PATH=workspace.working_dir,
            ELASTIC_GIT_INDEX_PREFIX=workspace.index_prefix)
