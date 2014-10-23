import os
import pygit2
from gitmodel.utils import repo_helper
from gitmodel.workspace import Workspace
from django.conf import settings


def get_credentials(ssh_pubkey_path, ssh_privkey_path, ssh_passphrase=None):
    if ssh_pubkey_path and ssh_privkey_path:
        return pygit2.Keypair(
            'git',
            ssh_pubkey_path,
            ssh_privkey_path,
            ssh_passphrase)
    return None


def init_repository(repo_path, repo_url=None, credentials=None):
    if repo_url and not os.path.exists(repo_path):
        pygit2.clone_repository(repo_url, repo_path, credentials=credentials)

    try:
        repo = pygit2.Repository(repo_path)
    except KeyError:
        repo = pygit2.init_repository(repo_path, False)
    repo_helper.checkout_all_upstream(repo)
    return repo

repo = init_repository(
    settings.GIT_REPO_PATH,
    settings.GIT_REPO_URL,
    get_credentials(settings.SSH_PUBKEY_PATH, settings.SSH_PRIVKEY_PATH))


def get_git_workspace():
    try:
        return Workspace(repo.path, repo.head.name)
    except pygit2.GitError:
        return Workspace(repo.path)

workspace = get_git_workspace()
