import pygit2

from cms.git import repo
from gitmodel.utils import repo_helper
from cms.models import ContentRepository


def workspace_changes(request):
    branch_name = repo.head.shorthand
    remote_name = repo_helper.get_remote_branch(repo, branch_name)
    if remote_name is None:
        return []

    if not branch_name is None:
        local_branch = repo.lookup_branch(branch_name)
    else:
        local_branch = repo.head

    branch = repo.lookup_branch(remote_name, pygit2.GIT_BRANCH_REMOTE)
    return {
        'repo_changes': len(repo.diff(local_branch.name, branch.name)),
        'content_repositories': ContentRepository.objects.all(),
    }
