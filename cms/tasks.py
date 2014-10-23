from celery import task


@task(serializer='json')
def push_to_git(repo_path, ssh_pubkey_path, ssh_privkey_path, passphrase=None):
    from cms import utils
    utils.push_to_git(repo_path, ssh_pubkey_path, ssh_privkey_path, passphrase)
