from cms.models import Post, Category, Localisation
from cms.tests.base import BaseCmsTestCase

from unicore.content import models as eg_models


class PostTestCase(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_create_post(self):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        with self.settings(GIT_REPO_PATH=self.workspace.working_dir):
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
        localisations = Localisation.objects.filter(
            language_code='eng', country_code='UK')
        self.assertEqual(localisations.count(), 0)
        localisation1 = Localisation._for('eng_UK')
        localisation2 = Localisation._for('eng_UK')
        self.assertEqual(localisations.count(), 1)
        self.assertEquals(localisation1.pk, localisation2.pk)

    def test_localisation_get_code_helper(self):
        self.assertEqual(
            Localisation._for('eng_UK').get_code(),
            'eng_UK')

    def test_category_position_is_saved(self):
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
