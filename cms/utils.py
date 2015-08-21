from urlparse import urlparse
import os.path
import shutil

from django.conf import settings
from django.core.exceptions import ValidationError

from git import Repo
from elasticgit import EG
from elasticgit.storage import StorageManager
from unicore.content.models import (
    Category, Page, Localisation as EGLocalisation)

from cms import mappings


def push_to_git(repo_path, index_prefix, es_host):
    workspace = EG.workspace(repo_path,
                             index_prefix=index_prefix,
                             es={'urls': [es_host]})
    if workspace.repo.remotes:
        repo = workspace.repo
        remote = repo.remote()
        remote.fetch()
        remote_master = remote.refs.master
        remote.push(remote_master.remote_head)


def parse_repo_name(repo_url):
    pr = urlparse(repo_url)
    _, _, repo_name_dot_ext = pr.path.rpartition('/')
    if any([
            repo_name_dot_ext.endswith('.git'),
            repo_name_dot_ext.endswith('.json')]):
        repo_name, _, _ = repo_name_dot_ext.partition('.')
        return repo_name
    return repo_name_dot_ext


def setup_workspace(repo_path, index_prefix, es={}):
    es_default = {'urls': [settings.ELASTICSEARCH_HOST]}
    es_default.update(es)
    workspace = EG.workspace(
        repo_path, index_prefix=index_prefix, es=es_default)

    branch = workspace.sm.repo.active_branch
    if workspace.im.index_exists(branch.name):
        workspace.im.destroy_index(branch.name)

    workspace.setup('ubuntu', 'dev@praekeltfoundation.org')

    while not workspace.index_ready():
        pass

    workspace.setup_custom_mapping(Category, mappings.CategoryMapping)
    workspace.setup_custom_mapping(Page, mappings.PageMapping)
    workspace.setup_custom_mapping(EGLocalisation,
                                   mappings.LocalisationMapping)

    return workspace


def clone_repo(url, name):
    repo_path = os.path.join(settings.IMPORT_CLONE_REPO_PATH, name)
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    return Repo.clone_from(url, repo_path)


def import_locale_content(repo, locales, override_if_exists=False):
    # NOTE: these are here to avoid circular imports
    from cms.management.commands.import_from_git import Command
    from cms import models
    mngmnt_command = Command()
    sm = StorageManager(repo)

    # TODO: implement override_if_exists flag

    # NOTE: we can iterate over all instances of a model
    # by using the elastic-git StorageManager directly
    for l in sm.iterate(EGLocalisation):
        if l.locale not in locales:
            continue
        language_code, _, country_code = l.locale.partition('_')
        localisation, new = models.Localisation.objects.get_or_create(
            language_code=language_code,
            country_code=country_code,
            defaults={
                'logo_text': l.logo_text,
                'logo_description': l.logo_description,
            })

        if new:
            mngmnt_command.set_image_field(l, localisation, 'image')
            mngmnt_command.set_image_field(l, localisation, 'logo_image')

    for instance in sm.iterate(Category):
        if instance.language not in locales:
            continue
        category, _ = models.Category.objects.get_or_create(
            uuid=instance.uuid,
            defaults={
                'slug': instance.slug,
                'title': instance.title,
                'subtitle': instance.subtitle,
                'localisation': localisation,
                'featured_in_navbar': instance.featured_in_navbar or False,
                'position': instance.position or 0,
            }
        )

        mngmnt_command.set_image_field(instance, category, 'image')
        category.save()

    for instance in sm.iterate(Page):
        if instance.language not in locales:
            continue
        primary_category = None
        if instance.primary_category:
            primary_category = models.Category.objects.get(
                uuid=instance.primary_category)
        try:
            post, _ = models.Post.objects.get_or_create(
                uuid=instance.uuid,
                defaults={
                    'title': instance.title,
                    'subtitle': instance.subtitle,
                    'slug': instance.slug,
                    'description': instance.description,
                    'content': instance.content,
                    'created_at': instance.created_at,
                    'modified_at': instance.modified_at,
                    'featured_in_category': (
                        instance.featured_in_category or False),
                    'featured': (
                        instance.featured or False),
                    'localisation': localisation,
                    'primary_category': primary_category,
                    'position': instance.position or 0
                }
            )
            # add the tags
            post.author_tags.add(*instance.author_tags)

            mngmnt_command.set_image_field(instance, post, 'image')

        except ValidationError:  # pragma: no cover
            print 'An error occured with: %s(%s)' % (
                instance.title, instance.uuid)

    # second pass to add related fields
    for instance in sm.iterate(Page):
        if instance.language not in locales:
            continue
        if instance.linked_pages:
            p = models.Post.objects.get(uuid=instance.uuid)
            p.related_posts.add(*list(
                models.Post.objects.filter(uuid__in=instance.linked_pages)))
