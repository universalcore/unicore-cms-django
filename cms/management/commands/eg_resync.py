from django.conf import settings
from django.core.management.base import BaseCommand

from elasticgit import EG
from elasticgit.utils import fqcn

from unicore.content.models import Page, Category, Localisation
from cms import mappings


class Command(BaseCommand):

    help = 'Resync an Elasticgit repository with its search index.'

    def setup_workspace(self):
        workspace = EG.workspace(
            settings.GIT_REPO_PATH,
            index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
            es={'urls': [settings.ELASTICSEARCH_HOST]})

        branch = workspace.sm.repo.active_branch
        if workspace.im.index_exists(branch.name):
            workspace.im.destroy_index(branch.name)

        workspace.setup('ubuntu', 'dev@praekeltfoundation.org')

        while not workspace.index_ready():
            pass

        workspace.setup_custom_mapping(Category, mappings.CategoryMapping)
        workspace.setup_custom_mapping(Page, mappings.PageMapping)
        workspace.setup_custom_mapping(Localisation,
                                       mappings.LocalisationMapping)

        return workspace

    def handle(self, *args, **kwargs):
        self.workspace = self.setup_workspace()

        for model_class in [Page, Category, Localisation]:
            self.sync_model(model_class)

    def sync_model(self, model_class):
        updated, removed = self.workspace.sync(model_class)
        self.stdout.write(
            '%s: %s updated, %s removed.\n' % (
                fqcn(model_class), len(updated), len(removed)))
