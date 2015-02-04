import pytest

from django.test import RequestFactory
from cms.backends import UnicoreCASBackend


@pytest.mark.django_db
def test_user_has_permissions(monkeypatch, django_user_model):
    factory = RequestFactory()
    request = factory.get('/')
    request.session = {}

    def mock_verify(ticket, service):
        return 'testuser', {
            'ticket': ticket,
            'service': service,
            'has_perm': 'True'}

    monkeypatch.setattr('django_cas_ng.backends._verify', mock_verify)

    backend = UnicoreCASBackend()
    user = backend.authenticate(
        ticket='fake-ticket', service='fake-service', request=request)

    assert user is not None
    assert user.username == 'testuser'
    assert user.is_staff
    assert user.is_superuser
    assert django_user_model.objects.filter(username='testuser').exists()


@pytest.mark.django_db
def test_user_no_permissions(monkeypatch, django_user_model):
    factory = RequestFactory()
    request = factory.get('/')
    request.session = {}

    def mock_verify(ticket, service):
        return 'testuser', {
            'ticket': ticket,
            'service': service,
            'has_perm': 'False'}

    monkeypatch.setattr('django_cas_ng.backends._verify', mock_verify)

    backend = UnicoreCASBackend()
    user = backend.authenticate(
        ticket='fake-ticket', service='fake-service', request=request)

    assert user is None
