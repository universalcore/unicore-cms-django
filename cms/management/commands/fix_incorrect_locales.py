from django.core.management.base import BaseCommand
from django.conf import settings

from cms.models import Post, Category, Localisation
from cms import tasks


class Command(BaseCommand):
    help = (
        'Fixes Categories, Pages and Localisation which '
        'have incorrect locale codes i.e (eng_UK, swh_TZ, swh_KE) '
        'correct codes are eng_GB, swa_TZ and swh_KE')

    def handle(self, *args, **options):

        self.stdout.write('Fixing Localisation..')
        for l in Localisation.objects.all():

            if l.language_code == 'swh':
                l.language_code = 'swa'
                l.save()

            if l.country_code == 'UK':
                l.country_code = 'GB'
                l.save()

        for cat in Category.objects.filter(localisation__language_code='swa'):
            cat.save()

        for cat in Category.objects.filter(localisation__country_code='GB'):
            cat.save()

        for post in Post.objects.filter(localisation__language_code='swa'):
            post.save()

        for post in Post.objects.filter(localisation__country_code='GB'):
            post.save()

        tasks.push_to_git.delay(
            settings.GIT_REPO_PATH, settings.ELASTIC_GIT_INDEX_PREFIX)
        self.stdout.write('done.')
