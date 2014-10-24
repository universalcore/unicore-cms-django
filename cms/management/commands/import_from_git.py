import sys
from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.utils.six.moves import input
from django.db.models.signals import post_save, post_delete
from django.conf import settings

from cms.models import (
    Post, Category, Localisation, auto_save_post_to_git,
    auto_save_category_to_git, auto_delete_post_to_git,
    auto_delete_category_to_git)

from elasticgit import EG

from unicore.content import models as eg_models

from html2text import html2text


class Command(BaseCommand):
    help = 'import all the current content from a github repository'

    option_list = BaseCommand.option_list + (
        make_option(
            '--quiet',
            action='store_true',
            dest='quiet',
            default=False,
            help='imports the data using default arguments'),
    )

    input_func = input

    def disconnect_signals(self):
        post_save.disconnect(auto_save_post_to_git, sender=Post)
        post_delete.disconnect(auto_delete_post_to_git, sender=Post)

        post_save.disconnect(auto_save_category_to_git, sender=Category)
        post_delete.disconnect(auto_delete_category_to_git, sender=Category)

    def reconnect_signals(self):
        post_save.connect(auto_save_post_to_git, sender=Post)
        post_delete.connect(auto_delete_post_to_git, sender=Post)

        post_save.connect(auto_save_category_to_git, sender=Category)
        post_delete.connect(auto_delete_category_to_git, sender=Category)

    def emit(self, message):
        if not self.quiet:
            self.stdout.write(message)

    def handle(self, *args, **options):
        self.disconnect_signals()
        self.quiet = options.get('quiet')
        workspace = EG.workspace(
            settings.GIT_REPO_PATH,
            index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX)

        if not self.quiet:
            must_delete = self.get_input_data(
                'Do you want to delete existing data? Y/n: ', 'y')
        else:
            must_delete = 'y'

        if must_delete.lower() == 'y':
            self.emit('deleting existing content..')
            Post.objects.all().delete()
            Category.objects.all().delete()

        self.emit('creating categories..')
        categories = workspace.S(eg_models.Category).everything()

        for instance in categories:
            Category.objects.create(
                slug=instance.slug,
                title=instance.title,
                subtitle=instance.subtitle,
                localisation=Localisation._for(instance.language),
                featured_in_navbar=instance.featured_in_navbar or False,
                uuid=instance.uuid,
                position=instance.position,
            )

        # second pass to add related fields
        for instance in categories:
            if instance.source:
                c = Category.objects.get(uuid=instance.uuid)
                c.source = Category.objects.get(uuid=instance.source)
                c.save()

        # Manually refresh stuff because the command disables signals
        workspace.refresh_index()

        pages = workspace.S(eg_models.Page).everything()
        for instance in pages:
            primary_category = None
            if instance.primary_category:
                primary_category = Category.objects.get(
                    uuid=instance.primary_category)
            try:
                Post.objects.create(
                    title=instance.title,
                    subtitle=instance.subtitle,
                    slug=instance.slug,
                    description=instance.description,
                    content=html2text(instance.content),
                    created_at=instance.created_at,
                    modified_at=instance.modified_at,
                    featured_in_category=(
                        instance.featured_in_category or False),
                    featured=(
                        instance.featured or False),
                    localisation=Localisation._for(instance.language),
                    primary_category=primary_category,
                    uuid=instance.uuid
                )
            except ValidationError, e:  # pragma: no cover
                self.stderr.write('An error occured with: %s(%s)' % (
                    instance.title, instance.uuid))
                self.stderr.write(e)

        # Manually refresh stuff because the command disables signals
        workspace.refresh_index()

        # second pass to add related fields
        for instance in pages:
            if instance.source:
                p = Post.objects.get(uuid=instance.uuid)
                p.source = Post.objects.get(uuid=instance.source)
                p.save()

            if instance.linked_pages:
                p = Post.objects.get(uuid=instance.uuid)
                p.related_posts.add(*list(
                    Post.objects.filter(uuid__in=instance.linked_pages)))
                p.save()
        self.emit('done.')
        self.reconnect_signals()

    def get_input_data(self, message, default=None):
        raw_value = self.input_func(message)
        if default and raw_value == '':
            raw_value = default

        return raw_value.lower()
