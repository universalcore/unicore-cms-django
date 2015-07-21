import json
import os.path
import shutil

from urlparse import urlparse

from django.http import HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required

from git import Repo
from elasticgit import EG

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

    return workspace


def clone_repo(url, name):
    repo_path = os.path.join(settings.IMPORT_CLONE_REPO_PATH, name)
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    return Repo.clone_from(url, repo_path)

@login_required
def import_clone_repo(request, *args, **kwargs):
    if request.is_ajax():
        url = request.GET.get('repo_url')
        if not url:
            return HttpResponse(
                'Invalid repo_url',
                status=400,
                mimetype='application/json')
        repo_index = 'import-prefix-%s' % parse_repo_name(url)
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
