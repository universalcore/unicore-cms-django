from urlparse import urlparse

from cms import mappings
from django.conf import settings
from elasticgit import EG

from unicore.content.models import (
    Category, Page, Localisation as EGLocalisation)


def push_to_git(repo_path, index_prefix, es_host):
    workspace = EG.workspace(repo_path,
                             index_prefix=index_prefix,
                             es={'urls': [es_host]})
    if workspace.repo.remotes:
        repo = workspace.repo
        remote = repo.remote()
        remote.fetch()
        remote_master = remote.refs.master
        remote.push(remote_master.remote_head)


def parse_repo_name(repo_url):
    pr = urlparse(repo_url)
    _, _, repo_name_dot_ext = pr.path.rpartition('/')
    if any([
            repo_name_dot_ext.endswith('.git'),
            repo_name_dot_ext.endswith('.json')]):
        repo_name, _, _ = repo_name_dot_ext.partition('.')
        return repo_name
    return repo_name_dot_ext


def setup_workspace(repo_path, index_prefix):
    workspace = EG.workspace(
        repo_path, index_prefix=index_prefix,
        es={'urls': [settings.ELASTICSEARCH_HOST]})

    branch = workspace.sm.repo.active_branch
    if workspace.im.index_exists(branch.name):
        workspace.im.destroy_index(branch.name)

    workspace.setup('ubuntu', 'dev@praekeltfoundation.org')

    while not workspace.index_ready():
        pass

    workspace.setup_custom_mapping(Category, mappings.CategoryMapping)
    workspace.setup_custom_mapping(Page, mappings.PageMapping)
    workspace.setup_custom_mapping(EGLocalisation,
                                   mappings.LocalisationMapping)

    return workspace
