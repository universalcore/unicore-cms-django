from cms.tasks import push_to_git
from cms.tests.base import BaseCmsTestCase
from django.conf import settings

from unicore.content.models import Page


class TaskTest(BaseCmsTestCase):

    def setUp(self):
        self.local_workspace = self.mk_workspace()
        self.remote_workspace = self.mk_workspace(
            name='%s_remote' % (self.id().lower(),),
            index_prefix='%s_remote' % (self.local_workspace.index_prefix,))

        for data, count in self.create_page_data_iter():
            data['title'] = 'remote page %i' % (count,)
            self.remote_workspace.save(
                Page(data), 'Saving %(title)s.' % data)
        self.remote_workspace.refresh_index()

    def test_push_to_git(self):
        # NOTE: In order to push to the remote workspace's master branch it
        #       needs to itself be checked out with a different branch,
        #       one cannot pushed to branches that are currently checked out.
        remote_repo = self.remote_workspace.repo
        remote_repo.git.checkout('HEAD', b='temp')

        with self.active_workspace(self.local_workspace):
            origin = self.local_workspace.repo.create_remote(
                'origin', self.remote_workspace.working_dir)
            branch = self.local_workspace.repo.active_branch
            origin.fetch()
            remote_master = origin.refs.master
            branch.set_tracking_branch(remote_master)

            self.local_workspace.fast_forward()
            self.local_workspace.reindex(Page)

            self.assertEqual(self.local_workspace.S(Page).count(), 2)
            self.create_pages(self.local_workspace)
            self.assertEqual(self.local_workspace.S(Page).count(), 4)

            push_to_git(settings.GIT_REPO_PATH,
                        settings.ELASTIC_GIT_INDEX_PREFIX)

        # NOTE: switching back to master on the remote because the changes
        #       should have been pushed and we are checking for their
        #       existence

        remote_repo.heads.master.checkout()

        self.assertEqual(self.remote_workspace.S(Page).count(), 2)
        self.remote_workspace.reindex(Page)
        self.assertEqual(self.remote_workspace.S(Page).count(), 4)
