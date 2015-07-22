from optparse import make_option
from urlparse import urljoin
import mimetypes

import requests

from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.utils.six.moves import input
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.conf import settings

from cms import tasks
from cms.models import (
    Post, Category, Localisation, auto_save_post_to_git,
    auto_save_category_to_git, auto_delete_post_to_git,
    auto_delete_category_to_git, auto_save_localisation_to_git,
    auto_delete_localisation_to_git, auto_save_related_posts_to_git)

from elasticgit import EG

from unicore.content import models as eg_models


class Command(BaseCommand):
    help = 'import all the current content from a github repository'

    option_list = BaseCommand.option_list + (
        make_option(
            '--quiet',
            action='store_true',
            dest='quiet',
            default=False,
            help='imports the data using default arguments'),
        make_option(
            '--push',
            action='store_true',
            dest='push',
            default=False,
            help='pushes changes in Git repo')
    )

    input_func = input

    def disconnect_signals(self):
        post_save.disconnect(auto_save_post_to_git, sender=Post)
        post_delete.disconnect(auto_delete_post_to_git, sender=Post)
        m2m_changed.disconnect(
            auto_save_related_posts_to_git, sender=Post.related_posts.through)

        post_save.disconnect(auto_save_category_to_git, sender=Category)
        post_delete.disconnect(auto_delete_category_to_git, sender=Category)

        post_save.disconnect(
            auto_save_localisation_to_git, sender=Localisation)
        post_delete.disconnect(
            auto_delete_localisation_to_git, sender=Localisation)

    def reconnect_signals(self):
        post_save.connect(auto_save_post_to_git, sender=Post)
        post_delete.connect(auto_delete_post_to_git, sender=Post)
        m2m_changed.connect(
            auto_save_related_posts_to_git, sender=Post.related_posts.through)

        post_save.connect(auto_save_category_to_git, sender=Category)
        post_delete.connect(auto_delete_category_to_git, sender=Category)

        post_save.connect(
            auto_save_localisation_to_git, sender=Localisation)
        post_delete.connect(
            auto_delete_localisation_to_git, sender=Localisation)

    def emit(self, message):
        if not self.quiet:
            self.stdout.write(message)

    def get_thumbor_image_file(self, host, uuid):
        url = urljoin(host, 'image/%s' % uuid)
        response = requests.get(url)
        if response.status_code == 200:
            return (
                ContentFile(response.content),
                response.headers['Content-Type'])
        return None, None

    def set_image_field(self, eg_obj, db_obj, field_name):
        '''
        Stores the image referenced by eg_obj in db_obj.field_name.
        If the image is hosted by an unknown Thumbor server, a copy
        of the image, with a new uuid, will be stored instead.

        Returns True if a copy of the image is stored, False otherwise.
        '''
        uuid = getattr(eg_obj, field_name)
        host = getattr(eg_obj, '%s_host' % field_name)
        if None in (uuid, host):
            return False

        file_obj, content_type = self.get_thumbor_image_file(host, uuid)
        if file_obj is None:
            self.emit('WARNING: image %s could not be downloaded' % uuid)
            return False

        extension = mimetypes.guess_extension(content_type)
        # NOTE: this is to handle Thumbor weirdness where it
        # returns a file extension instead of mime type.
        if extension is None:
            if content_type.startswith('.'):
                extension = content_type
            else:
                extension = ''

        file_name = '%s%s' % (field_name, extension)
        if host == settings.THUMBOR_SERVER:
            # We can serve scaled images from this host;
            # no need to re-upload image.
            upload_to = db_obj._meta.get_field(field_name).upload_to
            file_obj = ImageFile(file_obj)
            getattr(db_obj, field_name).name = '/image/%(uuid)s/%(name)s' % {
                'uuid': uuid,
                'name': upload_to(None, file_name)
            }
            setattr(db_obj, '%s_width' % field_name, file_obj.width)
            setattr(db_obj, '%s_height' % field_name, file_obj.height)
            db_obj.save()
            return False

        getattr(db_obj, field_name).save(file_name, file_obj)
        return True

    def commit_image_field(self, workspace, eg_obj, db_obj, field_name):
        field = getattr(db_obj, field_name)
        eg_obj = eg_obj.update({
            field_name: field.storage.key(field.name),
            '%s_host' % field_name: settings.THUMBOR_SERVER,
        })
        workspace.save(eg_obj, '%s %s updated: %s' % (
            eg_obj.__class__.__name__,
            field_name,
            unicode(db_obj)))

    def handle(self, *args, **options):
        self.disconnect_signals()
        self.quiet = options.get('quiet')
        self.push = options.get('push')
        workspace = EG.workspace(
            settings.GIT_REPO_PATH,
            index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
            es={'urls': [settings.ELASTICSEARCH_HOST]})

        if not self.quiet:
            must_delete = self.get_input_data(
                'Do you want to delete existing data? Y/n: ', 'y')
        else:
            must_delete = 'y'

        if must_delete.lower() == 'y':
            self.emit('deleting existing content..')
            Localisation.objects.all().delete()
            Post.objects.all().delete()
            Category.objects.all().delete()

        self.emit('creating localisations..')
        localisations = workspace.S(eg_models.Localisation).everything()
        for l in localisations:
            l = l.to_object()

            language_code, _, country_code = l.locale.partition('_')
            localisation, new = Localisation.objects.get_or_create(
                language_code=language_code,
                country_code=country_code,
                defaults={
                    'logo_text': l.logo_text,
                    'logo_description': l.logo_description,
                })

            if not new:
                continue

            if self.set_image_field(l, localisation, 'image'):
                self.commit_image_field(workspace, l, localisation, 'image')
            if self.set_image_field(l, localisation, 'logo_image'):
                self.commit_image_field(
                    workspace, l, localisation, 'logo_image')

        self.emit('creating categories..')
        categories = workspace.S(eg_models.Category).everything()

        for instance in categories:
            instance = instance.to_object()

            localisation = Localisation._for(
                instance.language) if instance.language else None
            category = Category.objects.create(
                slug=instance.slug,
                title=instance.title,
                subtitle=instance.subtitle,
                localisation=localisation,
                featured_in_navbar=instance.featured_in_navbar or False,
                uuid=instance.uuid,
                position=instance.position or 0,
            )

            if self.set_image_field(instance, category, 'image'):
                self.commit_image_field(workspace, instance, category, 'image')

        # second pass to add related fields
        for instance in categories:
            if instance.source:
                c = Category.objects.get(uuid=instance.uuid)
                c.source = Category.objects.get(uuid=instance.source)
                c.save()

        # Manually refresh stuff because the command disables signals
        workspace.refresh_index()

        self.emit('creating pages..')
        pages = workspace.S(eg_models.Page).everything()

        for instance in pages:
            instance = instance.to_object()

            primary_category = None
            if instance.primary_category:
                primary_category = Category.objects.get(
                    uuid=instance.primary_category)
            try:
                localisation = Localisation._for(
                    instance.language) if instance.language else None
                post = Post.objects.create(
                    title=instance.title,
                    subtitle=instance.subtitle,
                    slug=instance.slug,
                    description=instance.description,
                    content=instance.content,
                    created_at=instance.created_at,
                    modified_at=instance.modified_at,
                    featured_in_category=(
                        instance.featured_in_category or False),
                    featured=(
                        instance.featured or False),
                    localisation=localisation,
                    primary_category=primary_category,
                    uuid=instance.uuid,
                    position=instance.position or 0
                )
                # add the tags
                post.author_tags.add(*instance.author_tags)

                if self.set_image_field(instance, post, 'image'):
                    self.commit_image_field(workspace, instance, post, 'image')

            except ValidationError, e:  # pragma: no cover
                self.stderr.write('An error occured with: %s(%s)' % (
                    instance.title, instance.uuid))
                self.stderr.write(e)

        # Manually refresh stuff because the command disables signals
        workspace.refresh_index()

        # second pass to add related fields
        for instance in pages:
            instance = instance.to_object()

            if instance.source:
                p = Post.objects.get(uuid=instance.uuid)
                p.source = Post.objects.get(uuid=instance.source)
                p.save()

            if instance.linked_pages:
                p = Post.objects.get(uuid=instance.uuid)
                p.related_posts.add(*list(
                    Post.objects.filter(uuid__in=instance.linked_pages)))
        self.emit('done.')
        self.reconnect_signals()

        if self.push:
            tasks.push_to_git.delay(
                repo_path=workspace.working_dir,
                index_prefix=workspace.index_prefix,
                es_host=workspace.es_settings['urls'][0])

    def get_input_data(self, message, default=None):
        raw_value = self.input_func(message)
        if default and raw_value == '':
            raw_value = default

        return raw_value.lower()
