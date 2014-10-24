from celery import task
from cms import utils


@task(serializer='json')
def push_to_git(repo_path, index_prefix):
    utils.push_to_git(repo_path, index_prefix)
