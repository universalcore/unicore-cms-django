from pagedown.widgets import AdminPagedownWidget
from django import forms
from cms.models import Post


class PostForm(forms.ModelForm):
    content = forms.CharField(widget=AdminPagedownWidget())

    class Meta:
        model = Post
