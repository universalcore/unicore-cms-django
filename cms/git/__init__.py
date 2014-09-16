import pygit2
from gitmodel.utils import repo_helper
from django.conf import settings


def init_repository():
    try:
        repo = pygit2.Repository(settings.GIT_REPO_PATH)
    except KeyError:
        repo = pygit2.init_repository(settings.GIT_REPO_PATH, False)
    repo_helper.checkout_all_upstream(repo)
    return repo

repo = init_repository()
