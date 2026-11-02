# -*- coding: utf-8 -*-
"""Edytor opisu - lista wydzieleń bazy w osobnym oknie: filtry, sortowanie,
wczytanie wybranego wydzielenia do karty (także bez poligonu na warstwie -
tylko tak da się je obejrzeć i usunąć z bazy)."""
import os
import re

from PyQt5 import sip
from PyQt5.QtCore import QSettings, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from qgis.core import Qgis

from . import opis_adres as oa
from . import waypointy
from .znacznik_czasu import znacznik

TYTUL = 'Lista wydzieleń'
KLUCZ_SZEROKOSCI = 'LASR/opis_lista/szerokosci_kolumn'
_SZEROKOSC_STANU = 44

# (pole wiersza, nagłówek) - kolejność kolumn
KOLUMNY = (('gmina', 'Gmina'), ('obreb', 'Obręb'), ('grupa', 'Grupa'),
           ('oddz', 'Oddział'), ('wydz', 'Wydzielenie'), ('adr', 'Adres leśny'),
           ('rodzaj', 'Rodzaj pow.'), ('pow', 'Pow. [ha]'),
           ('status', 'Stan'))
FILTRY = ('gmina', 'obreb', 'grupa', 'oddz', 'wydz', 'rodzaj')
_NAGLOWKI = dict(KOLUMNY)
_KOL_ADR = [k[0] for k in KOLUMNY].index('adr')
_KOL_STATUS = [k[0] for k in KOLUMNY].index('status')
_PUSTE = '(puste)'

# stan wydzielenia - błąd ma pierwszeństwo przed ostrzeżeniem
BLAD, OSTRZEZENIE = 'blad', 'ostrzezenie'
_WAGA = {BLAD: 0, OSTRZEZENIE: 1, '': 2}   # sortowanie: czerwone na górze
_KOLOR = {BLAD: '#c62828', OSTRZEZENIE: '#ef8c00'}
_ROZMIAR_ZNAKU = 12


def status_uwag(bledy, ostrzezenia):
    return BLAD if bledy else OSTRZEZENIE if ostrzezenia else ''


def _kwadrat(status):
    px = QPixmap(_ROZMIAR_ZNAKU, _ROZMIAR_ZNAKU)
    px.fill(QColor(_KOLOR[status]))
    malarz = QPainter(px)
    malarz.setPen(QColor(_KOLOR[status]).darker(130))
    malarz.drawRect(0, 0, _ROZMIAR_ZNAKU - 1, _ROZMIAR_ZNAKU - 1)
    malarz.end()
    return px


def _t(wartosc):
    return '' if wartosc is None else str(wartosc).strip()


def klucz_naturalny(tekst):
    """Sortowanie z liczbami: 2 przed 10, a przed ax."""
    return [(0, int(c), '') if c.isdigit() else (1, 0, c.lower())
            for c in re.findall(r'\d+|\D+', _t(tekst))]


def _etykieta(numer, nazwa):
    return f'{numer} {nazwa}'.strip()


def _slownik_nazw(cur, sql, liczba_kluczy):
    """{sklejone kody: nazwa} - brak tabeli daje same numery."""
    try:
        return {''.join(_t(x) for x in w[:liczba_kluczy]): _t(w[liczba_kluczy])
                for w in cur.execute(sql).fetchall()}
    except Exception:
        return {}


def wczytaj_wiersze(cur, poligony, uwagi=None):
    """Wiersze listy (słowniki). poligony: adresy leśne obecne na warstwie,
    uwagi: {ARODES_INT_NUM: (błędy, ostrzeżenia)}."""
    uwagi = uwagi or {}
    gminy = _slownik_nazw(
        cur, 'select DISTRICT_CD, MUNICIPALITY_CD, MUNICIPALITY_NAME '
        'from F_MUNICIPALITY', 2)
    obreby = _slownik_nazw(
        cur, 'select DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, '
        'COMMUNITY_NAME from F_COMMUNITY', 3)
    wiersze = []
    for aint, adr, rodzaj, pow_ha in cur.execute(
            "select a.ARODES_INT_NUM, a.ADRESS_FOREST, s.AREA_TYPE_CD, "
            "s.SUB_AREA "
            "from F_ARODES as a left join F_SUBAREA as s "
            "on a.ARODES_INT_NUM = s.ARODES_INT_NUM "
            "where a.ARODES_TYP_CD = 'WYDZIEL'").fetchall():
        adr = '' if adr is None else str(adr)
        cz = oa.skladowe(adr) or dict.fromkeys(oa.CZESCI, '')
        bledy, ostrz = uwagi.get(aint, (0, 0))
        wiersze.append({
            'adr': adr,
            'gmina': _etykieta(adr[3:6], gminy.get(adr[1:6], '')),
            'obreb': _etykieta(cz['obreb'], obreby.get(adr[1:10], '')),
            'grupa': cz['grp'],
            'oddz': cz['oddz'],
            'wydz': cz['wydz'],
            'rodzaj': _t(rodzaj),
            'pow': None if pow_ha is None else float(pow_ha),
            'poligon': adr.strip() in poligony,
            'bledy': bledy,
            'ostrzezenia': ostrz,
            'status': status_uwag(bledy, ostrz),
        })
    return wiersze


def pasuje(wiersz, filtry, bez_poligonu=False, puste=False, pomin=None,
           statusy=None):
    """filtry: {pole: wartość} (None - bez filtra); pomin - pole, którego
    filtra nie brać pod uwagę (opcje listy zależą od pozostałych). puste -
    tylko bez rodzaju powierzchni (jak "Pokaż puste opisy"). statusy -
    dozwolone stany: wydzielenie ma jeden, więc to "lub" (puste = bez filtra)."""
    if bez_poligonu and wiersz['poligon']:
        return False
    if puste and wiersz['rodzaj']:
        return False
    if statusy and wiersz['status'] not in statusy:
        return False
    return all(w is None or k == pomin or wiersz[k] == w
               for k, w in filtry.items())


def opcje_filtra(wiersze, pole, filtry, **flagi):
    """Wartości pola w wierszach spełniających pozostałe filtry."""
    return sorted({w[pole] for w in wiersze
                   if pasuje(w, filtry, pomin=pole, **flagi)},
                  key=klucz_naturalny)


def _pow_tekst(v):
    return '' if v is None else f'{v:.4f}'.replace('.', ',')


def nazwa_sekcji(filtry, bez_poligonu=False, puste=False, statusy=None):
    """Sekcja w Nawigatorze - skąd ta lista: 'Lista wydzieleń: ZRĄB, 0001 ...'."""
    czesci = [filtry[p] or _PUSTE for p in FILTRY
              if filtry.get(p) is not None]
    if puste:
        czesci.append('puste')
    if bez_poligonu:
        czesci.append('bez poligonu')
    statusy = statusy or ()
    if BLAD in statusy:
        czesci.append('błędy')
    if OSTRZEZENIE in statusy:
        czesci.append('ostrzeżenia')
    return f"{TYTUL}: {', '.join(czesci)}" if czesci else TYTUL


def wiersze_nawigatora(wiersze, sekcja):
    """(wiersze waypointów, ile pominięto) - bez poligonów Nawigator nie ma
    czego pokazać na mapie."""
    wyn = [waypointy.wiersz(
        TYTUL, sekcja, 'ADR_LES', w['adr'].strip(),
        ', '.join(x for x in (
            w['rodzaj'], _pow_tekst(w['pow']) and
            f"{_pow_tekst(w['pow'])} ha") if x))
        for w in wiersze if w['poligon']]
    return wyn, len(wiersze) - len(wyn)


class _Komorka(QTableWidgetItem):
    """Sortuje po kluczu, nie po tekście (oddział 2 przed 10)."""

    def __init__(self, tekst, klucz):
        super().__init__(tekst)
        self.klucz = klucz
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)

    def __lt__(self, inna):
        return self.klucz < getattr(inna, 'klucz', self.klucz)


class ListaWydzielen(QWidget):
    """Okno niemodalne - zostaje otwarte w czasie pracy na karcie."""

    def __init__(self, panel):
        super().__init__(panel.iface.mainWindow(), Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.panel = panel
        self.wiersze = []
        self.setWindowTitle(TYTUL)
        self.resize(860, 620)

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()
        self.combo = {}
        for i, pole in enumerate(FILTRY):
            siatka.addWidget(QLabel(_NAGLOWKI[pole]), 0, i)
            c = QComboBox()
            c.currentIndexChanged.connect(self._zmiana_filtra)
            self.combo[pole] = c
            siatka.addWidget(c, 1, i)
            siatka.setColumnStretch(i, 3 if pole in ('gmina', 'obreb') else 1)
        uklad.addLayout(siatka)

        h = QHBoxLayout()
        self.cb_puste = QCheckBox('Puste wydzielenia')
        self.cb_puste.setToolTip('Wydzielenia bez rodzaju powierzchni (pusty '
                                 'AREA_TYPE_CD albo brak rekordu F_SUBAREA)')
        self.cb_puste.toggled.connect(self._zmiana_filtra)
        h.addWidget(self.cb_puste)
        self.cb_bez_pol = QCheckBox('Bez poligonu')
        self.cb_bez_pol.setToolTip(
            'Wydzielenia, które są w bazie, ale nie mają poligonu na warstwie '
            'wydzieleń')
        self.cb_bez_pol.toggled.connect(self._zmiana_filtra)
        h.addWidget(self.cb_bez_pol)
        b = QPushButton('Wyczyść filtry')
        b.clicked.connect(self._wyczysc_filtry)
        h.addWidget(b)
        h.addStretch(1)
        # przy prawej krawędzi, nad kolumną stanu
        self.cb_bledy = QCheckBox('Błędy')
        self.cb_bledy.setToolTip('Wydzielenia z czerwonym kwadratem')
        self.cb_ostrz = QCheckBox('Ostrzeżenia')
        self.cb_ostrz.setToolTip('Wydzielenia z pomarańczowym kwadratem')
        for cb in (self.cb_bledy, self.cb_ostrz):
            cb.toggled.connect(self._zmiana_filtra)
            h.addWidget(cb)
        uklad.addLayout(h)

        self.tabela = QTableWidget(0, len(KOLUMNY))
        self.tabela.setHorizontalHeaderLabels([k[1] for k in KOLUMNY])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.verticalHeader().setDefaultSectionSize(22)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # szerokości zmienia użytkownik, startowe ustawia _ustaw_kolumny
        naglowek = self.tabela.horizontalHeader()
        naglowek.setSectionResizeMode(QHeaderView.Interactive)
        naglowek.setSectionResizeMode(_KOL_STATUS, QHeaderView.Fixed)
        self.tabela.setColumnWidth(_KOL_STATUS, _SZEROKOSC_STANU)
        self.tabela.horizontalHeaderItem(_KOL_STATUS).setToolTip(
            'Reguły karty opisu (warstwy, gatunki, PNSW): czerwony - błędy, '
            'pomarańczowy - same ostrzeżenia. Kontrole SULMN i zabiegów nie '
            'są tu liczone. Sortowanie: czerwone na górze.')
        self.tabela.setSortingEnabled(True)
        self.tabela.sortByColumn(_KOL_ADR, Qt.AscendingOrder)
        self.tabela.activated.connect(lambda _: self.wczytaj_wybrane())
        self.tabela.itemSelectionChanged.connect(self._odswiez_przycisk)
        uklad.addWidget(self.tabela, 1)

        h = QHBoxLayout()
        b = QPushButton('Odśwież')
        b.setToolTip('Czyta listę z bazy i warstwy od nowa')
        b.clicked.connect(self.odswiez)
        h.addWidget(b)
        self.lbl_ile = QLabel()
        h.addWidget(self.lbl_ile)
        h.addStretch(1)
        self.btn_nawigator = QPushButton('Załaduj do Nawigatora')
        self.btn_nawigator.setToolTip(
            'Przerzuca aktualnie widoczną listę, w tej kolejności, do '
            'Nawigatora błędów i ustawia go na warstwę Edytora: przechodzenie '
            'po pozycjach przełącza kartę. Wydzielenia bez poligonu są '
            'pomijane.')
        self.btn_nawigator.clicked.connect(self.zaladuj_do_nawigatora)
        h.addWidget(self.btn_nawigator)
        self.btn_wczytaj = QPushButton('Wczytaj do edytora')
        self.btn_wczytaj.setToolTip(
            'Otwiera wydzielenie na karcie (także dwuklik albo Enter). '
            'Poligon zostaje zaznaczony i przybliżony na mapie, a '
            'usunąć z bazy można czerwonym przyciskiem na karcie.')
        self.btn_wczytaj.clicked.connect(self.wczytaj_wybrane)
        h.addWidget(self.btn_wczytaj)
        b = QPushButton('Zamknij')
        b.clicked.connect(self.close)
        h.addWidget(b)
        uklad.addLayout(h)

        self.odswiez()
        # po ułożeniu okna, żeby znać faktyczną szerokość tabeli
        self._kolumny_ustawione = False

    # -------------------------------------------------- szerokości kolumn

    def showEvent(self, zdarzenie):
        super().showEvent(zdarzenie)
        if not self._kolumny_ustawione:
            self._kolumny_ustawione = True
            QTimer.singleShot(0, self._ustaw_kolumny)

    def closeEvent(self, zdarzenie):
        if self._kolumny_ustawione:
            QSettings().setValue(
                KLUCZ_SZEROKOSCI,
                [str(self.tabela.columnWidth(i)) for i in range(len(KOLUMNY))])
        super().closeEvent(zdarzenie)

    def _ustaw_kolumny(self):
        """Szerokości z poprzedniego otwarcia, a przy pierwszym: dopasowane
        do treści, z wolnym miejscem dla adresu leśnego."""
        if sip.isdeleted(self):
            return
        zapisane = QSettings().value(KLUCZ_SZEROKOSCI)
        try:
            szerokosci = [int(x) for x in zapisane or []]
        except (TypeError, ValueError):
            szerokosci = []
        t = self.tabela
        if len(szerokosci) == len(KOLUMNY):
            for i, szer in enumerate(szerokosci):
                t.setColumnWidth(i, szer)
            return
        t.resizeColumnsToContents()
        t.setColumnWidth(_KOL_STATUS, _SZEROKOSC_STANU)
        zajete = sum(t.columnWidth(i) for i in range(len(KOLUMNY)))
        wolne = t.viewport().width() - zajete
        if wolne > 0:
            t.setColumnWidth(_KOL_ADR, t.columnWidth(_KOL_ADR) + wolne)

    # ------------------------------------------------------------- dane

    def odswiez(self):
        """Od nowa z bazy i warstwy; filtry i wybrany wiersz zostają."""
        wybrany = self.wybrany_adres()
        self.wiersze = wczytaj_wiersze(self.panel.baza.cur,
                                       set(self.panel.poligony_adresow()),
                                       self.panel.uwagi_wydzielen())
        self._pokaz(wybrany)

    def _filtry(self):
        return {p: c.currentData() for p, c in self.combo.items()}

    def _flagi(self):
        statusy = {BLAD} if self.cb_bledy.isChecked() else set()
        if self.cb_ostrz.isChecked():
            statusy.add(OSTRZEZENIE)
        return {'bez_poligonu': self.cb_bez_pol.isChecked(),
                'puste': self.cb_puste.isChecked(), 'statusy': statusy}

    def _zmiana_filtra(self, *_):
        self._pokaz(self.wybrany_adres())

    def _wyczysc_filtry(self):
        for c in self.combo.values():
            c.blockSignals(True)
            c.setCurrentIndex(0)
            c.blockSignals(False)
        for cb in (self.cb_puste, self.cb_bez_pol, self.cb_bledy,
                   self.cb_ostrz):
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._pokaz(self.wybrany_adres())

    def _odbuduj_filtry(self):
        """Opcje filtra wg pozostałych filtrów; wartość, której już nie ma,
        wraca do "(wszystkie)"."""
        flagi = self._flagi()
        for pole, c in self.combo.items():
            filtry = self._filtry()
            obecna = filtry[pole]
            opcje = opcje_filtra(self.wiersze, pole, filtry, **flagi)
            c.blockSignals(True)
            c.clear()
            c.addItem('(wszystkie)', None)
            for w in opcje:
                c.addItem(w or _PUSTE, w)
            i = c.findData(obecna) if obecna is not None else 0
            c.setCurrentIndex(max(i, 0))
            c.blockSignals(False)

    def _pokaz(self, wybrany=None):
        self._odbuduj_filtry()
        filtry = self._filtry()
        flagi = self._flagi()
        widoczne = [w for w in self.wiersze if pasuje(w, filtry, **flagi)]

        t = self.tabela
        t.blockSignals(True)
        t.setSortingEnabled(False)
        t.clearContents()
        t.setRowCount(len(widoczne))
        for r, w in enumerate(widoczne):
            for c, (pole, _n) in enumerate(KOLUMNY):
                if pole == 'pow':
                    kom = _Komorka(_pow_tekst(w['pow']),
                                   -1.0 if w['pow'] is None else w['pow'])
                    kom.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif pole == 'status':
                    kom = _Komorka('', _WAGA[w['status']])
                    if w['status']:
                        kom.setData(Qt.DecorationRole, _kwadrat(w['status']))
                        kom.setToolTip(f"błędy: {w['bledy']}, ostrzeżenia: "
                                       f"{w['ostrzezenia']}")
                else:
                    kom = _Komorka(w[pole], klucz_naturalny(w[pole]))
                t.setItem(r, c, kom)
        t.setSortingEnabled(True)
        t.blockSignals(False)

        self.lbl_ile.setText(f'Pokazano {len(widoczne)} z {len(self.wiersze)}')
        self._zaznacz(wybrany)
        self._odswiez_przycisk()

    def _zaznacz(self, adres):
        if not adres:
            return
        for r in range(self.tabela.rowCount()):
            if self.tabela.item(r, _KOL_ADR).text() == adres:
                self.tabela.selectRow(r)
                self.tabela.scrollToItem(self.tabela.item(r, _KOL_ADR))
                return

    # ------------------------------------------------------------ wybór

    def wybrany_adres(self):
        if not hasattr(self, 'tabela') or sip.isdeleted(self.tabela):
            return None
        wiersze = self.tabela.selectionModel().selectedRows()
        if not wiersze:
            return None
        return self.tabela.item(wiersze[0].row(), _KOL_ADR).text()

    def _odswiez_przycisk(self):
        self.btn_wczytaj.setEnabled(self.wybrany_adres() is not None)
        self.btn_nawigator.setEnabled(self.tabela.rowCount() > 0)

    # -------------------------------------------------------- Nawigator

    def widoczne_w_kolejnosci(self):
        """Wiersze tabeli tak, jak są teraz posortowane."""
        po_adresie = {w['adr']: w for w in self.wiersze}
        return [po_adresie[self.tabela.item(r, _KOL_ADR).text()]
                for r in range(self.tabela.rowCount())]

    def zaladuj_do_nawigatora(self):
        bar = self.panel.iface.messageBar()
        sekcja = nazwa_sekcji(self._filtry(), **self._flagi())
        wiersze, pominieto = wiersze_nawigatora(
            self.widoczne_w_kolejnosci(), sekcja)
        if not wiersze:
            bar.pushMessage(TYTUL, 'Żadne z widocznych wydzieleń nie ma '
                            'poligonu - nie ma czego pokazać w Nawigatorze.',
                            Qgis.Warning, 6)
            return
        katalog, plik = os.path.split(os.path.abspath(self.panel.baza_sc))
        sciezka = os.path.join(
            waypointy.katalog_raportow(katalog),
            f'lista_wydzielen_waypointy_{os.path.splitext(plik)[0]}_'
            f'{znacznik()}.csv')
        try:
            waypointy.zapisz(sciezka, wiersze)
        except OSError as e:
            bar.pushMessage(TYTUL, f'Nie udało się zapisać pliku: {e}',
                            Qgis.Critical, 8)
            return
        self.panel.listaDoNawigatora.emit(sciezka, self.panel.lyr)
        tekst = f'Załadowano do Nawigatora: {len(wiersze)}'
        if pominieto:
            tekst += f', pominięto {pominieto} bez poligonu'
        bar.pushMessage(TYTUL, tekst, Qgis.Success, 6)

    def wczytaj_wybrane(self):
        adres = self.wybrany_adres()
        if adres:
            self.panel.pokaz_wydzielenie(adres)
