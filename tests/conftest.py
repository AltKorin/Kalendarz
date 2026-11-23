import pytest

from przyjecia.models import Czlonek, Lokal


@pytest.fixture
def lokal(db):
    return Lokal.objects.create(nazwa="Restauracja Testowa")


def czlonek(user, lokal, kierownik=False):
    Czlonek.objects.create(user=user, lokal=lokal, kierownik=kierownik)
    return user
