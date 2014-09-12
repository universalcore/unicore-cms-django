from gitmodel.workspace import Workspace
from gitmodel import fields, models as gitmodels


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


class GitCategory(FilterMixin, gitmodels.GitModel):
    slug = fields.SlugField(required=True)
    title = fields.CharField(required=True)
    subtitle = fields.CharField(required=False)

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

    @classmethod
    def model(cls, repo):
        try:
            ws = Workspace(repo.path, repo.head.name)
        except:
            ws = Workspace(repo.path)
        return ws.register_model(cls)


class GitPage(FilterMixin, gitmodels.GitModel):
    slug = fields.SlugField(required=True)
    title = fields.CharField(required=True)
    subtitle = fields.CharField(required=False)
    description = fields.CharField(required=False)
    content = fields.CharField(required=False)
    created_at = fields.DateTimeField(required=False)
    modified_at = fields.DateTimeField(required=False)
    published = fields.BooleanField(default=True)
    primary_category = fields.RelatedField(GitCategory, required=False)

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

    @classmethod
    def model(cls, repo):
        try:
            ws = Workspace(repo.path, repo.head.name)
        except:
            ws = Workspace(repo.path)
        return ws.register_model(cls)
