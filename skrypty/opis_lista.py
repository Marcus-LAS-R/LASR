# -*- coding: utf-8 -*-
"""Edytor opisu - lista wydzieleń bazy w osobnym oknie: filtry, sortowanie,
wczytanie wybranego wydzielenia do karty (także bez poligonu na warstwie -
tylko tak da się je obejrzeć i usunąć z bazy)."""
import re

from PyQt5 import sip
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from . import opis_adres as oa

TYTUL = 'Lista wydzieleń'

# (pole wiersza, nagłówek) - kolejność kolumn
KOLUMNY = (('gmina', 'Gmina'), ('obreb', 'Obręb'), ('grupa', 'Grupa'),
           ('oddz', 'Oddział'), ('wydz', 'Wydzielenie'), ('adr', 'Adres leśny'),
           ('rodzaj', 'Rodzaj pow.'), ('pow', 'Pow. [ha]'))
FILTRY = ('gmina', 'obreb', 'grupa', 'oddz', 'wydz', 'rodzaj')
_NAGLOWKI = dict(KOLUMNY)
_KOL_ADR = [k[0] for k in KOLUMNY].index('adr')
_PUSTE = '(puste)'


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


def wczytaj_wiersze(cur, poligony):
    """Wiersze listy (słowniki). poligony: adresy leśne obecne na warstwie."""
    gminy = _slownik_nazw(
        cur, 'select DISTRICT_CD, MUNICIPALITY_CD, MUNICIPALITY_NAME '
        'from F_MUNICIPALITY', 2)
    obreby = _slownik_nazw(
        cur, 'select DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, '
        'COMMUNITY_NAME from F_COMMUNITY', 3)
    wiersze = []
    for adr, rodzaj, pow_ha in cur.execute(
            "select a.ADRESS_FOREST, s.AREA_TYPE_CD, s.SUB_AREA "
            "from F_ARODES as a left join F_SUBAREA as s "
            "on a.ARODES_INT_NUM = s.ARODES_INT_NUM "
            "where a.ARODES_TYP_CD = 'WYDZIEL'").fetchall():
        adr = '' if adr is None else str(adr)
        cz = oa.skladowe(adr) or dict.fromkeys(oa.CZESCI, '')
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
        })
    return wiersze


def pasuje(wiersz, filtry, tylko_bez_poligonu=False, pomin=None):
    """filtry: {pole: wartość} (None - bez filtra); pomin - pole, którego
    filtra nie brać pod uwagę (opcje listy zależą od pozostałych)."""
    if tylko_bez_poligonu and wiersz['poligon']:
        return False
    return all(w is None or k == pomin or wiersz[k] == w
               for k, w in filtry.items())


def opcje_filtra(wiersze, pole, filtry, tylko_bez_poligonu=False):
    """Wartości pola w wierszach spełniających pozostałe filtry."""
    return sorted({w[pole] for w in wiersze
                   if pasuje(w, filtry, tylko_bez_poligonu, pomin=pole)},
                  key=klucz_naturalny)


def _pow_tekst(v):
    return '' if v is None else f'{v:.4f}'.replace('.', ',')


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
        self.cb_bez_pol = QCheckBox('Tylko bez poligonu na warstwie')
        self.cb_bez_pol.setToolTip(
            'Wydzielenia, które są w bazie, ale nie mają poligonu na warstwie '
            'wydzieleń')
        self.cb_bez_pol.toggled.connect(self._zmiana_filtra)
        h.addWidget(self.cb_bez_pol)
        b = QPushButton('Wyczyść filtry')
        b.clicked.connect(self._wyczysc_filtry)
        h.addWidget(b)
        h.addStretch(1)
        self.lbl_ile = QLabel()
        h.addWidget(self.lbl_ile)
        uklad.addLayout(h)

        self.tabela = QTableWidget(0, len(KOLUMNY))
        self.tabela.setHorizontalHeaderLabels([k[1] for k in KOLUMNY])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.verticalHeader().setDefaultSectionSize(22)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setStretchLastSection(True)
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
        h.addStretch(1)
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

    # ------------------------------------------------------------- dane

    def odswiez(self):
        """Od nowa z bazy i warstwy; filtry i wybrany wiersz zostają."""
        wybrany = self.wybrany_adres()
        self.wiersze = wczytaj_wiersze(self.panel.baza.cur,
                                       set(self.panel.poligony_adresow()))
        self._pokaz(wybrany)

    def _filtry(self):
        return {p: c.currentData() for p, c in self.combo.items()}

    def _zmiana_filtra(self, *_):
        self._pokaz(self.wybrany_adres())

    def _wyczysc_filtry(self):
        for c in self.combo.values():
            c.blockSignals(True)
            c.setCurrentIndex(0)
            c.blockSignals(False)
        self.cb_bez_pol.blockSignals(True)
        self.cb_bez_pol.setChecked(False)
        self.cb_bez_pol.blockSignals(False)
        self._pokaz(self.wybrany_adres())

    def _odbuduj_filtry(self):
        """Opcje filtra wg pozostałych filtrów; wartość, której już nie ma,
        wraca do "(wszystkie)"."""
        tylko = self.cb_bez_pol.isChecked()
        for pole, c in self.combo.items():
            filtry = self._filtry()
            obecna = filtry[pole]
            opcje = opcje_filtra(self.wiersze, pole, filtry, tylko)
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
        tylko = self.cb_bez_pol.isChecked()
        widoczne = [w for w in self.wiersze if pasuje(w, filtry, tylko)]

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

    def wczytaj_wybrane(self):
        adres = self.wybrany_adres()
        if adres:
            self.panel.pokaz_wydzielenie(adres)
