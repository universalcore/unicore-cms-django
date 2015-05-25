import os
import mock

from PIL import Image
Image.init()  # noqa

from cms.models import Post, Category, Localisation
from cms.tests.base import BaseCmsTestCase

from unicore.content import models as eg_models

from django.core.urlresolvers import reverse
from django.core.files.images import ImageFile
from django.conf import settings


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


class PostTestCase(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_create_post(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            p = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content',
                position=3)
            p.save()
            self.assertEquals(p.featured_in_category, False)
            self.assertEquals(Post.objects.all().count(), 1)
            self.assertEquals(self.workspace.S(eg_models.Page).count(), 1)

            p = Post.objects.get(pk=p.pk)
            p.title = 'changed title'
            p.save()

            self.assertEquals(self.workspace.S(eg_models.Page).count(), 1)
            [eg_page] = self.workspace.S(eg_models.Page).everything()
            self.assertEquals(eg_page.title, 'changed title')
            self.assertEquals(eg_page.uuid, p.uuid)
            self.assertEquals(eg_page.subtitle, 'subtitle')
            self.assertEquals(eg_page.description, 'description')
            self.assertEquals(eg_page.featured_in_category, False)
            self.assertEquals(eg_page.position, 3)
            self.assertTrue(eg_page.created_at is not None)
            self.assertTrue(eg_page.modified_at is not None)

            p.delete()
            self.assertEquals(Post.objects.all().count(), 0)
            self.assertEquals(self.workspace.S(eg_models.Page).count(), 0)

    def test_create_category(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='sample title',
                subtitle='subtitle',
                slug='sample-title')
            c.save()
            self.assertEquals(Category.objects.all().count(), 1)
            self.assertEquals(self.workspace.S(eg_models.Category).count(), 1)

            c = Category.objects.get(pk=c.pk)
            c.title = 'changed title'
            c.save()

            self.assertEquals(self.workspace.S(eg_models.Category).count(), 1)
            [git_cat] = self.workspace.S(eg_models.Category).everything()
            self.assertEquals(git_cat.title, 'changed title')
            self.assertEquals(git_cat.uuid, c.uuid)
            self.assertEquals(git_cat.subtitle, 'subtitle')

            c.delete()
            self.assertEquals(Category.objects.all().count(), 0)
            self.assertEquals(self.workspace.S(eg_models.Category).count(), 0)

    def test_page_with_primary_category(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='guides',
                slug='guides')
            c.save()
            c = Category.objects.get(pk=c.pk)

            p = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content')
            p.primary_category = c
            p.save()

            p = Post.objects.get(pk=p.pk)

            [git_p] = self.workspace.S(eg_models.Page).filter(uuid=p.uuid)
            self.assertEquals(git_p.primary_category, c.uuid)

    def test_page_recreated_if_not_in_git(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            p = Post(
                title='sample test title',
                description='description',
                subtitle='subtitle',
                content='sample content')
            p.save()
            p = Post.objects.get(pk=p.pk)

            # Manually delete the git page
            [git_page] = self.workspace.S(eg_models.Page).filter(uuid=p.uuid)
            self.workspace.delete(git_page.get_object(),
                                  'Removing: %s' % p.uuid)
            self.workspace.refresh_index()
            self.assertEquals(
                self.workspace.S(eg_models.Page).filter(uuid=p.uuid).count(),
                0)

            p.title = 'new title'
            p.save()

            p = Post.objects.get(pk=p.pk)
            [git_p] = self.workspace.S(eg_models.Page).filter(uuid=p.uuid)

            self.assertEquals(git_p.title, 'new title')

    def test_category_recreated_if_not_in_git(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='sample test title',
                slug='slug')
            c.save()
            c = Category.objects.get(pk=c.pk)
            [git_c] = self.workspace.S(eg_models.Category).filter(uuid=c.uuid)
            self.workspace.delete(git_c.get_object(),
                                  'Deleting: %s' % (c.uuid,))
            c.title = 'new title'
            c.save()

            c = Category.objects.get(pk=c.pk)
            [git_c] = self.workspace.S(eg_models.Category).filter(uuid=c.uuid)

            self.assertEquals(git_c.title, 'new title')

    def test_page_with_source(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='guides',
                slug='guides')
            c.save()
            c = Category.objects.get(pk=c.pk)

            p = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content',
                localisation=Localisation._for('eng_UK'))
            p.save()
            p = Post.objects.get(pk=p.pk)

            p2 = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content',
                localisation=Localisation._for('eng_US'))
            p2.primary_category = c
            p2.source = p
            p2.save()
            p2 = Post.objects.get(pk=p2.pk)

            [git_p2] = self.workspace.S(eg_models.Page).filter(uuid=p2.uuid)
            [git_p2_source] = self.workspace.S(eg_models.Page).filter(
                uuid=p2.source.uuid)
            self.assertEquals(git_p2.language, 'eng_US')
            self.assertEquals(git_p2_source.language, 'eng_UK')

            p2.source = None
            p2.primary_category = None
            p2.save()

            [git_p2] = self.workspace.S(eg_models.Page).filter(uuid=p2.uuid)
            self.assertEquals(git_p2.source, None)
            self.assertEquals(git_p2.primary_category, None)

    def test_page_featured_in_category(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            p = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content',
                localisation=Localisation._for('eng_UK'),
                featured_in_category=True)
            p.save()

            p = Post.objects.get(pk=p.pk)
            [git_p] = self.workspace.S(eg_models.Page).filter(uuid=p.uuid)
            self.assertTrue(git_p.featured_in_category)

    def test_page_get_featured(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            post = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content',
                localisation=Localisation._for('eng_UK'))
            post.save()

            featured_post = Post(
                title='featured sample title',
                description='featured description',
                subtitle='featured subtitle',
                content='featured sample content',
                localisation=Localisation._for('eng_UK'),
                featured=True)
            featured_post.save()

            post = Post.objects.get(pk=post.pk)
            [git_post] = self.workspace.S(
                eg_models.Page).filter(uuid=post.uuid)

            featured_post = Post.objects.get(pk=featured_post.pk)
            [featured_git_post] = self.workspace.S(
                eg_models.Page).filter(uuid=featured_post.uuid)

            self.assertEqual(post.featured, False)
            self.assertEquals(git_post.featured, False)

            self.assertEqual(featured_post.featured, True)
            self.assertEquals(featured_git_post.featured, True)

    def test_category_with_source(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='sample title',
                subtitle='subtitle',
                localisation=Localisation._for('afr_ZA'))
            c.save()
            c2 = Category(
                title='sample title',
                subtitle='subtitle',
                localisation=Localisation._for('eng_UK'))
            c2.save()

            c = Category.objects.get(pk=c.pk)
            c2 = Category.objects.get(pk=c2.pk)
            c2.source = c
            c2.save()

            [git_c2] = self.workspace.S(
                eg_models.Category).filter(uuid=c2.uuid)
            self.assertEquals(git_c2.language, 'eng_UK')
            [source] = self.workspace.S(
                eg_models.Category).filter(uuid=git_c2.source)
            self.assertEquals(source.language, 'afr_ZA')

            c2.source = None
            c2.save()

            [git_c2] = self.workspace.S(
                eg_models.Category).filter(uuid=c2.uuid)
            self.assertEquals(git_c2.source, None)

    def test_category_with_featured_in_navbar(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='sample title',
                subtitle='subtitle',
                localisation=Localisation._for('afr_ZA'),
                featured_in_navbar=True)
            c.save()

            c = Category.objects.get(pk=c.pk)
            [git_c] = self.workspace.S(eg_models.Category).filter(uuid=c.uuid)
            self.assertTrue(git_c.featured_in_navbar)

    def test_localisation_for_helper(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            localisations = Localisation.objects.filter(
                language_code='eng', country_code='UK')
            self.assertEqual(localisations.count(), 0)
            localisation1 = Localisation._for('eng_UK')
            localisation2 = Localisation._for('eng_UK')
            self.assertEqual(localisations.count(), 1)
            self.assertEquals(localisation1.pk, localisation2.pk)

    def test_localisation_get_code_helper(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            self.assertEqual(
                Localisation._for('eng_UK').get_code(),
                'eng_UK')

    def test_category_position_is_saved(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            c = Category(
                title='sample title',
                subtitle='subtitle',
                localisation=Localisation._for('afr_ZA'),
                featured_in_navbar=True,
                position=4)
            c.save()

        c = Category.objects.get(pk=c.pk)
        [git_c] = self.workspace.S(eg_models.Category).filter(uuid=c.uuid)
        self.assertEquals(git_c.position, 4)

    def test_page_ordering(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            Post.objects.create(
                title=u'New page',
                content=u'New page sample content',
                localisation=Localisation._for('afr_ZA'),
            )
            self.assertEquals(Post.objects.all()[0].title, 'New page')
            self.assertEquals(Post.objects.all()[0].position, 0)

            Post.objects.create(
                title=u'New page 2',
                content=u'New page sample content 2',
                localisation=Localisation._for('afr_ZA'),
            )

        self.assertEquals(Post.objects.all()[0].title, 'New page 2')
        self.assertEquals(Post.objects.all()[0].position, 0)
        self.assertEquals(Post.objects.all()[1].title, 'New page')
        self.assertEquals(Post.objects.all()[1].position, 1)

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
            p = Post.objects.create(
                title=u'New page',
                content=u'New page sample content',
                localisation=Localisation._for('afr_ZA'),
            )
            content = ImageFile(open(os.path.join(IMAGE_DIR, 'gnu.png')))
            p.image.save('gnu.png', content)
            p.save()
            p = Post.objects.get(pk=p.id)

        self.assertEqual(p.image_uuid(), 'oooooo32chars_random_idooooooooo')
        self.assertEqual(
            p.image.url,
            'http://localhost:8888/'
            'J1ZrJaChK4mv90JF9fNutNcYJ1U=/oooooo32chars_random_idooooooooo')

        [eg_page] = self.workspace.S(eg_models.Page).filter(uuid=p.uuid)
        self.assertEquals(eg_page.title, 'New page')
        self.assertEquals(eg_page.image, 'oooooo32chars_random_idooooooooo')
        self.assertEquals(eg_page.image_host, 'http://localhost:8888')

        MockPostClass.assert_called_with(
            "%s/image" % settings.THUMBOR_RW_SERVER,
            data=content.file.read(),
            headers={"Content-Type": "image/png", "Slug": 'posts/gnu.png'})

    def test_category_image(self):
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
            c = Category.objects.create(
                title=u'New Category',
                localisation=Localisation._for('afr_ZA'),
            )
            content = ImageFile(open(os.path.join(IMAGE_DIR, 'gnu.png')))
            c.image.save('gnu.png', content)
            c.save()
            c = Category.objects.get(pk=c.id)

        self.assertEqual(c.image_uuid(), 'oooooo32chars_random_idooooooooo')
        self.assertEqual(
            c.image.url,
            'http://localhost:8888/'
            'J1ZrJaChK4mv90JF9fNutNcYJ1U=/oooooo32chars_random_idooooooooo')

        [eg_category] = self.workspace.S(
            eg_models.Category).filter(uuid=c.uuid)
        self.assertEquals(eg_category.title, 'New Category')
        self.assertEquals(
            eg_category.image, 'oooooo32chars_random_idooooooooo')
        self.assertEquals(eg_category.image_host, 'http://localhost:8888')

        MockPostClass.assert_called_with(
            "%s/image" % settings.THUMBOR_RW_SERVER,
            data=content.file.read(),
            headers={
                "Content-Type": "image/png", "Slug": 'categories/gnu.png'})

    def test_post_tagging(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            p = Post.objects.create(
                title=u'New page',
                content=u'New page sample content',
                localisation=Localisation._for('afr_ZA'))

            # NOTE: reload the to get the newly assigned UUID in the signal
            #       handler with an `.update()` set operation
            reloaded_p = Post.objects.get(pk=p.pk)
            reloaded_p.author_tags.add('foo', 'bar', 'baz')
            reloaded_p.save()

            pages = self.workspace.S(eg_models.Page)
            [post] = pages.filter(uuid=reloaded_p.uuid)
            self.assertEquals(
                set(post.author_tags),
                set(['foo', 'bar', 'baz']))

    def test_related_post_saving_to_git(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            # Django's ModelForm first calls `save`, then `save_m2m` for a
            # model instance. This means the post_save signal receives the
            # model instance before its ManyToManyField has been updated.
            # The m2m_changed signal should be used to track m2m updates.

            post1 = Post(
                title='sample title',
                description='description',
                subtitle='subtitle',
                content='sample content',
                localisation=Localisation._for('eng_UK'))
            post1.save()
            post2 = Post(
                title='featured sample title',
                description='featured description',
                subtitle='featured subtitle',
                content='featured sample content',
                localisation=Localisation._for('eng_UK'),
                featured=True)
            post2.save()
            # get uuids from DB
            post1 = Post.objects.get(pk=post1.pk)
            post2 = Post.objects.get(pk=post2.pk)

            # NOTE: `save` should not be called after `add`
            # Test add
            post2.related_posts.add(post1)

            [git_post2] = self.workspace.S(
                eg_models.Page).filter(uuid=post2.uuid)
            self.assertEqual(post2.related_posts.all()[0].uuid, post1.uuid)
            self.assertEquals(git_post2.linked_pages, [post1.uuid, ])

            # Test remove
            post2.related_posts.remove(post1)

            [git_post2] = self.workspace.S(
                eg_models.Page).filter(uuid=post2.uuid)
            self.assertEquals(git_post2.linked_pages, [])

            post2.related_posts.add(post1)

            [git_post2] = self.workspace.S(
                eg_models.Page).filter(uuid=post2.uuid)
            self.assertEqual(post2.related_posts.all()[0].uuid, post1.uuid)
            self.assertEquals(git_post2.linked_pages, [post1.uuid, ])

            # Test clear
            post2.related_posts.clear()

            [git_post2] = self.workspace.S(
                eg_models.Page).filter(uuid=post2.uuid)
            self.assertEqual(git_post2.linked_pages, [])

    def test_post_saving_ensure_only_created_once(self):
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir,
                           ELASTIC_GIT_INDEX_PREFIX=self.mk_index_prefix()):
            data = {
                'title': 'sample title',
                'description': 'description',
                'subtitle': 'subtitle',
                'content': 'sample content',
                'localisation': Localisation._for('eng_UK')
            }
            related_post = Post.objects.create(**data)
            post_with_related = Post(**data)
            post_with_related.save()
            post_with_related.related_posts.add(related_post)

            m2m_commit, add_commit = list(
                self.workspace.repo.iter_commits('master'))[:2]
            self.assertEqual(m2m_commit.message, "Page updated: sample title")
            self.assertEqual(add_commit.message, "Page created: sample title")
