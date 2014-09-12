from django.utils import timezone

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from gitmodel.workspace import Workspace
from gitmodel import fields, models as gitmodels
from cms import utils


class FilterMixin(object):

    @classmethod
    def filter(cls, **fields):
        items = list(cls.all())
        for field, value in fields.items():
            if hasattr(cls, field):
                items = [a for a in items if getattr(a, field) == value]
            else:
                raise Exception('invalid field %s' % field)
        return items


class GitCategory(FilterMixin, gitmodels.GitModel):
    slug = fields.SlugField(required=True)
    title = fields.CharField(required=True)

    @property
    def uuid(self):
        return self.id

    def __eq__(self, other):
        if not other:
            return False

        if isinstance(other, dict):
            return self.slug == other['slug']
        return self.slug == other.slug

    def __ne__(self, other):
        if not other:
            return True

        if isinstance(other, dict):
            return self.slug != other['slug']
        return self.slug != other.slug

    def to_dict(self):
        return {
            'uuid': self.uuid,
            'slug': self.slug,
            'title': self.title,
        }

    @classmethod
    def model(cls, repo):
        try:
            ws = Workspace(repo.path, repo.head.name)
        except:
            ws = Workspace(repo.path)
        return ws.register_model(cls)


class GitPage(FilterMixin, gitmodels.GitModel):
    slug = fields.SlugField(required=True)
    title = fields.CharField(required=True)
    subtitle = fields.CharField(required=False)
    description = fields.CharField(required=False)
    content = fields.CharField(required=False)
    created_at = fields.DateTimeField(required=False)
    modified_at = fields.DateTimeField(required=False)
    published = fields.BooleanField(default=True)
    primary_category = fields.RelatedField(GitCategory, required=False)

    @property
    def uuid(self):
        return self.id

    def to_dict(self):
        primary_category = self.primary_category.to_dict()\
            if self.primary_category else None

        return {
            'uuid': self.uuid,
            'slug': self.slug,
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description,
            'content': self.content,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'published': self.published,
            'primary_category': primary_category,
        }

    @classmethod
    def model(cls, repo):
        try:
            ws = Workspace(repo.path, repo.head.name)
        except:
            ws = Workspace(repo.path)
        return ws.register_model(cls)


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
            'Some titles may be the same and cause confusion in admin'
            'UI. A subtitle makes a distinction.'),
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
    categories = models.ManyToManyField(
        'category.Category',
        blank=True,
        null=True,
        help_text=_('Categorizing this item.')
    )
    primary_category = models.ForeignKey(
        'category.Category',
        blank=True,
        null=True,
        help_text=_(
            "Primary category for this item. Used to determine the"
            "object's absolute/default URL."),
        related_name="primary_modelbase_set",
    )
    tags = models.ManyToManyField(
        'category.Tag',
        blank=True,
        null=True,
        help_text=_('Tag this item.')
    )

    def save(self, *args, **kwargs):
        # set title as slug uniquely
        self.slug = utils.generate_slug(self)

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

    repo = utils.init_repository()
    if created:
        Page = GitPage.model(repo)
        page = Page()
        update_fields(page, instance)
        page.save(True, message='Page created: %s' % instance.title)

        # store the page's uuid on the Post instance without triggering `save`
        Post.objects.filter(pk=instance.pk).update(uuid=page.uuid)
    else:
        Page = GitPage.model(repo)
        page = Page.get(instance.uuid)
        update_fields(page, instance)
        page.save(True, message='Page updated: %s' % instance.title)

    utils.sync_repo()


@receiver(post_delete, sender=Post)
def auto_delete_post_to_git(sender, instance, **kwargs):
    repo = utils.init_repository()
    Page = GitPage.model(repo)
    Page.delete(
        instance.uuid, True, message='Page deleted: %s' % instance.title)
