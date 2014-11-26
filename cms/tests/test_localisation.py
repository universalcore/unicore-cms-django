from cms.models import Localisation
from cms.tests.base import BaseCmsTestCase

from unicore.content import models as eg_models


class LocalisationTestCase(BaseCmsTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.workspace.setup_custom_mapping(eg_models.Localisation, {
            'properties': {
                'locale': {
                    'type': 'string',
                    'index': 'not_analyzed',
                }
            }
        })

    def test_create_localisation(self):
        l = Localisation._for('spa_ES')
        l.save()
        self.assertEquals(l.language_code, 'spa')
        self.assertEquals(l.country_code, 'ES')
        self.assertEquals(Localisation.objects.all().count(), 1)
        self.assertEquals(self.workspace.S(eg_models.Localisation).count(), 1)

        [eg_local] = self.workspace.S(eg_models.Localisation).everything()
        self.assertEquals(eg_local.locale, 'spa_ES')

        l.delete()
        self.assertEquals(self.workspace.S(eg_models.Localisation).count(), 0)
