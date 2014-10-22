from elasticgit import EG


def push_to_git(repo_path, index_prefix):
    workspace = EG.workspace(repo_path,
                             index_prefix=index_prefix)
    if workspace.repo.remotes:
        repo = workspace.repo
        remote = repo.remote()
        remote.push()
