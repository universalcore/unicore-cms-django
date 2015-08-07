import os
import uuid

from django.test import TestCase
from django.conf import settings

import responses

from slugify import slugify

from unicore.content.models import Page, Category, Localisation
from cms import utils


class BaseCmsTestCase(TestCase):

    destroy = 'KEEP_REPO' not in os.environ

    def mk_index_prefix(self):
        long_name = self.id().split('.')
        class_name, test_name = long_name[-2], long_name[-1]
        index_prefix = '%s-%s' % (class_name, test_name)
        return index_prefix.lower()

    def mk_workspace(self, working_dir='.test_repos/',
                     name=None,
                     url='http://localhost',
                     index_prefix=None,
                     auto_destroy=None,
                     author_name='Test Kees',
                     author_email='kees@example.org'):
        name = name or self.id()
        index_prefix = (
            index_prefix or
            settings.ELASTIC_GIT_INDEX_PREFIX or
            self.mk_index_prefix())
        auto_destroy = auto_destroy or self.destroy
        workspace = utils.setup_workspace(
            os.path.join(working_dir, name),
            index_prefix=index_prefix,
            es={'urls': [url]})

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

    def create_localisation(self, workspace, locale='eng_UK', **kwargs):
        data = {'locale': locale}
        data.update(kwargs)
        loc = Localisation(data)
        workspace.save(loc, u'Added localisation %s.' % (locale,))
        workspace.refresh_index()
        return loc

    def mock_create_image_response(self, host, status=201):
        def callback(request):
            return (status, {
                'Location': '/image/%s/%s' %
                    (uuid.uuid4().hex, request.headers['Slug'])}, '')

        responses.add_callback(
            responses.POST, '%s/image' % host, callback=callback)
