# -*- coding: utf-8 -*-
"""Spis skryptów wtyczki zbierany na żywo z menu LAS-R i pasków LAS-R /
LAS-R KP - wspólny dla wyszukiwarki (wyszukiwarka.py) i Ulubionych
(ulubione.py). Nazwa, ścieżka i tooltip zawsze aktualne; dawne nazwy i
słowa kluczowe z indeks_skryptow.INDEKS.

Identyfikator akcji = nazwa atrybutu wtyczki (self.kas_op -> 'kas_op'),
ustawiany jako objectName akcji (ponowne użycie bez szukania)."""
from PyQt5.QtWidgets import QAction, QMenu

from .indeks_skryptow import POMIJANE, Wpis

SEP = ' › '
TESTOWE = 'Testowe'


class Skrypt(Wpis):
    """Wpis wyszukiwarki + akcja do uruchomienia."""

    def __init__(self, id_, akcja, sciezka):
        nazwa = akcja.text().replace('&', '')
        super().__init__(id_, nazwa, sciezka, akcja.toolTip()
                         if akcja.toolTip() != akcja.text() else '',
                         testowe=sciezka.startswith(TESTOWE))
        self.akcja = akcja

    def dostepny(self):
        return self.akcja.isEnabled()


def nadaj_identyfikatory(plugin):
    """objectName każdej akcji wtyczki = nazwa atrybutu (pierwsza, gdy
    akcja ma kilka). Akcje QGIS-a (iface.action*) pomijane. Zwraca zbiór
    nadanych identyfikatorów."""
    ids = set()
    for nazwa, obiekt in sorted(vars(plugin).items()):
        if isinstance(obiekt, QAction) and \
                obiekt.parent() is plugin.iface.mainWindow() and \
                obiekt.objectName() in ('', nazwa):
            obiekt.setObjectName(nazwa)
            ids.add(nazwa)
    return ids


def zbierz(plugin, ids, pomin_menu=()):
    """Lista Skrypt (bez powtórzeń - akcja z menu i paska raz, ze ścieżką
    z menu); ids - identyfikatory z nadaj_identyfikatory (bez akcji
    QGIS-a z pasków). pomin_menu - podmenu pomijane (Ulubione)."""
    wyn, byly = [], set()

    def dodaj(akcja, sciezka):
        id_ = akcja.objectName()
        if id_ not in ids or id_ in byly or id_ in POMIJANE or \
                not akcja.isVisible() or not akcja.isEnabled():
            return
        byly.add(id_)
        wyn.append(Skrypt(id_, akcja, sciezka))

    def przejdz(menu, sciezka):
        for a in menu.actions():
            if a.isSeparator():
                continue
            pod = a.menu()
            if isinstance(pod, QMenu):
                if pod not in pomin_menu:
                    przejdz(pod, sciezka + [pod.title()])
                continue
            dodaj(a, SEP.join(sciezka + [a.text().replace('&', '')]))

    przejdz(plugin.menu, [])
    for pasek, opis in ((plugin.toolbar, 'Pasek LAS-R'),
                        (plugin.toolbar_skr, 'Pasek LAS-R KP')):
        for a in pasek.actions():
            if not a.isSeparator():
                dodaj(a, f'{opis}{SEP}{a.text()}')
    return wyn
