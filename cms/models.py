from django.utils import timezone

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.template.defaultfilters import slugify

from sortedm2m.fields import SortedManyToManyField

from cms import utils, tasks
from cms.git.models import GitPage, GitCategory
from gitmodel import exceptions

ENG_UK = 'eng_UK'
SWH_TZ = 'swh_TZ'  # Swahili
SWH_KE = 'swh_KE'  # Swahili
THA_TH = 'tha_TH'  # Thai
IND_ID = 'ind_ID'  # Bahasa

LANGUAGE_CHOICES = (
    (ENG_UK, 'English (United Kingdom)'),
    (SWH_TZ, 'Swahili (Tanzania)'),
    (SWH_KE, 'Swahili (Kenya)'),
    (THA_TH, 'Thai (Thailand)'),
    (IND_ID, 'Bahasa (Indonesia)')
)


class Localisation(models.Model):
    country_code = models.CharField(
        _('2 letter country code'), max_length=2,
        help_text=(
            'See http://www.worldatlas.com/aatlas/ctycodes.htm '
            'for reference.'))
    language_code = models.CharField(
        _('3 letter language code'), max_length=3,
        help_text=(
            'See http://www.loc.gov/standards/iso639-2/php/code_list.php '
            'for reference.'))

    @classmethod
    def _for(cls, language):
        language_code, _, country_code = language.partition('_')
        localisation, _ = cls.objects.get_or_create(
            language_code=language_code, country_code=country_code)
        return localisation

    def get_code(self):
        return u'%s_%s' % (self.language_code, self.country_code)

    def __unicode__(self):
        """
        FIXME: this is probably a bad idea
        """
        language = self.get_code()
        return unicode(dict(LANGUAGE_CHOICES).get(language, language))


class Category(models.Model):
    """
    Category model to be used for categorization of content. Categories are
    high level constructs to be used for grouping and organizing content,
    thus creating a site's table of contents.
    """
    uuid = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        editable=False)
    title = models.CharField(
        max_length=200,
        help_text='Short descriptive name for this category.',
    )
    subtitle = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default='',
        help_text='Some titles may be the same and cause confusion in admin '
                  'UI. A subtitle makes a distinction.',
    )
    slug = models.SlugField(
        max_length=255,
        db_index=True,
        help_text='Short descriptive unique name for use in urls.',
    )
    last_author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        related_name='category_last_author'
    )
    localisation = models.ForeignKey(
        Localisation, blank=True, null=True)
    source = models.ForeignKey(
        'self',
        blank=True,
        null=True)
    featured_in_navbar = models.BooleanField(
        _('Featured in navigation bar'),
        default=False,
        help_text=_(
            'If checked this category will be displayed on the top'
            'navigation bar. It will always appear on the homepage.'))
    position = models.PositiveIntegerField(
        _('Position in Ordering'), null=True)

    class Meta:
        ordering = ('position', 'title',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __unicode__(self):
        if self.localisation:
            return '%s (%s)' % (self.title, self.localisation)
        else:
            return self.title

    def save(self, *args, **kwargs):
        # use django slugify filter to slugify
        if not self.slug:
            self.slug = slugify(self.title)

        super(Category, self).save(*args, **kwargs)


class Post(models.Model):

    class Meta:
        ordering = ('-created_at',)

    uuid = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        editable=False)
    title = models.CharField(
        _("Title"),
        max_length=200, help_text=_('A short descriptive title.'),
    )
    subtitle = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default='',
        help_text=_(
            'Some titles may be the same and cause confusion in admin UI. '
            'A subtitle makes a distinction.'),
    )
    slug = models.SlugField(
        max_length=255,
        db_index=True,
        help_text='Short descriptive unique name for use in urls.',
    )
    description = models.TextField(
        help_text=_(
            'A short description. More verbose than the title but'
            'limited to one or two sentences.'),
        blank=True,
        null=True,
    )
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(
        _('Created Date & Time'),
        blank=True,
        db_index=True,
        help_text=_(
            'Date and time on which this item was created. This is'
            'automatically set on creation, but can be changed subsequently.')
    )
    modified_at = models.DateTimeField(
        _('Modified Date & Time'),
        db_index=True,
        editable=False,
        auto_now=True,
        help_text=_(
            'Date and time on which this item was last modified. This'
            'is automatically set each time the item is saved.')
    )
    owner = models.ForeignKey(
        User,
        blank=True,
        null=True,
    )
    last_author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        related_name='post_last_author'
    )
    primary_category = models.ForeignKey(
        Category,
        blank=True,
        null=True,
        related_name="primary_modelbase_set",
    )

    featured = models.BooleanField(
        _('Feature on homepage'),
        default=False,
        help_text=_(
            'If checked this post will be displayed on the homepage.'))

    featured_in_category = models.BooleanField(
        _('Feature in category post listing'),
        default=False,
        help_text=_(
            'If checked this post will be displayed in the category\'s '
            'list of featured posts.'))

    related_posts = SortedManyToManyField('self', blank=True)

    localisation = models.ForeignKey(
        Localisation, blank=True, null=True)
    source = models.ForeignKey(
        'self',
        blank=True,
        null=True)

    def save(self, *args, **kwargs):
        # use django slugify filter to slugify
        if not self.slug:
            self.slug = slugify(self.title)

        # set created time to now if not already set.
        if not self.created_at:
            self.created_at = timezone.now()

        super(Post, self).save(*args, **kwargs)

    def __unicode__(self):
        if self.subtitle:
            return '%s - %s' % (self.title, self.subtitle)
        else:
            return self.title


def celery_push_to_git():
    if hasattr(settings, 'SSH_PUBKEY_PATH') and hasattr(
            settings, 'SSH_PRIVKEY_PATH'):
        tasks.push_to_git.delay(
            settings.GIT_REPO_PATH,
            settings.SSH_PUBKEY_PATH,
            settings.SSH_PRIVKEY_PATH,
            settings.SSH_PASSPHRASE)


@receiver(post_save, sender=Post)
def auto_save_post_to_git(sender, instance, created, **kwargs):
    def update_fields(page):
        page.title = instance.title
        page.subtitle = instance.subtitle
        page.slug = instance.slug
        page.description = instance.description
        page.content = instance.content
        page.created_at = instance.created_at
        page.modified_at = instance.modified_at
        page.language = (
            instance.localisation.get_code()
            if instance.localisation else None)
        page.featured_in_category = instance.featured_in_category
        page.featured = instance.featured
        page.linked_pages = [related_post.uuid
                             for related_post in instance.related_posts.all()]

        if instance.primary_category:
            category = GitCategory.get(instance.primary_category.uuid)
            page.primary_category = category

        if instance.source:
            source = GitPage.get(instance.source.uuid)
            page.source = source

        if instance.uuid:
            page.id = instance.uuid

    author = utils.get_author_from_user(instance.last_author)

    try:
        page = GitPage.get(instance.uuid)
        update_fields(page)
        page.save(
            True, message='Page updated: %s' % instance.title,
            author=author)
    except exceptions.DoesNotExist:
        page = GitPage()
        update_fields(page)
        page.save(
            True, message='Page created: %s' % instance.title,
            author=author)

        if not instance.uuid:
            Post.objects.filter(pk=instance.pk).update(uuid=page.uuid)

    utils.sync_repo()
    celery_push_to_git()


@receiver(post_delete, sender=Post)
def auto_delete_post_to_git(sender, instance, **kwargs):
    author = utils.get_author_from_user(instance.last_author)
    try:
        GitPage.delete(
            instance.uuid, True, message='Page deleted: %s' % instance.title,
            author=author)
        utils.sync_repo()
        celery_push_to_git()
    except:
        pass


@receiver(post_save, sender=Category)
def auto_save_category_to_git(sender, instance, created, **kwargs):
    def update_fields(category):
        category.title = instance.title
        category.subtitle = instance.subtitle
        category.slug = instance.slug
        category.language = (
            instance.localisation.get_code()
            if instance.localisation else None)
        category.featured_in_navbar = instance.featured_in_navbar

        if instance.source and instance.uuid:
            source = GitCategory.get(instance.source.uuid)
            category.source = source

        if instance.uuid:
            category.id = instance.uuid

    author = utils.get_author_from_user(instance.last_author)

    try:
        category = GitCategory.get(instance.uuid)
        update_fields(category)
        category.save(
            True, message='Category updated: %s' % instance.title,
            author=author)
    except exceptions.DoesNotExist:
        category = GitCategory()
        update_fields(category)
        category.save(
            True, message='Category created: %s' % instance.title,
            author=author)

        if not instance.uuid:
            Category.objects.filter(pk=instance.pk).update(uuid=category.uuid)

    utils.sync_repo()
    celery_push_to_git()


@receiver(post_delete, sender=Category)
def auto_delete_category_to_git(sender, instance, **kwargs):
    author = utils.get_author_from_user(instance.last_author)
    try:
        GitCategory.delete(
            instance.uuid, True,
            message='Category deleted: %s' % instance.title,
            author=author)
        utils.sync_repo()
        celery_push_to_git()
    except:
        pass
