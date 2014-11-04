from django.conf import settings
from django.core.management.base import BaseCommand

from elasticgit import EG
from elasticgit.utils import fqcn

from unicore.content.models import Page, Category


class Command(BaseCommand):

    help = 'Resync an Elasticgit repository with its search index.'

    def handle(self, *args, **kwargs):
        self.workspace = EG.workspace(
            settings.GIT_REPO_PATH,
            index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX)

        for model_class in [Page, Category]:
            self.sync_model(model_class)

    def sync_model(self, model_class):
        updated, removed = self.workspace.sync(model_class)
        self.stdout.write(
            '%s: %s updated, %s removed.\n' % (
                fqcn(model_class), len(updated), len(removed)))
