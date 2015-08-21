import json
import os.path
import shutil

from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from git import Repo
from elasticgit.storage import StorageManager

from cms import utils
from cms.tasks import import_repo as import_repo_task

from unicore.content.models import Localisation as EGLocalisation


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
        repo = utils.clone_repo(url, repo_name)
        # NOTE: we can iterate over all instances of a model
        # by using the elastic-git StorageManager directly
        localisations = [
            l.locale for l in
            StorageManager(repo).iterate(EGLocalisation)]
        return HttpResponse(
            json.dumps({'locales': localisations, 'repo_name': repo_name}),
            mimetype='application/json')
    return redirect('/github/import/choose/')


@csrf_exempt
@login_required
def import_repo(request, *args, **kwargs):
    if request.is_ajax():
        repo_name = request.POST.get('repo_name')
        locales = request.POST.getlist('locales[]')

        repo_path = os.path.join(settings.IMPORT_CLONE_REPO_PATH, repo_name)
        repo = Repo(repo_path)
        utils.import_locale_content(repo, locales)
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
    data = json.loads(request.body)
    repo_url = data['repo_url']
    locales = data['locales']
    override_if_exists = data['override_if_exists']
    import_repo_task.delay(repo_url, locales, override_if_exists)
    return HttpResponse(
            json.dumps({'success': True}),
            mimetype='application/json')
