from cms.tests.base import BaseCmsTestCase
from django.test.client import RequestFactory

from cms import context_processors


class TestContextProcessors(BaseCmsTestCase):

    def test_workspace_changes(self):
        local_workspace = self.mk_workspace()
        remote_workspace = self.mk_workspace(
            name='%s_remote' % (self.id().lower(),))

        # the local grows some categories
        self.create_categories(remote_workspace)

        local_repo = local_workspace.repo
        origin = local_repo.create_remote(
            'origin', remote_workspace.working_dir)
        [fetch_info] = origin.fetch()
        local_repo.git.merge(fetch_info.commit)

        # Make 2 local changes
        self.create_pages(local_workspace)

        request = RequestFactory().get('/')
        with self.active_workspace(local_workspace):
            context = context_processors.workspace_changes(request)
            self.assertEqual(context, {
                'repo_changes': 2,
            })

    def test_content_repositories(self):
        request = RequestFactory().get('/')
        context = context_processors.content_repositories(request)
        self.assertEqual(list(context['content_repositories']), [])
