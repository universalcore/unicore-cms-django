import re
import pygit2
from django.conf import settings
from django.template.defaultfilters import slugify

from gitmodel.utils import repo_helper
from gitmodel.workspace import Workspace

RE_NUMERICAL_SUFFIX = re.compile(r'^[\w-]*-(\d+)+$')


def generate_slug(obj, tail_number=0):
    from cms.models import Post
    """
    Returns a new unique slug. Object must provide a SlugField called slug.
    URL friendly slugs are generated using django.template.defaultfilters'
    slugify. Numbers are added to the end of slugs for uniqueness.
    """
    # use django slugify filter to slugify
    slug = slugify(obj.title)

    # Empty slugs are ugly (eg. '-1' may be generated) so force non-empty
    if not slug:
        slug = 'no-title'

    values_list = Post.objects.filter(
        slug__startswith=slug
    ).values_list('id', 'slug')

    # Find highest suffix
    max = -1
    for tu in values_list:
        if tu[1] == slug:
            if tu[0] == obj.id:
                # If we encounter obj and the stored slug is the same as
                # the desired slug then return.
                return slug

            if max == -1:
                # Set max to indicate a collision
                max = 0

        # Update max if suffix is greater
        match = RE_NUMERICAL_SUFFIX.match(tu[1])
        if match is not None:

            # If the collision is on obj then use the existing slug
            if tu[0] == obj.id:
                return tu[1]

            i = int(match.group(1))
            if i > max:
                max = i

    if max >= 0:
        # There were collisions
        return "%s-%s" % (slug, max + 1)
    else:
        # No collisions
        return slug


def init_repository():
    try:
        repo = pygit2.Repository(settings.GIT_REPO_PATH)
    except KeyError:
        repo = pygit2.init_repository(settings.GIT_REPO_PATH, False)
    repo_helper.checkout_all_upstream(repo)
    return repo


def get_git_workspace(repo):
    try:
        ws = Workspace(repo.path, repo.head.name)
    except pygit2.GitError:
        ws = Workspace(repo.path)
    return ws


def sync_repo():
    ws = get_git_workspace(init_repository())
    ws.sync_repo_index()
