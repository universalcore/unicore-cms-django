import json
import os.path
import shutil

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from git import Repo
from elasticgit import EG
from elasticgit.storage import StorageManager

from cms import models, utils
from cms.management.commands.import_from_git import Command

from unicore.content.models import (
    Category, Page, Localisation as EGLocalisation)


def clone_repo(url, name, delete_if_exists=True):
    repo_path = os.path.join(settings.IMPORT_CLONE_REPO_PATH, name)
    if delete_if_exists:
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
    elif os.path.exists(repo_path):
        repo = Repo(repo_path)
        StorageManager(repo).pull()
        return repo
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
        repo_name = 'import-repo-prefix-%s' % utils.parse_repo_name(url)
        repo = clone_repo(url, repo_name)
        # NOTE: we can iterate over all instances of a model
        # by using the elastic-git StorageManager directly
        localisations = [
            l.locale for l in
            StorageManager(repo).iterate(EGLocalisation)]
        return HttpResponse(
            json.dumps({'locales': localisations, 'repo_name': repo_name}),
            mimetype='application/json')
    return redirect('/github/import/choose/')


def import_locale_content(repo, locales):
    mngmnt_command = Command()
    sm = StorageManager(repo)

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

    for instance in sm.iterate(Pages):
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
    for instance in sm.iterate(Pages):
        if instance.language not in locales:
            continue
        if instance.linked_pages:
            p = models.Post.objects.get(uuid=instance.uuid)
            p.related_posts.add(*list(
                models.Post.objects.filter(uuid__in=instance.linked_pages)))


@csrf_exempt
@login_required
def import_repo(request, *args, **kwargs):
    if request.is_ajax():
        repo_name = request.POST.get('repo_name')
        locales = request.POST.getlist('locales[]')

        repo_path = os.path.join(settings.IMPORT_CLONE_REPO_PATH, repo_name)
        repo = Repo(repo_path)
        import_locale_content(repo, locales)
        shutil.rmtree(repo_path)

        return HttpResponse(
            json.dumps({'success': True}),
            mimetype='application/json')
    return redirect('/github/import/choose/')


@csrf_exempt
def import_repo_hook(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # TODO: authorize request by checking domain or CAS token

    return HttpResponse()