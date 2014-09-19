import os
import pygit2
from gitmodel.utils import repo_helper
from django.conf import settings


def init_repository():
    if settings.GIT_REPO_URL and not os.path.exists(settings.GIT_REPO_PATH):
        pygit2.clone_repository(settings.GIT_REPO_URL, settings.GIT_REPO_PATH)

    try:
        repo = pygit2.Repository(settings.GIT_REPO_PATH)
    except KeyError:
        repo = pygit2.init_repository(settings.GIT_REPO_PATH, False)
    repo_helper.checkout_all_upstream(repo)
    return repo

repo = init_repository()
