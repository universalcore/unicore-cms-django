from celery import task


@task(serializer='json')
def push_to_git():
    from cms import utils
    utils.push_to_git()
