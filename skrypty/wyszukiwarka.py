# -*- coding: utf-8 -*-
"""Wyszukiwarka skryptów Las-R w pasku wyszukiwania QGIS-a (lewy dolny
róg, Ctrl+K). Prefiks 'lr' - tylko skrypty Las-R (samo 'lr ' - wszystkie);
bez prefiksu wyniki Las-R obok wyników QGIS-a. Enter uruchamia skrypt.
Menu "Znajdź skrypt..." i lupa na pasku LAS-R wołają otworz()."""
from qgis.core import QgsLocatorFilter, QgsLocatorResult

from . import indeks_skryptow as ix

PREFIKS = 'lr'
LIMIT = 30


class FiltrSkryptow(QgsLocatorFilter):
    """Spis skryptów (dostarczany funkcją - zbierany po zbudowaniu menu)
    przeszukiwany w wątku głównym (FastFlag) - szukanie w pamięci jest
    szybkie, a akcje Qt wolno ruszać tylko w wątku głównym."""

    def __init__(self, daj_spis, parent=None):
        super().__init__(parent)
        self.daj_spis = daj_spis

    def clone(self):
        return FiltrSkryptow(self.daj_spis)

    def name(self):
        return 'lasr_skrypty'

    def displayName(self):
        return 'Las-R - skrypty'

    def description(self):
        return 'Skrypty wtyczki Las-R (nazwa, dawna nazwa, słowa kluczowe)'

    def prefix(self):
        return PREFIKS

    def flags(self):
        return QgsLocatorFilter.FastFlag

    def priority(self):
        return QgsLocatorFilter.High

    def fetchResults(self, tekst, kontekst, feedback):
        tekst = (tekst or '').strip()
        # bez prefiksu - dopiero od 2 znaków (pojedyncza litera zalewałaby
        # listę QGIS-a); z prefiksem 'lr ' - także cała lista
        # activePrefix() zwraca prefix() także bez wpisanego prefiksu -
        # o prefiksie mówi kontekst
        if len(tekst) < 2 and not getattr(kontekst, 'usingPrefix', False):
            return
        for w, dawna in ix.szukaj(self.daj_spis(), tekst, limit=LIMIT):
            if feedback is not None and feedback.isCanceled():
                return
            wynik = QgsLocatorResult(self, w.nazwa, w.id)
            opis = w.sciezka.rsplit(' › ', 1)[0] if ' › ' in w.sciezka \
                else w.sciezka
            if dawna:
                opis = f'dawniej: {dawna} | {opis}'
            if w.tip:
                opis += ' | ' + (w.tip if len(w.tip) <= 90
                                 else w.tip[:87] + '...')
            wynik.description = opis
            self.resultFetched.emit(wynik)

    def triggerResult(self, wynik):
        # userData: atrybut (starsze QGIS) albo metoda (nowsze)
        id_ = wynik.userData
        if callable(id_):
            id_ = id_()
        w = next((x for x in self.daj_spis() if x.id == id_), None)
        if w is not None and w.dostepny():
            w.akcja.trigger()


def otworz(iface):
    """Pasek wyszukiwania QGIS-a z wpisanym 'lr ' - lista skryptów Las-R."""
    iface.locatorSearch(PREFIKS + ' ')
