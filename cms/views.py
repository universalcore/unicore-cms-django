import json
import os.path
import shutil

from urlparse import urlparse

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from git import Repo
from elasticgit import EG

from cms import mappings, models
from cms.management.commands.import_from_git import Command

from unicore.content.models import (
    Category, Page, Localisation as EGLocalisation)


def parse_repo_name(repo_url):
    pr = urlparse(repo_url)
    _, _, repo_name_dot_ext = pr.path.rpartition('/')
    if any([
            repo_name_dot_ext.endswith('.git'),
            repo_name_dot_ext.endswith('.json')]):
        repo_name, _, _ = repo_name_dot_ext.partition('.')
        return repo_name
    return repo_name_dot_ext


def setup_workspace(repo_path, index_prefix):
    workspace = EG.workspace(
        repo_path, index_prefix=index_prefix,
        es={'urls': settings.ELASTICSEARCH_HOST})

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


@csrf_exempt
@login_required
def import_clone_repo(request, *args, **kwargs):
    if request.is_ajax():
        url = request.POST.get('repo_url')
        if not url:
            return HttpResponse(
                'Invalid repo_url',
                status=400,
                mimetype='application/json')
        repo_index = 'import-repo-prefix-%s' % parse_repo_name(url)
        repo = clone_repo(url, repo_index)
        ws = setup_workspace(repo.working_dir, repo_index)
        ws.sync(EGLocalisation)
        ws.sync(Category)
        ws.sync(Page)

        localisations = [
            l.to_object().locale for l in ws.S(EGLocalisation).everything()]

        return HttpResponse(
            json.dumps({'locales': localisations, 'index_prefix': repo_index}),
            mimetype='application/json')
    return redirect('/github/import/choose/')


def import_locale_content(workspace, locale):
    mngmnt_command = Command()

    [l] = workspace.S(EGLocalisation).filter(locale=locale)
    l = l.to_object()
    language_code, _, country_code = l.locale.partition('_')
    localisation, new = models.Localisation.objects.get_or_create(
        language_code=language_code,
        country_code=country_code,
        defaults={
            'logo_text': l.logo_text,
            'logo_description': l.logo_description,
        })

    if new:
        if mngmnt_command.set_image_field(l, localisation, 'image'):
            mngmnt_command.commit_image_field(
                workspace, l, localisation, 'image')
        if mngmnt_command.set_image_field(l, localisation, 'logo_image'):
            mngmnt_command.commit_image_field(
                workspace, l, localisation, 'logo_image')

    workspace.refresh_index()
    categories = workspace.S(Category).filter(language=locale)[:1000]

    for instance in categories:
        instance = instance.to_object()

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

        if mngmnt_command.set_image_field(instance, category, 'image'):
            mngmnt_command.commit_image_field(
                workspace, instance, category, 'image')
        category.save()

    # Manually refresh stuff because the command disables signals
    workspace.refresh_index()

    pages = workspace.S(Page).filter(language=locale)[:1000]

    for instance in pages:
        instance = instance.to_object()

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
            workspace.refresh_index()
            # add the tags
            post.author_tags.add(*instance.author_tags)

            if mngmnt_command.set_image_field(instance, post, 'image'):
                mngmnt_command.commit_image_field(
                    workspace, instance, post, 'image')

        except ValidationError:  # pragma: no cover
            print 'An error occured with: %s(%s)' % (
                instance.title, instance.uuid)

    # Manually refresh stuff because the command disables signals
    workspace.refresh_index()

    # second pass to add related fields
    for instance in pages:
        instance = instance.to_object()

        if instance.linked_pages:
            p = models.Post.objects.get(uuid=instance.uuid)
            p.related_posts.add(*list(
                models.Post.objects.filter(uuid__in=instance.linked_pages)))


@csrf_exempt
@login_required
def import_repo(request, *args, **kwargs):
    if request.is_ajax():
        index_prefix = request.POST.get('index_prefix')
        locales = request.POST.getlist('locales[]')

        repo_path = os.path.join(settings.IMPORT_CLONE_REPO_PATH, index_prefix)
        workspace = EG.workspace(
            repo_path, index_prefix=index_prefix,
            es={'urls': settings.ELASTICSEARCH_HOST})

        for locale in locales:
            import_locale_content(workspace, locale)

        return HttpResponse(
            json.dumps({'success': True}),
            mimetype='application/json')
    return redirect('/github/import/choose/')
