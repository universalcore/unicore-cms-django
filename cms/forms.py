from pagedown.widgets import AdminPagedownWidget
from django import forms
from cms.models import Post, Category

from taggit_live.forms import LiveTagField


class PostForm(forms.ModelForm):
    content = forms.CharField(widget=AdminPagedownWidget())
    tags = LiveTagField()

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['localisation'].required = True

    class Meta:
        model = Post


class CategoryForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.fields['localisation'].required = True

    class Meta:
        model = Category
