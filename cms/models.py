import os
from datetime import datetime

from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.db.models import F
from django.db.models.signals import (
    post_save, post_delete, m2m_changed)
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from django_thumborstorage.storages import ThumborStorage

from taggit.managers import TaggableManager

from sortedm2m.fields import SortedManyToManyField

from elasticgit import EG

from git import GitCommandError

from unicore.content import models as eg_models
from cms import constants

CONTENT_REPO_LICENSE_PATH = os.path.join(
    settings.PROJECT_ROOT, '..', 'licenses')

CUSTOM_REPO_LICENSE_TYPE = '_custom'
CONTENT_REPO_LICENSES = (
    (CUSTOM_REPO_LICENSE_TYPE, 'Custom license'),
    ('CC-BY-4.0',
        'Creative Commons Attribution 4.0 International License'),
    ('CC-BY-NC-4.0',
        'Creative Commons Attribution-NonCommercial 4.0 '
        'International License'),
    ('CC-BY-NC-ND-4.0',
        'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 '
        'International License'),
    ('CC-BY-NC-SA-4.0',
        'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 '
        'International License'),
    ('CC-BY-ND-4.0',
        'Creative Commons Attribution-NoDerivatives 4.0 '
        'International License'),
    ('CC-BY-SA-4.0',
        'Creative Commons Attribution-ShareAlike 4.0 '
        'International License'),
)

DEFAULT_REPO_LICENSE = 'CC-BY-NC-ND-4.0'


def get_author_info(user):
    if not user:
        return

    return (user.get_full_name() or user.username,
            user.email or settings.DEFAULT_FROM_EMAIL)


class ContentRepository(models.Model):
    # NOTE:
    #       Support for this will grow with tickets focussing on
    #       the targets.
    #
    # This is the entity that'll grow support for what we've been
    # calling targets, it'll store things like:
    #
    # - ssh_public_key
    # - ssh_private_key
    # - ssh_passphrase

    class Meta:
        verbose_name = 'Content Repository Information'
        verbose_name_plural = 'Content Repositories Information'

    @classmethod
    def get_default_name(cls):
        if settings.GIT_REPO_URL is None:
            return None

        url_head, url_path = settings.GIT_REPO_URL.rsplit('/', 1)
        repo_name, _, dot_git = url_path.rpartition('.')
        return repo_name

    @classmethod
    def get_default_url(cls):
        return settings.GIT_REPO_URL

    name = models.CharField(
        _('The name of the content repository'),
        max_length=255, blank=True, null=True,
        default=lambda: ContentRepository.get_default_name())
    url = models.CharField(
        _('Internet address of where this content repository lives'),
        max_length=255, blank=True, null=True,
        default=lambda: ContentRepository.get_default_url())
    license = models.CharField(
        _('The license to use with this content.'),
        max_length=255, choices=CONTENT_REPO_LICENSES,
        default=DEFAULT_REPO_LICENSE,
        blank=True, null=True)
    custom_license_name = models.CharField(
        _('Name for the custom license.'),
        help_text=_('This name is for your own reference only.'),
        max_length=255, blank=True, null=True)
    custom_license_text = models.TextField(
        _('Should you decide to go with a custom license, paste '
          'the text here.'), blank=True, null=True)
    targets = models.ManyToManyField('PublishingTarget')

    def get_license_text(self):
        if self.license != CUSTOM_REPO_LICENSE_TYPE:
            return self.get_existing_license_text()
        return self.get_custom_license_text()

    def get_custom_license_text(self):
        return self.custom_license_text

    def get_existing_license_text(self):
        file_path = os.path.join(
            CONTENT_REPO_LICENSE_PATH, '%s.txt' % (self.license,))
        with open(file_path) as fp:
            return fp.read()

    def __unicode__(self):  # pragma: no cover
        if self.license == CUSTOM_REPO_LICENSE_TYPE:
            return '%s (%s)' % (self.custom_license_name,
                                self.get_license_display())
        return self.get_license_display()

    def clean(self):
        if (self.license == CUSTOM_REPO_LICENSE_TYPE and
                not all([self.custom_license_text,
                        self.custom_license_name])):
            raise ValidationError(
                'You must specify a license name & text for a custom license.')


class PublishingTarget(models.Model):

    name = models.CharField(
        _('Name for the publishing target.'), max_length=255)
    url = models.URLField(
        _('The Internet address for this target.'))

    @classmethod
    def get_default_target(cls):
        target, _ = cls.objects.get_or_create(
            name=settings.DEFAULT_TARGET_NAME)
        return target

    def __unicode__(self):  # pragma: no cover
        return self.name


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

    image = models.ImageField(
        upload_to=lambda _, filename: os.path.join('locales/', filename),
        storage=ThumborStorage(),
        height_field='image_height',
        width_field='image_width',
        blank=True, null=True)
    image_height = models.IntegerField(blank=True, null=True)
    image_width = models.IntegerField(blank=True, null=True)

    logo_image = models.ImageField(
        upload_to=lambda _, filename: os.path.join('locales/', filename),
        storage=ThumborStorage(),
        height_field='logo_image_height',
        width_field='logo_image_width',
        blank=True, null=True)
    logo_image_height = models.IntegerField(blank=True, null=True)
    logo_image_width = models.IntegerField(blank=True, null=True)

    logo_text = models.CharField(
        _("logo text"), max_length=255,
        blank=True, null=True)

    logo_description = models.CharField(
        _('logo description'), max_length=255,
        blank=True, null=True,
        help_text=_(
            'A short description of the logo for accessibility purposes.'))

    def image_uuid(self):
        if self.image:
            return self.image.storage.key(self.image.name)
        return None

    def logo_image_uuid(self):
        if self.logo_image:
            return self.logo_image.storage.key(self.logo_image.name)
        return None

    @classmethod
    def _for(cls, language):
        language_code, _, country_code = language.partition('_')
        localisation, _ = cls.objects.get_or_create(
            language_code=language_code, country_code=country_code)
        return localisation

    def get_code(self):
        return u'%s_%s' % (self.language_code, self.country_code)

    def __unicode__(self):  # pragma: no cover
        language = constants.LANGUAGES.get(self.language_code)
        country = constants.COUNTRIES.get(self.country_code)
        return u'%s (%s)' % (language, country)


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
        _('Position in Ordering'), default=0)

    image = models.ImageField(
        upload_to=lambda _, filename: os.path.join('categories/', filename),
        storage=ThumborStorage(),
        height_field='image_height',
        width_field='image_width',
        blank=True, null=True)
    image_height = models.IntegerField(blank=True, null=True)
    image_width = models.IntegerField(blank=True, null=True)

    def image_uuid(self):
        if self.image:
            return self.image.storage.key(self.image.name)
        return None

    class Meta:
        ordering = ('position', 'title',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __unicode__(self):  # pragma: no cover
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
        ordering = ('position', '-created_at',)

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
        _('Feature in latest'),
        default=False,
        help_text=_(
            'If checked this post will be displayed on the homepage '
            'under the latest section.'))

    featured_in_category = models.BooleanField(
        _('Feature in category post listing'),
        default=False,
        help_text=_(
            'If checked this post will be displayed in the category\'s '
            'list of featured posts on the homepage.'))

    related_posts = SortedManyToManyField(
        'self', blank=True, symmetrical=False,
        related_name='related_posts_set')

    localisation = models.ForeignKey(
        Localisation, blank=True, null=True)
    source = models.ForeignKey(
        'self',
        blank=True,
        null=True)
    position = models.PositiveIntegerField(
        _('Position in Ordering'), default=0)

    image = models.ImageField(
        upload_to=lambda _, filename: os.path.join('posts/', filename),
        storage=ThumborStorage(),
        height_field='image_height',
        width_field='image_width',
        blank=True, null=True)
    image_height = models.IntegerField(blank=True, null=True)
    image_width = models.IntegerField(blank=True, null=True)

    author_tags = TaggableManager()

    def image_uuid(self):
        if self.image:
            return self.image.storage.key(self.image.name)
        return None

    def save(self, *args, **kwargs):
        # use django slugify filter to slugify
        if not self.slug:
            self.slug = slugify(self.title)

        # set created time to now if not already set.
        if not self.created_at:
            self.created_at = timezone.now()

        super(Post, self).save(*args, **kwargs)

    def __unicode__(self):  # pragma: no cover
        if self.subtitle:
            return '%s - %s' % (self.title, self.subtitle)
        else:
            return self.title


@receiver(post_save, sender=ContentRepository)
def auto_save_content_repository_to_git(sender, instance, created, **kwargs):
    workspace = EG.workspace(settings.GIT_REPO_PATH,
                             index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
                             es={'urls': [settings.ELASTICSEARCH_HOST]})
    # FIXME: We don't have access to the author information here and so
    #        we cannot set it.
    workspace.sm.store_data(
        'LICENSE', instance.get_license_text(), 'Specify license.')


@receiver(m2m_changed, sender=Post.related_posts.through)
def auto_save_related_posts_to_git(sender, instance, action, **kwargs):
    if isinstance(instance, Post) and action in (
            'post_add', 'post_remove', 'post_clear'):
        auto_save_post_to_git(Post, instance, created=False)


@receiver(post_save, sender=Post)
def auto_save_post_to_git(sender, instance, created, **kwargs):
    # When saving to git, we update the uuid of the instance to ensure
    # we can find it again.
    # We need to always retrieve the latest version of the instance to
    # make sure we always have the uuid if it has been set.
    if not instance.uuid:
        instance = Post.objects.get(pk=instance.pk)

    data = {
        "title": instance.title,
        "subtitle": instance.subtitle,
        "slug": instance.slug,
        "description": instance.description,
        "content": instance.content,
        "created_at": instance.created_at.isoformat()
        if isinstance(instance.created_at, datetime) else instance.created_at,
        "modified_at": instance.modified_at.isoformat()
        if isinstance(instance.created_at, datetime) else instance.created_at,
        # TODO: We should migrate this to localisation everywhere
        "language": (
            instance.localisation.get_code()
            if instance.localisation else None),
        "featured_in_category": instance.featured_in_category,
        "featured": instance.featured,
        "position": instance.position,
        "linked_pages": [related_post.uuid
                         for related_post in instance.related_posts.all()],
        "primary_category": (
            instance.primary_category.uuid
            if instance.primary_category
            else None),
        "source": (
            instance.source.uuid
            if instance.source
            else None),
        "image": instance.image_uuid(),
        "image_host": settings.THUMBOR_SERVER,
        "author_tags": [tag.name for tag in instance.author_tags.all()],
    }

    if instance.uuid:
        data.update({'uuid': instance.uuid})

    # NOTE: If newly created always give it the highest ordering position
    if created:
        Post.objects.exclude(pk=instance.pk).update(position=F('position') + 1)

    try:
        workspace = EG.workspace(
            settings.GIT_REPO_PATH,
            index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
            es={'urls': [settings.ELASTICSEARCH_HOST]})
        [page] = workspace.S(eg_models.Page).filter(uuid=instance.uuid)
        original = page.get_object()
        updated = original.update(data)
        workspace.save(updated, 'Page updated: %s' % instance.title,
                       author=get_author_info(instance.last_author))
        workspace.refresh_index()
    except ValueError:
        page = eg_models.Page(data)
        workspace.save(page, 'Page created: %s' % instance.title,
                       author=get_author_info(instance.last_author))
        workspace.refresh_index()
        # Always update the UUID as we've just generated a new one.
        Post.objects.filter(pk=instance.pk).update(uuid=page.uuid)


@receiver(post_delete, sender=Post)
def auto_delete_post_to_git(sender, instance, **kwargs):
    workspace = EG.workspace(settings.GIT_REPO_PATH,
                             index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
                             es={'urls': [settings.ELASTICSEARCH_HOST]})
    [page] = workspace.S(eg_models.Page).filter(uuid=instance.uuid)
    # FIXME: We're attributing the delete to the person who last updated
    #        the content, which is complete incorrect.
    #
    #        We need a better abstraction for this.
    workspace.delete(
        page.get_object(), 'Page deleted: %s' % (instance.title,),
        author=get_author_info(instance.last_author))
    workspace.refresh_index()


@receiver(post_save, sender=Category)
def auto_save_category_to_git(sender, instance, created, **kwargs):

    data = {
        "title": instance.title,
        "subtitle": instance.subtitle,
        "slug": instance.slug,
        "position": instance.position,
        "language": (
            instance.localisation.get_code()
            if instance.localisation else None),
        "featured_in_navbar": instance.featured_in_navbar,
        "source": (
            instance.source.uuid
            if instance.source else None),
        "image": instance.image_uuid(),
        "image_host": settings.THUMBOR_SERVER,
    }

    if instance.uuid:
        data.update({'uuid': instance.uuid})

    workspace = EG.workspace(settings.GIT_REPO_PATH,
                             index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
                             es={'urls': [settings.ELASTICSEARCH_HOST]})
    try:
        # FIXME: This can fail if we ever store a value with None
        #        as the uuid.
        [category] = workspace.S(eg_models.Category).filter(uuid=instance.uuid)
        original = category.get_object()
        updated = original.update(data)
        workspace.save(updated, 'Category updated: %s' % instance.title,
                       author=get_author_info(instance.last_author))
        workspace.refresh_index()
    except (GitCommandError, ValueError):
        category = eg_models.Category(data)
        workspace.save(category, 'Category created: %s' % instance.title,
                       author=get_author_info(instance.last_author))
        workspace.refresh_index()
        Category.objects.filter(pk=instance.pk).update(uuid=category.uuid)


@receiver(post_delete, sender=Category)
def auto_delete_category_to_git(sender, instance, **kwargs):
    workspace = EG.workspace(settings.GIT_REPO_PATH,
                             index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
                             es={'urls': [settings.ELASTICSEARCH_HOST]})
    [category] = workspace.S(eg_models.Category).filter(uuid=instance.uuid)
    original = category.get_object()
    # FIXME: We're attributing the delete to the person who last updated
    #        the content, which is complete incorrect.
    #
    #        We need a better abstraction for this.
    workspace.delete(original, 'Category deleted: %s' % instance.title,
                     author=get_author_info(instance.last_author))
    workspace.refresh_index()


@receiver(post_save, sender=Localisation)
def auto_save_localisation_to_git(sender, instance, created, **kwargs):

    data = {
        "locale": instance.get_code(),
        "image": instance.image_uuid(),
        "image_host": settings.THUMBOR_SERVER,
        "logo_image": instance.logo_image_uuid(),
        "logo_image_host": settings.THUMBOR_SERVER,
        "logo_text": instance.logo_text,
        "logo_description": instance.logo_description
    }

    workspace = EG.workspace(settings.GIT_REPO_PATH,
                             index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
                             es={'urls': [settings.ELASTICSEARCH_HOST]})
    try:
        [localisation] = workspace.S(
            eg_models.Localisation).filter(locale=instance.get_code())
        original = localisation.get_object()
        updated = original.update(data)
        # FIXME: We don't have access to the author information here and so
        #        we cannot set it.
        workspace.save(updated, 'Localisation updated: %s' % unicode(instance))
        workspace.refresh_index()
    except (GitCommandError, ValueError):
        localisation = eg_models.Localisation(data)
        # FIXME: We don't have access to the author information here and so
        #        we cannot set it.
        workspace.save(
            localisation, 'Localisation created: %s' % unicode(instance))
        workspace.refresh_index()


@receiver(post_delete, sender=Localisation)
def auto_delete_localisation_to_git(sender, instance, **kwargs):
    workspace = EG.workspace(settings.GIT_REPO_PATH,
                             index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
                             es={'urls': [settings.ELASTICSEARCH_HOST]})
    [localisation] = workspace.S(
        eg_models.Localisation).filter(locale=instance.get_code())
    original = localisation.get_object()
    # FIXME: We don't have access to the author information here and so
    #        we cannot set it.
    workspace.delete(original, 'Localisation deleted: %s' % unicode(instance))
    workspace.refresh_index()
