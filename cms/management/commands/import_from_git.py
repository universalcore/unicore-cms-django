import os
import pygit2
import shutil

from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves import input

from optparse import make_option
from gitmodel.workspace import Workspace
from unicore_gitmodels import models

from cms.models import Post, Category

from html2text import html2text


class Command(BaseCommand):
    help = 'import all the current content from a github repository'

    option_list = BaseCommand.option_list + (
        make_option(
            '--repo',
            action='store',
            dest='repo',
            default=False,
            help='The url for the github repository'),
        make_option(
            '--fake',
            action='store_true',
            dest='fake',
            default=False,
            help='Exports the data without saving to db')
    )

    def handle(self, *args, **options):
        repo_url = options.get('repo')

        if not repo_url:
            raise CommandError(
                'Missing options. --repo is reqiured.')

        print 'cloning repo..'

        repo_path = os.path.join(os.getcwd(), 'cms_temp_repo')

        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)

        self.repo = pygit2.clone_repository(
            repo_url, repo_path)

        try:
            ws = Workspace(self.repo.path, self.repo.head.name)
        except pygit2.GitError:
            ws = Workspace(self.repo.path)

        self.GitPage = ws.register_model(models.GitPageModel)
        self.GitCategory = ws.register_model(models.GitCategoryModel)

        must_delete = self.get_input_data(
            'Do you want to delete existing data? Y/n: ', 'y')

        if must_delete.lower() == 'y':
            print 'deleting existing content..'
            Post.objects.all().delete()
            Category.objects.all().delete()

        print 'creating categories..'
        for instance in self.GitCategory.all():
            Category.objects.create(
                slug=instance.slug,
                title=instance.title,
                subtitle=instance.subtitle,
                language=instance.language,
                featured_in_navbar=instance.featured_in_navbar,
                uuid=instance.uuid
            )

        print 'creating pages..'
        for instance in self.GitPage.all():
            primary_category = None
            if instance.primary_category:
                primary_category = Category.objects.get(
                    uuid=instance.primary_category.uuid)
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
                language=instance.language,
                primary_category=primary_category,
                uuid=instance.uuid
            )

        # second pass to add related fields
        for instance in self.GitPage.all():
            if instance.source:
                p = Post.objects.get(uuid=instance.uuid)
                p.source = Post.get(uuid=instance.source.uuid)
                p.save()

            if instance.linked_pages:
                p = Post.objects.get(uuid=instance.uuid)
                p.related_posts.add(*list(
                    Post.objects.filter(uuid__in=instance.linked_pages)))
                p.save()

        print 'done.'

    def get_input_data(self, message, default=None):
        raw_value = input(message)
        if default and raw_value == '':
            raw_value = default

        return raw_value.lower()
