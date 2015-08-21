from celery import task
from cms import utils


@task(serializer='json')
def push_to_git(repo_path, index_prefix, es_host):
    utils.push_to_git(repo_path, index_prefix, es_host)


@task(serializer='json')
def import_repo(repo_url, locales, override_if_exists=False):
    repo_name = 'import-repo-prefix-%s' % utils.parse_repo_name(repo_url)
    repo = utils.clone_url(repo_name)
    utils.import_locale_content(
        repo, locales, override_if_exists=override_if_exists)
