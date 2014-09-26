from django.utils import timezone

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

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
        unique=True,
        help_text='Short descriptive unique name for use in urls.',
    )
    last_author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        related_name='category_last_author'
    )
    language = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        choices=LANGUAGE_CHOICES)
    source = models.ForeignKey(
        'self',
        blank=True,
        null=True)

    class Meta:
        ordering = ('title',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        # set title as slug uniquely
        self.slug = utils.generate_slug(self, Category)
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
        editable=False,
        max_length=255,
        db_index=True,
        unique=True,
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
    featured_in_category = models.BooleanField(
        _('Feature in category post listing'),
        default=False,
        help_text=_(
            'If checked this post will be displayed in the category\'s '
            'list of featured posts.'))

    language = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        choices=LANGUAGE_CHOICES)
    source = models.ForeignKey(
        'self',
        blank=True,
        null=True)

    def save(self, *args, **kwargs):
        # set title as slug uniquely
        self.slug = utils.generate_slug(self, Post)

        # set created time to now if not already set.
        if not self.created_at:
            self.created_at = timezone.now()

        super(Post, self).save(*args, **kwargs)

    def __unicode__(self):
        if self.subtitle:
            return '%s - %s' % (self.title, self.subtitle)
        else:
            return self.title


@receiver(post_save, sender=Post)
def auto_save_post_to_git(sender, instance, created, **kwargs):
    def update_fields(page, post):
        page.title = instance.title
        page.subtitle = instance.subtitle
        page.slug = instance.slug
        page.description = instance.description
        page.content = instance.content
        page.created_at = instance.created_at
        page.modified_at = instance.modified_at
        page.language = instance.language
        page.featured_in_category = instance.featured_in_category

        if instance.primary_category and instance.uuid:
            category = GitCategory.get(instance.primary_category.uuid)
            page.primary_category = category

        if instance.source and instance.uuid:
            source = GitPage.get(instance.source.uuid)
            page.source = source

    author = utils.get_author_from_user(instance.last_author)

    if created:
        page = GitPage()
        update_fields(page, instance)
        page.save(
            True, message='Page created: %s' % instance.title,
            author=author)

        # store the page's uuid on the Post instance without triggering `save`
        Post.objects.filter(pk=instance.pk).update(uuid=page.uuid)
    else:
        try:
            page = GitPage.get(instance.uuid)
            update_fields(page, instance)
            page.save(
                True, message='Page updated: %s' % instance.title,
                author=author)
        except exceptions.DoesNotExist:
            page = GitPage()
            update_fields(page, instance)
            page.save(
                True, message='Page re-created: %s' % instance.title,
                author=author)
            Post.objects.filter(pk=instance.pk).update(uuid=page.uuid)

    utils.sync_repo()
    tasks.push_to_git.delay()


@receiver(post_delete, sender=Post)
def auto_delete_post_to_git(sender, instance, **kwargs):
    author = utils.get_author_from_user(instance.last_author)
    GitPage.delete(
        instance.uuid, True, message='Page deleted: %s' % instance.title,
        author=author)
    utils.sync_repo()
    tasks.push_to_git.delay()


@receiver(post_save, sender=Category)
def auto_save_category_to_git(sender, instance, created, **kwargs):
    def update_fields(category, post):
        category.title = instance.title
        category.subtitle = instance.subtitle
        category.slug = instance.slug
        category.language = instance.language

        if instance.source and instance.uuid:
            source = GitCategory.get(instance.source.uuid)
            category.source = source

    author = utils.get_author_from_user(instance.last_author)

    if created:
        category = GitCategory()
        update_fields(category, instance)
        category.save(
            True, message='Category created: %s' % instance.title,
            author=author)

        # store the page's uuid on the Post instance without triggering `save`
        Category.objects.filter(pk=instance.pk).update(uuid=category.uuid)
    else:
        try:
            category = GitCategory.get(instance.uuid)
            update_fields(category, instance)
            category.save(
                True, message='Category updated: %s' % instance.title,
                author=author)
        except exceptions.DoesNotExist:
            category = GitCategory()
            update_fields(category, instance)
            category.save(
                True, message='Category re-updated: %s' % instance.title,
                author=author)
            Category.objects.filter(pk=instance.pk).update(uuid=category.uuid)

    utils.sync_repo()
    tasks.push_to_git.delay()


@receiver(post_delete, sender=Category)
def auto_delete_category_to_git(sender, instance, **kwargs):
    author = utils.get_author_from_user(instance.last_author)
    GitCategory.delete(
        instance.uuid, True, message='Category deleted: %s' % instance.title,
        author=author)
    utils.sync_repo()
    tasks.push_to_git.delay()
