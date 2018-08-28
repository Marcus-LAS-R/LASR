from ..skrypty.sprawdz_dzkat import *
from ..skrypty import baza_wrapper
import pytest


def test_naglowkow():
    a = AnalizujDzKat(False, False)
    kol = set([x.name() for x in a.kolumny])
    assert isinstance(kol, set)

    uzup = a.uzup_temp(' ', ' ', ' ', ' ', ' ',
                          ' ', ' ', ' ', ' ', ' ',
                          0.0000, 0.0000)
    klucze = set(list(uzup._asdict().keys()))
    assert isinstance(klucze, set)

    assert kol == klucze

