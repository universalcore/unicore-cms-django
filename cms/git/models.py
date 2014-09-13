from gitmodel import fields, models as gitmodels
from cms import utils


class FilterMixin(object):

    @classmethod
    def filter(cls, **fields):
        items = list(cls.all())
        for field, value in fields.items():
            if hasattr(cls, field):
                items = [a for a in items if getattr(a, field) == value]
            else:
                raise Exception('invalid field %s' % field)
        return items


class GitCategoryModel(FilterMixin, gitmodels.GitModel):
    slug = fields.SlugField(required=True)
    title = fields.CharField(required=True)
    subtitle = fields.CharField(required=False)

    def __unicode__(self):
        return self.title

    @property
    def uuid(self):
        return self.id

    def __eq__(self, other):
        if not other:
            return False

        if isinstance(other, dict):
            return self.slug == other['slug']
        return self.slug == other.slug

    def __ne__(self, other):
        if not other:
            return True

        if isinstance(other, dict):
            return self.slug != other['slug']
        return self.slug != other.slug

    def to_dict(self):
        return {
            'uuid': self.uuid,
            'slug': self.slug,
            'title': self.title,
        }


class GitPageModel(FilterMixin, gitmodels.GitModel):
    slug = fields.SlugField(required=True)
    title = fields.CharField(required=True)
    subtitle = fields.CharField(required=False)
    description = fields.CharField(required=False)
    content = fields.CharField(required=False)
    created_at = fields.DateTimeField(required=False)
    modified_at = fields.DateTimeField(required=False)
    published = fields.BooleanField(default=True)
    primary_category = fields.RelatedField(GitCategoryModel, required=False)

    def __unicode__(self):
        return self.title

    @property
    def uuid(self):
        return self.id

    def to_dict(self):
        primary_category = self.primary_category.to_dict()\
            if self.primary_category else None

        return {
            'uuid': self.uuid,
            'slug': self.slug,
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description,
            'content': self.content,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'published': self.published,
            'primary_category': primary_category,
        }

ws = utils.get_git_workspace(utils.init_repository())
GitPage = ws.register_model(GitPageModel)
GitCategory = ws.register_model(GitCategoryModel)
