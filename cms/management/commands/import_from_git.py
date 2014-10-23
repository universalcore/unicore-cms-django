from django.core.management.base import BaseCommand
from django.utils.six.moves import input
from django.db.models.signals import post_save, post_delete

from optparse import make_option

from cms.models import (
    Post, Category, Localisation, auto_save_post_to_git,
    auto_save_category_to_git, auto_delete_post_to_git,
    auto_delete_category_to_git)
from cms.git.models import GitPage, GitCategory

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

    def handle(self, *args, **options):
        quiet = options.get('quiet')

        self.disconnect_signals()

        if not quiet:
            must_delete = self.get_input_data(
                'Do you want to delete existing data? Y/n: ', 'y')
        else:
            must_delete = 'y'

        if must_delete.lower() == 'y':
            print 'deleting existing content..'
            Post.objects.all().delete()
            Category.objects.all().delete()

        print 'creating categories..'
        categories = list(GitCategory.all())

        for instance in categories:
            Category.objects.create(
                slug=instance.slug,
                title=instance.title,
                subtitle=instance.subtitle,
                localisation=Localisation._for(instance.language),
                featured_in_navbar=instance.featured_in_navbar,
                uuid=instance.uuid,
                position=instance.position,
            )

        # second pass to add related fields
        for instance in categories:
            if instance.source:
                p = Category.objects.get(uuid=instance.uuid)
                p.source = Category.objects.get(uuid=instance.source.uuid)
                p.save()

        print 'creating pages..'
        pages = list(GitPage.all())

        for instance in pages:
            primary_category = None
            if instance.primary_category:
                primary_category = Category.objects.get(
                    uuid=instance.primary_category.uuid)
            try:
                Post.objects.create(
                    title=instance.title,
                    subtitle=instance.subtitle,
                    slug=instance.slug,
                    description=instance.description,
                    content=html2text(instance.content),
                    created_at=instance.created_at,
                    modified_at=instance.modified_at,
                    featured_in_category=instance.featured_in_category,
                    featured=instance.featured,
                    localisation=Localisation._for(instance.language),
                    primary_category=primary_category,
                    uuid=instance.uuid
                )
            except Exception, e:
                print 'An error occured with: %s(%s)' % (
                    instance.title, instance.uuid)
                print e

        # second pass to add related fields
        for instance in pages:
            if instance.source:
                p = Post.objects.get(uuid=instance.uuid)
                p.source = Post.objects.get(uuid=instance.source.uuid)
                p.save()

            if instance.linked_pages:
                p = Post.objects.get(uuid=instance.uuid)
                p.related_posts.add(*list(
                    Post.objects.filter(uuid__in=instance.linked_pages)))
                p.save()

        self.reconnect_signals()
        print 'done.'

    def get_input_data(self, message, default=None):
        raw_value = input(message)
        if default and raw_value == '':
            raw_value = default

        return raw_value.lower()
