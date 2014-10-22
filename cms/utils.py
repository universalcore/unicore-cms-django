from elasticgit import EG


def push_to_git(repo_path, index_prefix):
    workspace = EG.workspace(repo_path,
                             index_prefix=index_prefix)
    if workspace.repo.remotes:
        repo = workspace.repo
        remote = repo.remote()
        remote.push()


def get_author_from_user(user):
    author = None
    if user:
        author = (
            user.username,
            user.email if user.email else 'author@unicore.io'
        )
    return author
