import re
from datetime import datetime

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from ckeditor.fields import RichTextField
from django.template.defaultfilters import slugify

RE_NUMERICAL_SUFFIX = re.compile(r'^[\w-]*-(\d+)+$')


class Post(models.Model):

    class Meta:
        ordering = ('-created',)

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
    content = RichTextField(blank=True, null=True)
    created = models.DateTimeField(
        _('Created Date & Time'),
        blank=True,
        db_index=True,
        help_text=_(
            'Date and time on which this item was created. This is'
            'automatically set on creation, but can be changed subsequently.')
    )
    modified = models.DateTimeField(
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
        self.slug = self.generate_slug()

        # set created time to now if not already set.
        if not self.created:
            self.created = datetime.now()

        super(Post, self).save(*args, **kwargs)

    def __unicode__(self):
        if self.subtitle:
            return '%s - %s' % (self.title, self.subtitle)
        else:
            return self.title

    def generate_slug(self, tail_number=0):
        """
        Returns a new unique slug. Object must provide a SlugField called slug.
        URL friendly slugs are generated using django.template.defaultfilters'
        slugify. Numbers are added to the end of slugs for uniqueness.
        """
        # use django slugify filter to slugify
        slug = slugify(self.title)

        # Empty slugs are ugly (eg. '-1' may be generated) so force non-empty
        if not slug:
            slug = 'no-title'

        values_list = Post.objects.filter(
            slug__startswith=slug
        ).values_list('id', 'slug')

        # Find highest suffix
        max = -1
        for tu in values_list:
            if tu[1] == slug:
                if tu[0] == self.id:
                    # If we encounter obj and the stored slug is the same as
                    # the desired slug then return.
                    return slug

                if max == -1:
                    # Set max to indicate a collision
                    max = 0

            # Update max if suffix is greater
            match = RE_NUMERICAL_SUFFIX.match(tu[1])
            if match is not None:

                # If the collision is on self then use the existing slug
                if tu[0] == self.id:
                    return tu[1]

                i = int(match.group(1))
                if i > max:
                    max = i

        if max >= 0:
            # There were collisions
            return "%s-%s" % (slug, max + 1)
        else:
            # No collisions
            return slug
