import pygit2
from django.conf import settings

from gitmodel.workspace import Workspace
from cms.git import repo


def get_git_workspace():
    try:
        ws = Workspace(repo.path, repo.head.name)
    except pygit2.GitError:
        ws = Workspace(repo.path)
    return ws


def sync_repo():
    ws = get_git_workspace()
    ws.sync_repo_index()


def push_to_git():
    if hasattr(settings, 'SSH_PUBKEY_PATH') and hasattr(
            settings, 'SSH_PRIVKEY_PATH'):
        key = pygit2.Keypair(
            'git',
            settings.SSH_PUBKEY_PATH,
            settings.SSH_PRIVKEY_PATH,
            settings.SSH_PASSPHRASE)

        for remote in repo.remotes:
            remote.credentials = key
            remote.push(repo.head.name)


def get_author_from_user(user):
    author = None
    if user:
        author = (
            user.username,
            user.email if user.email else 'author@unicore.io'
        )
    return author
