from cms.tests.base import BaseCmsTestCase

from cms.forms import PostForm, CategoryForm


class FormTest(BaseCmsTestCase):

    def test_required_localisations(self):
        post_form = PostForm()
        self.assertTrue(post_form.fields['localisation'].required)
        category_form = CategoryForm()
        self.assertTrue(category_form.fields['localisation'].required)
