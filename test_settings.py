from project.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'cms_django.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

DEBUG = True

GIT_REPO_URL = None
GIT_REPO_PATH = abspath('cmsrepo_test')
CELERY_ALWAYS_EAGER = DEBUG

ELASTIC_GIT_INDEX_PREFIX = ''

THUMBOR_SERVER = 'http://localhost:8888'
THUMBOR_SECURITY_KEY = 'MY_SECURE_KEY'
THUMBOR_RW_SERVER = 'http://localhost:8888'
