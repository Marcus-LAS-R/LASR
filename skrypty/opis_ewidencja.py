# -*- coding: utf-8 -*-
"""Edytor opisu, zakładka Ewidencja - tylko odczyt i nawigacja: działki,
jednostki rejestrowe i właściciele wydzielenia, wyszukiwarka właściciela
i działki z dynamiczną listą podpowiedzi. Dane: opis_ewidencja_dane.py."""
from PyQt5 import sip
from PyQt5.QtCore import QStringListModel, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCompleter, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import opis_adres as oa
from . import opis_ewidencja_dane as dane

KOLUMNY_DZIALEK = (('obreb', 'Obręb'), ('dzialka', 'Działka'),
                   ('jr', 'Jedn. rej.'), ('uzytek', 'Klasoużytek'),
                   ('pow_uzytku', 'Pow. użytku [ha]'),
                   ('rozliczona', 'Rozliczona [ha]'))
KOLUMNY_WLASCICIELI = (('jr', 'Jedn. rej.'), ('wlasciciel', 'Właściciel'),
                       ('udzial', 'Udział'), ('rodzaj', 'Rodzaj'),
                       ('miejsc', 'Miejscowość'))
_KOLOR_UWAGI = '#b36b00'


def _ha(v):
    return '' if v is None else f'{float(v):.4f}'.replace('.', ',')


def _adres_czytelny(adr):
    cz = oa.skladowe(adr)
    if not cz:
        return adr
    return f"{cz['obreb']}  {cz['grp']}  {cz['oddz']}-{cz['wydz']}"


def _tabela(kolumny):
    t = QTableWidget(0, len(kolumny))
    t.setHorizontalHeaderLabels([k[1] for k in kolumny])
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(22)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def _wypelnij(tabela, kolumny, wiersze):
    tabela.setRowCount(len(wiersze))
    for r, w in enumerate(wiersze):
        for c, (pole, _n) in enumerate(kolumny):
            liczba = pole in ('pow_uzytku', 'rozliczona')
            it = QTableWidgetItem(_ha(w[pole]) if liczba else w[pole])
            if liczba:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabela.setItem(r, c, it)


class Szukajka(QLineEdit):
    """Pole z dynamiczną listą: każde słowo gdziekolwiek w podpowiedzi, bez
    rozróżniania wielkości liter i polskich znaków."""

    def __init__(self, na_wybor, parent=None):
        super().__init__(parent)
        self.pozycje = []
        self.widoczne = []
        self.na_wybor = na_wybor
        self.model_listy = QStringListModel(self)
        k = QCompleter(self.model_listy, self)
        k.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        k.setCaseSensitivity(Qt.CaseInsensitive)
        k.setMaxVisibleItems(15)
        lista = QListView()
        lista.setUniformItemSizes(True)
        k.setPopup(lista)
        k.activated[str].connect(self.wybrano)
        self.setCompleter(k)
        self.setClearButtonEnabled(True)
        self.textEdited.connect(self._edycja)
        self.returnPressed.connect(self._enter)

    def ustaw_pozycje(self, pozycje):
        self.pozycje = pozycje
        self.widoczne = []
        self.model_listy.setStringList([])

    def _edycja(self, tekst):
        self.widoczne = dane.filtruj(self.pozycje, tekst)
        self.model_listy.setStringList([p.etykieta for p in self.widoczne])
        if self.widoczne:
            self.completer().complete()
        else:
            self.completer().popup().hide()

    def _enter(self):
        """Enter bez wyboru z listy: dokładna pozycja albo jedyne trafienie."""
        p = dane.dokladna(self.widoczne, self.text())
        if p is None and len(self.widoczne) == 1:
            p = self.widoczne[0]
        if p is not None:
            self.wybrano(p.etykieta)

    def wybrano(self, etykieta):
        p = next((x for x in self.widoczne if x.etykieta == etykieta), None)
        if p is not None:
            self.setText(etykieta)
            self.completer().popup().hide()
            self.na_wybor(p)


class WidokEwidencji(QWidget):
    """Treść zakładki. Niczego nie zapisuje w bazie."""

    def __init__(self, karta):
        super().__init__(karta)
        self.karta = karta
        self.ew = None
        self._wyniki = []   # adresy z ostatniego wyszukiwania

        uklad = QVBoxLayout(self)
        uklad.setContentsMargins(4, 6, 4, 4)

        siatka = QGridLayout()
        siatka.addWidget(QLabel('Szukaj właściciela:'), 0, 0)
        self.szukaj_wl = Szukajka(self._wybrano)
        siatka.addWidget(self.szukaj_wl, 0, 1)
        siatka.addWidget(QLabel('Szukaj działki:'), 0, 2)
        self.szukaj_dz = Szukajka(self._wybrano)
        self.szukaj_dz.setPlaceholderText('obręb lub numer działki')
        siatka.addWidget(self.szukaj_dz, 0, 3)
        siatka.setColumnStretch(1, 3)
        siatka.setColumnStretch(3, 2)
        uklad.addLayout(siatka)

        self.lbl_uwaga = QLabel()
        self.lbl_uwaga.setWordWrap(True)
        self.lbl_uwaga.setStyleSheet(f'color: {_KOLOR_UWAGI};')
        self.lbl_uwaga.hide()
        uklad.addWidget(self.lbl_uwaga)

        # wyniki, gdy działka/właściciel jest w kilku wydzieleniach
        self.wyniki = QWidget()
        lay = QVBoxLayout(self.wyniki)
        lay.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout()
        self.lbl_wyniki = QLabel()
        h.addWidget(self.lbl_wyniki)
        h.addStretch(1)
        b = QPushButton('Wyczyść')
        b.setToolTip('Chowa listę wyników i czyści pola wyszukiwania')
        b.clicked.connect(self.wyczysc_wyszukiwanie)
        h.addWidget(b)
        lay.addLayout(h)
        self.lista_wynikow = QListWidget()
        self.lista_wynikow.setFlow(QListWidget.LeftToRight)
        self.lista_wynikow.setWrapping(True)
        self.lista_wynikow.setResizeMode(QListWidget.Adjust)
        self.lista_wynikow.setSpacing(2)
        self.lista_wynikow.setMaximumHeight(72)
        self.lista_wynikow.itemClicked.connect(self._klik_wyniku)
        self.lista_wynikow.itemActivated.connect(self._klik_wyniku)
        lay.addWidget(self.lista_wynikow)
        self.wyniki.hide()
        uklad.addWidget(self.wyniki)

        self.lbl_dzialki = QLabel()
        uklad.addWidget(self.lbl_dzialki)
        self.t_dzialki = _tabela(KOLUMNY_DZIALEK)
        uklad.addWidget(self.t_dzialki, 3)
        self.lbl_wlasciciele = QLabel()
        uklad.addWidget(self.lbl_wlasciciele)
        self.t_wlasciciele = _tabela(KOLUMNY_WLASCICIELI)
        uklad.addWidget(self.t_wlasciciele, 2)

    # --------------------------------------------------------------- dane

    def aktywuj(self, aint):
        """Wejście na zakładkę: świeży odczyt bazy (po zmianach na karcie)."""
        self._uwaga('')
        try:
            self.ew = dane.wczytaj(self.karta.baza.cur)
        except Exception as e:
            self.ew = None
            self.szukaj_wl.ustaw_pozycje([])
            self.szukaj_dz.ustaw_pozycje([])
            self._uwaga(f'Nie udało się odczytać ewidencji z bazy: {e}')
            self.pokaz(None)
            return
        self.szukaj_dz.ustaw_pozycje(self.ew.podpowiedzi_dzialek())
        if self.ew.anonimowa:
            self.szukaj_wl.ustaw_pozycje([])
            self.szukaj_wl.setEnabled(False)
            self.szukaj_wl.setPlaceholderText(
                'baza zanonimizowana (BDO) - brak nazwisk')
        else:
            self.szukaj_wl.ustaw_pozycje(self.ew.podpowiedzi_wlascicieli())
            self.szukaj_wl.setEnabled(True)
            self.szukaj_wl.setPlaceholderText('nazwisko, imię lub miejscowość')
        if not self.ew.rozliczona:
            self._uwaga('Baza nie jest rozliczona: działki i właściciele nie '
                        'prowadzą do wydzieleń. Uruchom Rozlicz powierzchnię.')
        self.pokaz(aint)
        self._zaznacz_wynik()

    def pokaz(self, aint):
        """Tabele dla wydzielenia (None - puste)."""
        dzialki, wlasciciele = [], []
        if self.ew is not None and aint is not None:
            dzialki = self.ew.dzialki_wydzielenia(aint)
            wlasciciele = self.ew.wlasciciele_wydzielenia(aint)
        _wypelnij(self.t_dzialki, KOLUMNY_DZIALEK, dzialki)
        _wypelnij(self.t_wlasciciele, KOLUMNY_WLASCICIELI, wlasciciele)
        suma = sum(float(w['rozliczona'] or 0) for w in dzialki)
        self.lbl_dzialki.setText(
            f'<b>Działki wydzielenia</b> ({len(dzialki)}, rozliczono '
            f'{_ha(suma)} ha)' if dzialki else '<b>Działki wydzielenia</b>')
        self.lbl_wlasciciele.setText(
            f'<b>Właściciele</b> ({len(wlasciciele)})' if wlasciciele
            else '<b>Właściciele</b>')
        self._zaznacz_wynik()

    def _uwaga(self, tekst):
        self.lbl_uwaga.setText(tekst)
        self.lbl_uwaga.setVisible(bool(tekst))

    # ------------------------------------------------------- wyszukiwanie

    def _adresy(self, pozycja):
        """Adresy wydzieleń pozycji, naturalnie posortowane."""
        odwrotny = {a: adr for adr, a in self.karta.wydz.items()}
        adresy = [odwrotny[a] for a in self.ew.wydzielenia_pozycji(pozycja)
                  if a in odwrotny]
        return sorted(adresy, key=dane.klucz_naturalny)

    def _wybrano(self, pozycja):
        self._uwaga('')
        adresy = self._adresy(pozycja)
        if not adresy:
            self._pokaz_wyniki([])
            self._uwaga(f'{pozycja.tekst}: brak w rozliczeniu - nie prowadzi '
                        'do żadnego wydzielenia.')
            return
        if len(adresy) == 1:
            self._pokaz_wyniki([])
            if self._wczytaj(adresy[0]):
                self.karta.przejdz_do_opisu()
            return
        self._pokaz_wyniki(adresy, pozycja.tekst)
        self._wczytaj(adresy[0])

    def _wczytaj(self, adr):
        """True, gdy karta pokazuje to wydzielenie (przy niezapisanych
        zmianach użytkownik mógł zostać przy poprzednim)."""
        self.karta.panel.pokaz_wydzielenie(adr)
        if sip.isdeleted(self):
            return False
        wczytano = (self.karta.adr or '').strip() == adr.strip()
        if not wczytano:
            self._uwaga('Zostało poprzednie wydzielenie (niezapisane zmiany).')
        self._zaznacz_wynik()
        return wczytano

    def _pokaz_wyniki(self, adresy, tytul=''):
        self._wyniki = adresy
        self.lista_wynikow.clear()
        for adr in adresy:
            it = QListWidgetItem(_adres_czytelny(adr))
            it.setData(Qt.UserRole, adr)
            it.setToolTip(adr)
            self.lista_wynikow.addItem(it)
        self.lbl_wyniki.setText(
            f'<b>{tytul}</b>: {len(adresy)} wydzieleń' if adresy else '')
        self.wyniki.setVisible(bool(adresy))

    def _klik_wyniku(self, it):
        self._uwaga('')
        self._wczytaj(it.data(Qt.UserRole))

    def _zaznacz_wynik(self):
        """Na liście wyników zaznaczone wydzielenie otwarte na karcie."""
        adr = (self.karta.adr or '').strip()
        self.lista_wynikow.blockSignals(True)
        self.lista_wynikow.clearSelection()
        for i in range(self.lista_wynikow.count()):
            it = self.lista_wynikow.item(i)
            if it.data(Qt.UserRole).strip() == adr:
                it.setSelected(True)
                self.lista_wynikow.setCurrentItem(it)
                break
        self.lista_wynikow.blockSignals(False)

    def wyczysc_wyszukiwanie(self):
        self.szukaj_wl.clear()
        self.szukaj_dz.clear()
        self._pokaz_wyniki([])
        self._uwaga('')
