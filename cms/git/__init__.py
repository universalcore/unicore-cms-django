import os
import pygit2
from gitmodel.utils import repo_helper
from django.conf import settings


def get_credentials():
    if hasattr(settings, 'SSH_PUBKEY_PATH') and hasattr(
            settings, 'SSH_PRIVKEY_PATH'):
        return pygit2.Keypair(
            'git',
            settings.SSH_PUBKEY_PATH,
            settings.SSH_PRIVKEY_PATH,
            settings.SSH_PASSPHRASE)
    return None


def init_repository(repo_path, repo_url=None):
    if repo_url and not os.path.exists(repo_path):
        credentials = get_credentials()
        pygit2.clone_repository(repo_url, repo_path, credentials=credentials)

    try:
        repo = pygit2.Repository(repo_path)
    except KeyError:
        repo = pygit2.init_repository(repo_path, False)
    repo_helper.checkout_all_upstream(repo)
    return repo

repo = init_repository(settings.GIT_REPO_PATH, settings.GIT_REPO_URL)
