from django.conf import settings
from elasticgit import EG

from cms.models import ContentRepository


def workspace_changes(request):
    workspace = EG.workspace(settings.GIT_REPO_PATH)
    repo = workspace.repo
    index = repo.index
    origin = repo.remote()
    remote_master = origin.refs.master
    return {
        'repo_changes': len(index.diff(remote_master.commit)),
        'content_repositories': ContentRepository.objects.all(),
    }
