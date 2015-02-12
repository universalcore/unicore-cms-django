from django.conf import settings
from django.core.management.base import BaseCommand

from elasticgit import EG
from elasticgit.utils import fqcn

from elasticsearch.exceptions import NotFoundError

from cms import models as django_models
from unicore.content import models as eg_models


class Command(BaseCommand):

    help = 'Resync an Elasticgit repository with a Django db.'

    def handle(self, *args, **kwargs):
        self.workspace = EG.workspace(
            settings.GIT_REPO_PATH,
            index_prefix=settings.ELASTIC_GIT_INDEX_PREFIX,
            es={'urls': [settings.ELASTICSEARCH_HOST]})
        self.index_manager = self.workspace.im
        self.storage_manager = self.workspace.sm

        model_pairs = [
            (django_models.Post, eg_models.Page),
            (django_models.Category, eg_models.Category)
        ]
        for django_model_class, eg_model_class in model_pairs:
            self.sync_model(django_model_class, eg_model_class)

        self.sync_localisation_model(
            django_models.Localisation, eg_models.Localisation)

    def sync_model(self, django_model_class, eg_model_class):
        uuids = set([])
        for model in django_model_class.objects.all():
            uuids.add(model.uuid)
            model.save()

        for git_model in self.storage_manager.iterate(eg_model_class):
            if git_model.uuid not in uuids:
                self.storage_manager.delete(
                    git_model, 'This has been deleted in the CMS')
                try:
                    self.index_manager.unindex(git_model)
                except NotFoundError:
                    pass
                self.stdout.write(
                    'Deleted %s: %s.\n' % (
                        fqcn(eg_model_class), git_model.uuid,))
            else:
                self.stdout.write(
                    'Kept %s: %s.\n' % (fqcn(eg_model_class), git_model.uuid))

    def sync_localisation_model(self, django_model_class, eg_model_class):
        locales = set([])
        for model in django_model_class.objects.all():
            locales.add(model.get_code())
            model.save()

        for git_model in self.storage_manager.iterate(eg_model_class):
            if git_model.locale not in locales:
                self.storage_manager.delete(
                    git_model, 'This has been deleted in the CMS')
                try:
                    self.index_manager.unindex(git_model)
                except NotFoundError:
                    pass
                self.stdout.write(
                    'Deleted %s: %s.\n' % (
                        fqcn(eg_model_class), git_model.locale,))
            else:
                self.stdout.write(
                    'Kept %s: %s.\n' %
                    (fqcn(eg_model_class), git_model.locale))
