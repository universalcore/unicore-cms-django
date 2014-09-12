import pygit2
from django.conf import settings
from gitmodel.utils import repo_helper
from gitmodel.workspace import Workspace


def init_repository():
    try:
        repo = pygit2.Repository(settings.GIT_REPO_PATH)
    except:
        #repo = pygit2.clone_repository(settings.GIT_REPO_URL, repo_path)
        repo = pygit2.init_repository(settings.GIT_REPO_PATH, False)
    repo_helper.checkout_all_upstream(repo)
    return repo


def sync_repo():
    repo = init_repository()
    try:
        ws = Workspace(repo.path, repo.head.name)
    except:
        ws = Workspace(repo.path)
    ws.sync_repo_index()
