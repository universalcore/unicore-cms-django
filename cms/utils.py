import pygit2

from gitmodel.workspace import Workspace
from cms.git import repo, init_repository, get_credentials


def get_git_workspace():
    try:
        ws = Workspace(repo.path, repo.head.name)
    except pygit2.GitError:
        ws = Workspace(repo.path)
    return ws


def sync_repo():
    ws = get_git_workspace()
    ws.sync_repo_index()


def push_to_git(repo_path, ssh_pubkey_path, ssh_privkey_path, passphrase=None):
    repo = init_repository(repo_path)
    if ssh_pubkey_path and ssh_privkey_path:
        credentials = get_credentials(
            ssh_pubkey_path, ssh_privkey_path, passphrase)

        for remote in repo.remotes:
            remote.credentials = credentials
            remote.push(repo.head.name)


def get_author_from_user(user):
    author = None
    if user:
        author = (
            user.username,
            user.email if user.email else 'author@unicore.io'
        )
    return author
