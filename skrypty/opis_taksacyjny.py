"""Podgląd/Edycja opisu taksacyjnego - zakotwiczony panel połączenia z
bazą (PanelOpisu) + pływające okno karty opisu wydzielenia (OknoOpisu) w
układzie jak w Taksatorze (Opis wydzielenia / Opis drzewostanu: warstwy +
gatunki / Wskazania gospodarcze / Informacje różne).

Panel otwarty = baza podłączona:
- w panelu wybór warstwy wydzieleń (domyślnie WYDZ, pole ADR_LES) i
  "Połącz bazę..." (jawny wybór .mdb); zamknięcie panelu albo "Rozłącz"
  zamyka kartę i rozłącza bazę; zamknięcie samej karty bazy nie rozłącza,
- plik blokady .ldb/.laccdb obok bazy (baza otwarta np. w Taksatorze) ->
  tryb tylko do podglądu (sprawdzane przed własnym połączeniem, które też
  tworzy .ldb),
- kontrola zgodności warstwa-baza (raport, praca możliwa dalej),
- zaznaczenie jednego wydzielenia na warstwie otwiera/przełącza kartę,
- edytowalne: "Opis wydzielenia" (F_SUBAREA, cechy F_AROD_STAND_PEC i TD =
  F_AROD_GOAL typ 'D' - jako osobne wiersze, jak w Taksatorze) i
  "Informacje różne" (SUBAREA_INFO); warstwy, gatunki i zabiegi podgląd,
- pola kodów: rozwijana lista albo wpisanie kodu lub numeru jak w
  Taksatorze (SO albo 1, D-STAN albo 92) - numery ze słowników TEJ bazy
  (kolumny *_NR, dla gatunków BUL_SPECIES_NR; numery rodzaju powierzchni
  różnią się między bazami),
- nic nie jest przeliczane (zasobność, przyrost - robi to Taksator PU),
- zapis w jednej transakcji, kopia bazy raz na połączenie,
- okno karty tylko rośnie (maks. 90% ekranu, powyżej - przewijanie).
"""
import copy
import os
from collections import Counter

from PyQt5 import sip
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QDoubleValidator, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QCompleter, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QStyledItemDelegate, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from .baza_wrapper import Baza, zajmij_baze, zwolnij_baze

SZARY = QColor(225, 225, 225)
ZMIENIONE = QColor(255, 243, 190)
MAX_INFO = 255  # F_SUBAREA.SUBAREA_INFO VARCHAR(255)

# pole -> (tabela słownika, kolumna kodu, kolumna nazwy, kolumna numeru)
SLOWNIKI = {
    'AREA_TYPE_CD': ('F_AREA_TYPE_DIC', 'area_type_cd', 'area_type_name',
                     'area_type_nr'),
    'FOREST_PEC_CD': ('F_FOREST_PEC_DIC', 'FOREST_PEC_CD', 'FOREST_PEC_NAME',
                      'FOREST_PEC_NR'),
    'STAND_STRUCT_CD': ('F_STAND_STRUCT_DIC', 'STAND_STRUCT_CD',
                        'STAND_STRUCT_NAME', 'STAND_STRUCT_NR'),
    'DAMAGE_DEGREE_CD': ('F_DAMAGE_DEGR_DIC', 'DAMAGE_DEGREE_CD',
                         'DAMAGE_DEGREE_NAME', 'DAMAGE_DEGREE_NR'),
    'CAUSE_CD': ('F_END_CAUSE_DIC', 'CAUSE_CD', 'CAUSE_NAME', 'CAUSE_NR'),
    'SITE_TYPE_CD': ('F_SITE_TYPE_DIC', 'SITE_TYPE_CD', 'SITE_TYPE_NAME',
                     'SITE_TYPE_NR'),
    'VEG_COVER_CD': ('F_VEG_COVER_DIC', 'VEG_COVER_CD', 'VEG_COVER_NAME',
                     'VEG_COVER_NR'),
    'SPECIES_CD': ('F_TREE_SPECIES', 'SPECIES_CD', 'SPECIES_NAME',
                   'BUL_SPECIES_NR'),
}

# górny wiersz: (nagłówek, pole, typ, słownik)
# typ: 'kod' - jeden kod, 'lista' - kilka kodów w osobnych wierszach,
# 'liczba'. Szerokości liczone z najdłuższego kodu (_szerokosci_opisu).
KOLUMNY_OPIS = [
    ('Rodz.\npow.', 'AREA_TYPE_CD', 'kod', 'AREA_TYPE_CD'),
    ('Cecha\ndrzewost.', 'FOREST_PEC_CD', 'lista', 'FOREST_PEC_CD'),
    ('Budowa\npion.', 'STAND_STRUCT_CD', 'kod', 'STAND_STRUCT_CD'),
    ('Stopień\nuszk.', 'DAMAGE_DEGREE_CD', 'kod', 'DAMAGE_DEGREE_CD'),
    ('Gł. przycz.\nzagr.', 'CAUSE_CD', 'kod', 'CAUSE_CD'),
    ('TSL', 'SITE_TYPE_CD', 'kod', 'SITE_TYPE_CD'),
    ('TD', 'TD', 'lista', 'SPECIES_CD'),
    ('Typ\npokrywy', 'VEG_COVER_CD', 'kod', 'VEG_COVER_CD'),
    ('Drewno\nmartwe', 'DEAD_WOOD', 'liczba', None),
]
POLA_SUBAREA = [
    'AREA_TYPE_CD', 'STAND_STRUCT_CD', 'DAMAGE_DEGREE_CD', 'CAUSE_CD',
    'SITE_TYPE_CD', 'VEG_COVER_CD', 'DEAD_WOOD', 'SUBAREA_INFO',
]

# warstwa: (nagłówek, kolumna, miejsca po przecinku albo None = tekst, szer.)
KOLUMNY_WARSTWY = [
    ('Zmiesz.', 'MIXTURE_CD', None, 55),
    ('Zwarcie', 'DENSITY_CD', None, 55),
    ('Zd.', 'STANDDENSITY_INDEX', 2, 42),
    ('Zagęszcz.', 'TREE_STOCK_CD', None, 65),
    ('Lokal.', 'LOCATION_CD', None, 50),
]
# gatunki: (nagłówek, kolumna, miejsca, szerokość, szara = liczona)
KOLUMNY_GATUNKI = [
    ('Kod', 'SPECIES_CD', None, 48, False),
    ('Udział', 'PART_CD', None, 48, False),
    ('Wiek', 'SPECIES_AGE', 0, 40, False),
    ('D 13', 'BHD', 0, 40, False),
    ('Wys.', 'HEIGHT', 0, 40, False),
    ('Bonit.', 'SITE_CLASS_CD', None, 45, False),
    ('Zasob.', 'VOLUME', 0, 50, False),
]
KOLUMNY_ZABIEGI = [
    ('Grupa\nczynności', 'MEASURE_CD', None, 80, False),
    ('Pilność\nzabiegu', 'URGENCY', 'bool', 55, False),
    ('% pow.\nwydz.', 'PROC_AREA', 0, 50, False),
    ('Pow.', 'CUTTING_AREA', 4, 60, False),
    ('% grub.', 'LARGE_TIMBER_PERC', 0, 50, False),
    ('m3 grub.', 'LARGE_TIMBER_VALUE', 0, 60, True),
]


# ---------------------------------------------------------------- pomocnicze

def _pusty(v):
    return v is None or str(v).strip() in ('', 'NULL', 'None')


def _txt(v):
    return '' if _pusty(v) else str(v).strip()


def _fmt(v, miejsca):
    """Liczba po polsku (przecinek) z podaną liczbą miejsc po przecinku,
    tekst bez zmian, None -> ''."""
    if _pusty(v):
        return ''
    if miejsca is None:
        return str(v).strip()
    if miejsca == 'bool':
        return '☑' if v not in (0, '0', False) else '☐'
    try:
        return f'{float(v):.{miejsca}f}'.replace('.', ',')
    except (TypeError, ValueError):
        return str(v)


def _nr_txt(nr):
    try:
        f = float(nr)
        return str(int(f)) if f.is_integer() else str(f)
    except (TypeError, ValueError):
        return str(nr).strip()


def _plik_blokady(baza_sc):
    rdzen = os.path.splitext(baza_sc)[0]
    for ext in ('.ldb', '.laccdb'):
        if os.path.isfile(rdzen + ext):
            return rdzen + ext
    return None


class Slownik:
    """Kody słownika bazy z nazwami i numerami (jak w Taksatorze: SO=1).
    Numer jest wyłączany, jeśli któryś numer jest jednocześnie kodem innej
    pozycji tego słownika (np. stopień uszkodzeń '0'/'1') - wtedy
    wpisana liczba zawsze oznacza kod."""

    def __init__(self, wiersze):
        self.kody = []
        self.nazwy = {}
        self.nr_kod = {}
        self.kod_nr = {}
        for kod, nazwa, nr in wiersze:
            if _pusty(kod):
                continue
            kod = str(kod).strip()
            self.kody.append(kod)
            self.nazwy[kod] = _txt(nazwa)
            if not _pusty(nr):
                n = _nr_txt(nr)
                self.nr_kod[n] = kod
                self.kod_nr[kod] = n
        self.numery = not any(
            n in self.nazwy and k != n for n, k in self.nr_kod.items())
        self._upper = {}
        for k in self.kody:
            self._upper.setdefault(k.upper(), []).append(k)

    def rozwiaz(self, tekst):
        """Kod dla wpisanego tekstu (kod, kod małymi literami, numer albo
        pozycja z listy "KOD | nr") albo None."""
        t = str(tekst).split(' | ')[0].strip()
        if t in self.nazwy:
            return t
        kand = self._upper.get(t.upper(), [])
        if len(kand) == 1:
            return kand[0]
        if self.numery and t.isdigit() and t in self.nr_kod:
            return self.nr_kod[t]
        return None

    def pozycja(self, kod):
        """Tekst pozycji na liście/w podpowiedzi: "KOD | nr" (bez nazwy)."""
        nr = self.kod_nr.get(kod) if self.numery else None
        return f'{kod} | {nr}' if nr else kod

    def pozycje(self):
        return [self.pozycja(k) for k in self.kody]

    def opis(self, kod):
        if not kod:
            return ''
        nr = self.kod_nr.get(kod)
        dop = f' (nr {nr})' if nr and self.numery else ''
        return f'{kod} - {self.nazwy.get(kod, "?")}{dop}'


def rozbij_adres(adr):
    """Czytelne części adresu leśnego UPUL
    (COUNTY_L[0] DISTRICT[1:3] MUNICIP[3:6] COMMUNITY[6:10] - GRP[11:13]
    ODDZ[13:17] - WYDZ[18:22] - SUFIKS): '0001    10    1-d' albo ''."""
    if not adr or len(adr) < 22:
        return ''
    obreb, grp = adr[6:10].strip(), adr[11:13].strip()
    oddz, wydz = adr[13:17].strip(), adr[18:22].strip()
    return f'{obreb}    {grp}    {oddz}-{wydz}'


def wczytaj_slowniki(baza):
    wyn = {}
    for pole, (tab, kod, nazwa, nr) in SLOWNIKI.items():
        wiersze = baza.pobierz(f'select {kod}, {nazwa}, {nr} from {tab};')
        if wiersze:
            wyn[pole] = Slownik(wiersze)
    return wyn


def _warstwy_poligonowe():
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.geometryType() == QgsWkbTypes.PolygonGeometry
    ]


def sprawdz_zgodnosc(lyr, wydz_baza):
    """Porównanie ADR_LES warstwy z wydzieleniami bazy. Zwraca (czy_ok,
    krótkie podsumowanie, szczegóły)."""
    adr_warstwa = []
    puste = 0
    for f in lyr.getFeatures():
        v = f['ADR_LES']
        if _pusty(v):
            puste += 1
        else:
            adr_warstwa.append(str(v))
    zbior = set(adr_warstwa)
    duble = sorted(a for a, n in Counter(adr_warstwa).items() if n > 1)
    bez_opisu = sorted(zbior - set(wydz_baza))
    bez_poligonu = sorted(set(wydz_baza) - zbior)

    czesci, szczegoly = [], []
    for opis, lista in (
            ('wydzielenia w warstwie bez opisu w bazie', bez_opisu),
            ('opisy w bazie bez poligonu w warstwie', bez_poligonu),
            ('zdublowane ADR_LES w warstwie', duble)):
        if lista:
            czesci.append(f'{len(lista)} - {opis}')
            szczegoly.append(f'{opis.upper()} ({len(lista)}):\n'
                             + '\n'.join(lista[:300])
                             + ('\n...' if len(lista) > 300 else ''))
    if puste:
        czesci.append(f'{puste} - poligony z pustym ADR_LES')
    ok = not czesci
    podsum = (f'Warstwa: {len(zbior)} wydzieleń, baza: {len(wydz_baza)}.\n'
              + ('Warstwa i baza są zgodne.' if ok else
                 'Niezgodności:\n- ' + '\n- '.join(czesci)))
    return ok, podsum, '\n\n'.join(szczegoly)


# ------------------------------------------------------------ delegat edycji

class _DelegatOpisu(QStyledItemDelegate):
    """Pole kodu = rozwijana lista "KOD | nr" z możliwością wpisania kodu
    albo numeru (z podpowiedziami); pole liczbowe = zwykła linia."""

    def __init__(self, okno):
        super().__init__(okno)
        self.okno = okno

    def createEditor(self, parent, option, index):
        _nag, pole, typ, slow = KOLUMNY_OPIS[index.column()]
        if typ == 'liczba':
            ed = QLineEdit(parent)
            v = QDoubleValidator(0, 1e9, 2, ed)
            v.setNotation(QDoubleValidator.StandardNotation)
            ed.setValidator(v)
            return ed
        ed = QComboBox(parent)
        ed.setEditable(True)
        ed.setInsertPolicy(QComboBox.NoInsert)
        ed.setMaxVisibleItems(20)
        s = self.okno.slowniki.get(slow)
        if s is not None:
            ed.addItem('')
            ed.addItems(s.pozycje())
            comp = QCompleter(ed.model(), ed)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchStartsWith)
            comp.setCompletionMode(QCompleter.PopupCompletion)
            ed.setCompleter(comp)
        # wybór z listy myszką od razu zatwierdza
        ed.activated.connect(lambda _i, e=ed: self._zatwierdz(e))
        return ed

    def _zatwierdz(self, ed):
        self.commitData.emit(ed)
        self.closeEditor.emit(ed)

    def setEditorData(self, editor, index):
        tekst = index.data() or ''
        if isinstance(editor, QComboBox):
            editor.setEditText(tekst)
            editor.lineEdit().selectAll()
        else:
            editor.setText(tekst)

    def setModelData(self, editor, model, index):
        tekst = editor.currentText() if isinstance(editor, QComboBox) \
            else editor.text()
        pole = KOLUMNY_OPIS[index.column()][1]
        wiersz = index.row()
        # zatwierdzenie może wywołać przebudowę tabeli (liczba wierszy
        # cech/TD) - dlatego odroczone, poza obsługą edytora
        QTimer.singleShot(0, lambda: self.okno.ustaw_pole(
            pole, tekst, wiersz))


# ----------------------------------------------------------- grupa warstwy

class _GrupaWarstwy(QWidget):
    """Zwijana grupa: nagłówek z kodem warstwy, pod nim tabela parametrów
    warstwy (lewa) i gatunków (prawa) - jak w Taksatorze."""

    def __init__(self, warstwa, gatunki, parent=None):
        super().__init__(parent)
        self.kod = _txt(warstwa.get('STOREY_CD'))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)

        self.btn = QToolButton()
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn.setCheckable(True)
        self.btn.setStyleSheet(
            'QToolButton { border: none; font-weight: bold; }')
        self.btn.setText(f'{self.kod}   ({len(gatunki)} gat.)')
        self.btn.toggled.connect(self._przelacz)
        lay.addWidget(self.btn)

        self.cialo = QWidget()
        hl = QHBoxLayout(self.cialo)
        hl.setContentsMargins(14, 0, 0, 0)
        hl.setSpacing(4)

        tw = _tabela([k[0] for k in KOLUMNY_WARSTWY],
                     [k[3] for k in KOLUMNY_WARSTWY])
        tw.setRowCount(1)
        for c, (_n, kol, m, _s) in enumerate(KOLUMNY_WARSTWY):
            tw.setItem(0, c, _item(_fmt(warstwa.get(kol), m)))
        _dopasuj(tw)
        hl.addWidget(tw, 0, Qt.AlignTop)

        tg = _tabela([k[0] for k in KOLUMNY_GATUNKI],
                     [k[3] for k in KOLUMNY_GATUNKI])
        tg.setRowCount(len(gatunki))
        for r, g in enumerate(gatunki):
            for c, (_n, kol, m, _s, szara) in enumerate(KOLUMNY_GATUNKI):
                tg.setItem(r, c, _item(_fmt(g.get(kol), m), szara))
        _dopasuj(tg)
        hl.addWidget(tg, 0, Qt.AlignTop)
        hl.addStretch(1)
        lay.addWidget(self.cialo)
        self.ustaw(True)

    def _przelacz(self, rozwiniety):
        self.btn.setArrowType(Qt.DownArrow if rozwiniety else Qt.RightArrow)
        self.cialo.setVisible(rozwiniety)

    def ustaw(self, rozwiniety):
        self.btn.setChecked(rozwiniety)
        self._przelacz(rozwiniety)


SZEROKOSC_GRUPY = (14 + sum(k[3] for k in KOLUMNY_WARSTWY)
                   + sum(k[3] for k in KOLUMNY_GATUNKI) + 4 + 4 * 2)


def _tabela(naglowki, szerokosci):
    t = QTableWidget(0, len(naglowki))
    t.setHorizontalHeaderLabels(naglowki)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    t.verticalHeader().setDefaultSectionSize(20)
    for i, s in enumerate(szerokosci):
        t.setColumnWidth(i, s)
    t.setFixedWidth(sum(szerokosci) + 2 * t.frameWidth())
    return t


def _item(tekst, szary=False):
    it = QTableWidgetItem(tekst)
    if szary:
        it.setBackground(QBrush(SZARY))
    return it


def _dopasuj(t):
    """Wysokość tabeli = nagłówek + wszystkie wiersze (bez przewijania)."""
    h = t.horizontalHeader().sizeHint().height() + 2 * t.frameWidth()
    h += sum(t.rowHeight(r) for r in range(t.rowCount()))
    t.setFixedHeight(h)


def _sekcja(tytul):
    lbl = QLabel(tytul)
    f = lbl.font()
    f.setBold(True)
    lbl.setFont(f)
    return lbl


# --------------------------------------------------------------- okno karty

class OknoOpisu(QWidget):
    """Karta opisu - korzysta z połączenia panelu (PanelOpisu), sama nie
    łączy się z bazą i nie śledzi zaznaczenia (robi to panel)."""

    def __init__(self, panel):
        super().__init__(panel.iface.mainWindow(), Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.panel = panel
        self.iface = panel.iface
        self.lyr = panel.lyr
        self.baza = panel.baza
        self.baza_sc = panel.baza_sc
        self.tylko_odczyt = panel.tylko_odczyt
        self.slowniki = panel.slowniki
        self.wydz = panel.wydz
        self.adr = None
        self.aint = None
        self.dane = None
        self.oryginal = None
        self.grupy = []

        self._ustaw_tytul()
        self._zbuduj()
        self.zmiana_zaznaczenia()

    def _ustaw_tytul(self):
        czesci = [self.adr, rozbij_adres(self.adr)] if self.adr else []
        czesci.append('Opis taksacyjny')
        if self.tylko_odczyt:
            czesci.append('[TYLKO PODGLĄD]')
        self.setWindowTitle('   '.join(czesci))

    def _wiersze(self, sql, parametry):
        """Lista słowników {kolumna: wartość}."""
        cur = self.baza.cur
        cur.execute(sql, parametry)
        kol = [d[0] for d in cur.description]
        return [dict(zip(kol, w)) for w in cur.fetchall()]

    def _wczytaj(self, aint):
        sub = self._wiersze(
            'select * from F_SUBAREA where ARODES_INT_NUM = ?', (aint,))
        if not sub:
            return None
        s = sub[0]
        dane = {p: s.get(p) for p in POLA_SUBAREA}
        for p in POLA_SUBAREA:
            if p != 'DEAD_WOOD':
                dane[p] = _txt(dane[p])
        dane['FOREST_PEC_CD'] = [_txt(w['FOREST_PEC_CD']) for w in self._wiersze(
            'select FOREST_PEC_CD from F_AROD_STAND_PEC where '
            'ARODES_INT_NUM = ? order by PEC_RANK_ORDER', (aint,))]
        dane['TD'] = [_txt(w['SPECIES_CD']) for w in self._wiersze(
            "select SPECIES_CD from F_AROD_GOAL where ARODES_INT_NUM = ? "
            "and GOAL_TYPE_FL = 'D' order by GOAL_RANK_ORDER", (aint,))]
        warstwy = self._wiersze(
            'select * from F_AROD_STOREY where ARODES_INT_NUM = ? '
            'order by STOREY_RANK_ORDER', (aint,))
        gatunki = self._wiersze(
            'select * from F_STOREY_SPECIES where ARODES_INT_NUM = ? '
            'order by SPECIES_RANK_ORDER', (aint,))
        zabiegi = self._wiersze(
            'select * from F_AROD_CUE where ARODES_INT_NUM = ? '
            'order by CUE_RANK_ORDER', (aint,))
        return dane, warstwy, gatunki, zabiegi

    # ----------------------------------------------------------------- UI

    def _szerokosci_opisu(self):
        """Szerokość kolumn opisu z najdłuższego kodu słownika / linii
        nagłówka (+ miejsce na strzałkę listy)."""
        fm = self.fontMetrics()
        wyn = []
        for nag, _pole, typ, slow in KOLUMNY_OPIS:
            w = max(fm.width(linia) for linia in nag.split('\n')) + 14
            s = self.slowniki.get(slow)
            if s is not None and s.kody:
                w = max(w, max(fm.width(k) for k in s.kody) + 32)
            elif typ == 'liczba':
                w = max(w, fm.width('0000,00') + 14)
            wyn.append(w)
        return wyn

    def _zbuduj(self):
        glowny = QVBoxLayout(self)
        glowny.setContentsMargins(6, 6, 6, 6)

        gora = QHBoxLayout()
        self.lbl_adr = QLabel()
        f = QFont(self.lbl_adr.font())
        f.setBold(True)
        f.setPointSize(f.pointSize() + 2)
        self.lbl_adr.setFont(f)
        gora.addWidget(self.lbl_adr)
        self.lbl_status = QLabel()
        gora.addWidget(self.lbl_status, 1)
        glowny.addLayout(gora)

        self.przewijanie = QScrollArea()
        self.przewijanie.setWidgetResizable(True)
        self.przewijanie.setFrameShape(QFrame.NoFrame)
        self.tresc = QWidget()
        self.lay_tresc = QVBoxLayout(self.tresc)
        self.lay_tresc.setContentsMargins(0, 0, 0, 0)
        self.przewijanie.setWidget(self.tresc)
        glowny.addWidget(self.przewijanie)

        # --- opis wydzielenia
        self.lay_tresc.addWidget(_sekcja('Opis wydzielenia'))
        self.t_opis = QTableWidget(1, len(KOLUMNY_OPIS))
        self.t_opis.setHorizontalHeaderLabels([k[0] for k in KOLUMNY_OPIS])
        self.t_opis.verticalHeader().setVisible(False)
        self.t_opis.verticalHeader().setDefaultSectionSize(22)
        self.t_opis.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.t_opis.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.t_opis.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        szer = self._szerokosci_opisu()
        for i, w in enumerate(szer):
            self.t_opis.setColumnWidth(i, w)
        self.t_opis.setFixedWidth(sum(szer) + 2 * self.t_opis.frameWidth())
        self.t_opis.setItemDelegate(_DelegatOpisu(self))
        self.t_opis.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_opis.setEditTriggers(
            QAbstractItemView.NoEditTriggers if self.tylko_odczyt else
            QAbstractItemView.CurrentChanged | QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed)
        _dopasuj(self.t_opis)
        self.lay_tresc.addWidget(self.t_opis)

        # --- opis drzewostanu (grupy warstw)
        self.lay_tresc.addWidget(_sekcja('Opis drzewostanu'))
        self.kontener_warstw = QWidget()
        self.lay_warstw = QVBoxLayout(self.kontener_warstw)
        self.lay_warstw.setContentsMargins(0, 0, 0, 0)
        self.lay_warstw.setSpacing(2)
        self.lay_tresc.addWidget(self.kontener_warstw)

        # --- wskazania + informacje różne
        dol = QHBoxLayout()
        lewa = QVBoxLayout()
        lewa.addWidget(_sekcja('Wskazania gospodarcze'))
        self.t_zab = _tabela([k[0] for k in KOLUMNY_ZABIEGI],
                             [k[3] for k in KOLUMNY_ZABIEGI])
        lewa.addWidget(self.t_zab)
        lewa.addStretch(1)
        dol.addLayout(lewa)
        prawa = QVBoxLayout()
        naglowek_info = QHBoxLayout()
        naglowek_info.addWidget(_sekcja('Informacje różne'))
        self.lbl_licznik = QLabel()
        naglowek_info.addStretch(1)
        naglowek_info.addWidget(self.lbl_licznik)
        prawa.addLayout(naglowek_info)
        self.info = QPlainTextEdit()
        self.info.setReadOnly(self.tylko_odczyt)
        self.info.setFixedHeight(100)
        self.info.textChanged.connect(self._zmiana_info)
        prawa.addWidget(self.info)
        prawa.addStretch(1)
        dol.addLayout(prawa, 1)
        self.lay_tresc.addLayout(dol)
        self.lay_tresc.addStretch(1)

        # --- przyciski na dole okna (z dala od zamykania okna)
        self.pasek = QHBoxLayout()
        self.pasek.addStretch(1)
        self.btn_cofnij = QPushButton('Cofnij zmiany')
        self.btn_cofnij.clicked.connect(self._cofnij)
        self.btn_zapisz = QPushButton('Zapisz')
        self.btn_zapisz.clicked.connect(self.zapisz)
        self.pasek.addWidget(self.btn_cofnij)
        self.pasek.addWidget(self.btn_zapisz)
        glowny.addLayout(self.pasek)

        szer_okna = max(
            self.t_opis.width(), SZEROKOSC_GRUPY,
            sum(k[3] for k in KOLUMNY_ZABIEGI) + 260,
        ) + 12 + 20  # marginesy + ewentualny pasek przewijania
        self.setFixedWidth(szer_okna)

    def _pokaz(self, tekst_statusu):
        """Czyści kartę (brak/nieznane wydzielenie)."""
        self.dane = self.oryginal = None
        self.aint = None
        self.t_opis.clearContents()
        self.t_opis.setRowCount(1)
        _dopasuj(self.t_opis)
        self._wyczysc_warstwy()
        self.t_zab.setRowCount(0)
        _dopasuj(self.t_zab)
        self.info.blockSignals(True)
        self.info.setPlainText('')
        self.info.blockSignals(False)
        self.lbl_licznik.setText('')
        self._status(tekst_statusu)
        self._odswiez_przyciski()
        self._dopasuj_okno()

    def _wyczysc_warstwy(self):
        self.grupy = []
        while self.lay_warstw.count():
            w = self.lay_warstw.takeAt(0).widget()
            if w is not None:
                w.deleteLater()

    def _wypelnij(self, dane, warstwy, gatunki, zabiegi):
        self.dane = dane
        self.oryginal = copy.deepcopy(dane)
        self._wypelnij_opis()

        self._wyczysc_warstwy()
        for w in warstwy:
            gat = [g for g in gatunki
                   if _txt(g.get('STOREY_CD')) == _txt(w.get('STOREY_CD'))]
            grupa = _GrupaWarstwy(w, gat)
            grupa.btn.toggled.connect(
                lambda _r: QTimer.singleShot(0, self._dopasuj_okno))
            self.lay_warstw.addWidget(grupa)
            self.grupy.append(grupa)
        if not warstwy:
            self.lay_warstw.addWidget(QLabel('  (brak warstw)'))

        self.t_zab.setRowCount(len(zabiegi))
        for r, z in enumerate(zabiegi):
            for c, (_n, kol, m, _s, szara) in enumerate(KOLUMNY_ZABIEGI):
                self.t_zab.setItem(r, c, _item(_fmt(z.get(kol), m), szara))
        _dopasuj(self.t_zab)

        self.info.blockSignals(True)
        self.info.setPlainText(dane['SUBAREA_INFO'])
        self.info.blockSignals(False)
        self._licznik()
        self._status('')
        self._odswiez_przyciski()
        # rozmiary widgetów są wiarygodne dopiero po wyświetleniu/polerowaniu
        QTimer.singleShot(0, self._uloz_grupy)

    def _wypelnij_opis(self):
        """Opis wydzielenia: cechy i TD w osobnych wierszach (jak w
        Taksatorze), pozostałe pola w pierwszym wierszu. W trybie edycji
        pod ostatnią cechą/TD jest jeden pusty wiersz do dopisania."""
        dl = max(len(self.dane['FOREST_PEC_CD']), len(self.dane['TD']))
        wierszy = max(1, dl + (0 if self.tylko_odczyt else 1))
        self.t_opis.setRowCount(wierszy)
        for c, (_n, pole, typ, slow) in enumerate(KOLUMNY_OPIS):
            s = self.slowniki.get(slow)
            for r in range(wierszy):
                edytowalna = not self.tylko_odczyt
                zmienione = False
                if typ == 'lista':
                    lst, org = self.dane[pole], self.oryginal[pole]
                    tekst = lst[r] if r < len(lst) else ''
                    # dopisywać można tylko bezpośrednio pod ostatnim kodem
                    edytowalna = edytowalna and r <= len(lst)
                    zmienione = tekst != (org[r] if r < len(org) else '')
                    tip = s.opis(tekst) if s and tekst else ''
                elif r > 0:
                    tekst, tip, edytowalna = '', '', False
                elif typ == 'liczba':
                    v = self.dane[pole]
                    tekst = _fmt(v, 2) if not _pusty(v) else ''
                    tip = ''
                    zmienione = v != self.oryginal[pole]
                else:
                    tekst = self.dane[pole]
                    tip = s.opis(tekst) if s and tekst else ''
                    zmienione = tekst != self.oryginal[pole]
                it = QTableWidgetItem(tekst)
                if tip:
                    it.setToolTip(tip)
                if not edytowalna:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if zmienione:
                    it.setBackground(QBrush(ZMIENIONE))
                self.t_opis.setItem(r, c, it)
        _dopasuj(self.t_opis)

    def _uloz_grupy(self):
        """DRZEW zawsze rozwinięte, pozostałe - dopóki okno mieści się na
        ekranie (bez przewijania)."""
        if sip.isdeleted(self):
            return
        ekran = QApplication.desktop().availableGeometry(self)
        limit = int(ekran.height() * 0.9)
        for g in self.grupy:
            g.ustaw(g.kod == 'DRZEW')
        for g in self.grupy:
            if g.kod == 'DRZEW':
                continue
            g.ustaw(True)
            if self._wysokosc_tresci() > limit:
                g.ustaw(False)
        self._dopasuj_okno()

    def _wysokosc_tresci(self):
        """Wysokość całego okna potrzebna, by pokazać treść bez
        przewijania."""
        self.tresc.setMinimumHeight(0)
        self.lay_tresc.activate()
        m = self.layout().contentsMargins()
        return (self.tresc.sizeHint().height()
                + self.lbl_adr.sizeHint().height()
                + self.btn_zapisz.sizeHint().height()
                + m.top() + m.bottom() + 2 * self.layout().spacing() + 4)

    def _dopasuj_okno(self):
        """Okno dopasowane do treści (maks. 90% ekranu - dopiero wtedy
        przewijanie), tylko rośnie. Minimalna wysokość treści zapobiega jej
        zgniataniu przez obszar przewijania."""
        if sip.isdeleted(self):
            return
        ekran = QApplication.desktop().availableGeometry(self)
        # okno tylko rośnie (największa wysokość z tego połączenia), żeby
        # nie skakało przy przełączaniu wydzieleń; powyżej 90% - przewijanie
        h = min(max(self._wysokosc_tresci(), self.panel.max_h),
                int(ekran.height() * 0.9))
        self.panel.max_h = h
        self.tresc.setMinimumHeight(self.tresc.sizeHint().height())
        self.resize(self.width(), h)

    # ------------------------------------------------------------ edycja

    def ustaw_pole(self, pole, tekst, wiersz=0):
        if sip.isdeleted(self) or self.dane is None or self.tylko_odczyt:
            return
        _n, _p, typ, slow = next(k for k in KOLUMNY_OPIS if k[1] == pole)
        tekst = (tekst or '').strip()
        s = self.slowniki.get(slow)
        if typ == 'liczba':
            if not tekst:
                nowa = None
            else:
                try:
                    nowa = float(tekst.replace(',', '.'))
                except ValueError:
                    return self._blad(f'"{tekst}" to nie liczba')
                if nowa < 0:
                    return self._blad('Wartość nie może być ujemna')
            self.dane[pole] = nowa
        elif typ == 'lista':
            lst = list(self.dane[pole])
            if not tekst:
                if wiersz < len(lst):
                    del lst[wiersz]  # pusta komórka = usunięcie kodu
            else:
                kod = s.rozwiaz(tekst) if s else None
                if kod is None:
                    return self._blad(f'Nieznany kod/numer: "{tekst}"')
                inne = [k for i, k in enumerate(lst) if i != wiersz]
                if kod in inne:
                    return self._blad(f'Kod {kod} już jest na liście')
                if wiersz < len(lst):
                    lst[wiersz] = kod
                else:
                    lst.append(kod)
            self.dane[pole] = lst
        else:
            if not tekst:
                nowa = ''
            else:
                nowa = s.rozwiaz(tekst) if s else None
                if nowa is None:
                    return self._blad(f'Nieznany kod/numer: "{tekst}"')
            self.dane[pole] = nowa
        self._wypelnij_opis()
        self._status('')
        self._odswiez_przyciski()
        QTimer.singleShot(0, self._dopasuj_okno)

    def _zmiana_info(self):
        if self.dane is None:
            return
        tekst = self.info.toPlainText()
        if len(tekst) > MAX_INFO:
            kursor = self.info.textCursor()
            self.info.blockSignals(True)
            self.info.setPlainText(tekst[:MAX_INFO])
            self.info.blockSignals(False)
            kursor.setPosition(MAX_INFO)
            self.info.setTextCursor(kursor)
            tekst = tekst[:MAX_INFO]
            self._blad(f'Informacje różne: maksymalnie {MAX_INFO} znaków')
        self.dane['SUBAREA_INFO'] = tekst.strip()
        self._licznik()
        self._odswiez_przyciski()

    def _licznik(self):
        n = len(self.info.toPlainText())
        self.lbl_licznik.setText(f'{n}/{MAX_INFO}')

    def _zmienione(self):
        return self.dane is not None and self.dane != self.oryginal

    def _odswiez_przyciski(self):
        zm = self._zmienione() and not self.tylko_odczyt
        self.btn_zapisz.setEnabled(zm)
        self.btn_cofnij.setEnabled(zm)
        self.btn_zapisz.setVisible(not self.tylko_odczyt)
        self.btn_cofnij.setVisible(not self.tylko_odczyt)
        if zm:
            self.lbl_status.setText('  zmiany niezapisane')
            self.lbl_status.setStyleSheet('color: #b36b00;')

    def _status(self, tekst, kolor='#555'):
        self.lbl_status.setText('  ' + tekst if tekst else '')
        self.lbl_status.setStyleSheet(f'color: {kolor};')

    def _blad(self, tekst):
        self._status(tekst, '#c00000')
        QApplication.beep()
        return False

    def _cofnij(self):
        if self.oryginal is None:
            return
        self.dane = copy.deepcopy(self.oryginal)
        self._wypelnij_opis()
        self.info.blockSignals(True)
        self.info.setPlainText(self.dane['SUBAREA_INFO'])
        self.info.blockSignals(False)
        self._licznik()
        self._status('cofnięto zmiany')
        self._odswiez_przyciski()
        QTimer.singleShot(0, self._dopasuj_okno)

    # ------------------------------------------------------------- zapis

    def zapisz(self):
        if not self._zmienione() or self.tylko_odczyt:
            return True
        # plik .ldb tworzy też nasze własne połączenie, więc "cudza" blokada
        # jest sprawdzana tylko na starcie (uruchom)
        if not os.path.isfile(self.baza_sc):
            return self._blad('Plik bazy zniknął - nie zapisano')

        if not self.panel.kopia_zrobiona:
            self.baza.utworz_kopie('edycja_opisu_taks')
            self.panel.kopia_zrobiona = True

        d, o, aint = self.dane, self.oryginal, self.aint
        cur = self.baza.cur
        try:
            zmiany = [p for p in POLA_SUBAREA if d[p] != o[p]]
            if zmiany:
                wart = [None if d[p] in ('', None) else d[p] for p in zmiany]
                cur.execute(
                    'update F_SUBAREA set '
                    + ', '.join(f'{p} = ?' for p in zmiany)
                    + ' where ARODES_INT_NUM = ?', (*wart, aint))
            if d['FOREST_PEC_CD'] != o['FOREST_PEC_CD']:
                cur.execute('delete from F_AROD_STAND_PEC where '
                            'ARODES_INT_NUM = ?', (aint,))
                for i, kod in enumerate(d['FOREST_PEC_CD'], 1):
                    cur.execute(
                        'insert into F_AROD_STAND_PEC (FOREST_PEC_CD, '
                        'ARODES_INT_NUM, PEC_RANK_ORDER) values (?, ?, ?)',
                        (kod, aint, i))
            if d['TD'] != o['TD']:
                cur.execute("delete from F_AROD_GOAL where ARODES_INT_NUM = ? "
                            "and GOAL_TYPE_FL = 'D'", (aint,))
                for i, kod in enumerate(d['TD'], 1):
                    cur.execute(
                        'insert into F_AROD_GOAL (GOAL_TYPE_FL, ARODES_INT_NUM, '
                        'SPECIES_CD, GOAL_RANK_ORDER) values (?, ?, ?, ?)',
                        ('D', aint, kod, i))
            self.baza.con.commit()
        except Exception as e:
            try:
                self.baza.con.rollback()
            except Exception:
                pass
            QMessageBox.critical(
                self, 'Błąd zapisu',
                f'Zapis nie powiódł się, nic nie zostało zmienione:\n{e}')
            return False

        wynik = self._wczytaj(aint)
        if wynik:
            self._wypelnij(*wynik)
        self._status('zapisano', '#107010')
        self.iface.messageBar().pushSuccess(
            'Opis taksacyjny', f'Zapisano zmiany: {self.adr}')
        return True

    def _zapytaj_o_zmiany(self):
        """True - można przejść dalej (zapisane albo porzucone)."""
        if not self._zmienione() or self.tylko_odczyt:
            return True
        odp = QMessageBox.question(
            self, 'Niezapisane zmiany',
            f'Wydzielenie {self.adr} ma niezapisane zmiany. Zapisać?',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save)
        if odp == QMessageBox.Save:
            return self.zapisz()
        return odp == QMessageBox.Discard

    # ------------------------------------------------------ zaznaczenie

    def zmiana_zaznaczenia(self, *_args):
        """Wołane przez panel przy zmianie zaznaczenia na warstwie."""
        if sip.isdeleted(self.lyr):
            return
        ids = self.lyr.selectedFeatureIds()
        if len(ids) != 1:
            if self.dane is None:
                self._pokaz('zaznacz jedno wydzielenie na warstwie '
                            f'{self.lyr.name()}' if not ids else
                            f'zaznaczono {len(ids)} - zaznacz jedno')
            return
        f = self.lyr.getFeature(ids[0])
        adr = _txt(f['ADR_LES'])
        if adr == self.adr and self.dane is not None:
            return
        if not self._zapytaj_o_zmiany():
            self._status(f'zostaję przy {self.adr} (niezapisane zmiany)',
                         '#b36b00')
            return
        self.adr = adr
        self.lbl_adr.setText(
            f'{adr}      {rozbij_adres(adr)}' if adr else '(puste ADR_LES)')
        self._ustaw_tytul()
        if adr not in self.wydz:
            self._pokaz('brak opisu tego wydzielenia w bazie')
            return
        self.aint = self.wydz[adr]
        wynik = self._wczytaj(self.aint)
        if wynik is None:
            self._pokaz('brak rekordu F_SUBAREA dla tego wydzielenia')
            return
        self._wypelnij(*wynik)

    # -------------------------------------------------------- zamknięcie

    def porzuc_zmiany(self):
        if self.oryginal is not None:
            self.dane = copy.deepcopy(self.oryginal)

    def closeEvent(self, event):
        """Zamknięcie karty nie rozłącza bazy (połączenie trzyma panel)."""
        if not self._zapytaj_o_zmiany():
            event.ignore()
            return
        event.accept()


# ------------------------------------------------------------------- panel

class PanelOpisu(QDockWidget):
    """Zakotwiczony panel: warstwa wydzieleń + połączenie z bazą + status.
    Panel otwarty = baza podłączona (zamknięcie panelu rozłącza). Poniżej
    statusu wolne miejsce na kolejne funkcje."""

    TYTUL = 'Opis taksacyjny - baza'

    def __init__(self, iface):
        super().__init__(self.TYTUL, iface.mainWindow())
        self.setObjectName('LasR_PanelOpisuTaks')
        self.iface = iface
        self.lyr = None
        self.baza = None
        self.baza_sc = ''
        self.tylko_odczyt = False
        self.slowniki = {}
        self.wydz = {}
        self.karta = None
        self.max_h = 0
        self.kopia_zrobiona = False
        self._szczegoly = ''
        self._warstwy = []
        self._zbuduj()
        self._odswiez()
        QgsProject.instance().layerWillBeRemoved.connect(self._usuwana_warstwa)

    # ----------------------------------------------------------------- UI

    def _zbuduj(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        lay.addWidget(QLabel('Warstwa wydzieleń:'))
        wiersz = QHBoxLayout()
        self.combo = QComboBox()
        # wąski panel - lista nie może wymuszać szerokości nazwą warstwy
        self.combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setMinimumContentsLength(6)
        wiersz.addWidget(self.combo, 1)
        self.btn_warstwy = QToolButton()
        self.btn_warstwy.setText('⟳')
        self.btn_warstwy.setToolTip('Odśwież listę warstw')
        self.btn_warstwy.clicked.connect(self._wczytaj_warstwy)
        wiersz.addWidget(self.btn_warstwy)
        lay.addLayout(wiersz)

        wiersz = QHBoxLayout()
        self.btn_polacz = QPushButton('Połącz...')
        self.btn_polacz.setToolTip('Połącz bazę Taksatora (.mdb)')
        self.btn_polacz.clicked.connect(self.polacz)
        self.btn_rozlacz = QPushButton('Rozłącz')
        self.btn_rozlacz.clicked.connect(lambda: self.rozlacz())
        wiersz.addWidget(self.btn_polacz)
        wiersz.addWidget(self.btn_rozlacz)
        lay.addLayout(wiersz)

        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setTextFormat(Qt.RichText)
        lay.addWidget(self.lbl_status)

        wiersz = QHBoxLayout()
        self.btn_szczegoly = QPushButton('Zgodność')
        self.btn_szczegoly.setToolTip('Szczegóły zgodności warstwy z bazą')
        self.btn_szczegoly.clicked.connect(self._pokaz_szczegoly)
        self.btn_karta = QPushButton('Karta')
        self.btn_karta.setToolTip('Pokaż kartę opisu zaznaczonego wydzielenia')
        self.btn_karta.clicked.connect(self.pokaz_karte)
        wiersz.addWidget(self.btn_szczegoly)
        wiersz.addWidget(self.btn_karta)
        lay.addLayout(wiersz)

        # miejsce na kolejne funkcje panelu
        self.lay_dodatki = QVBoxLayout()
        lay.addLayout(self.lay_dodatki)
        lay.addStretch(1)
        w.setMinimumWidth(10)
        self.setWidget(w)
        self._wczytaj_warstwy()

    def _wczytaj_warstwy(self):
        if self.polaczona():
            return
        self._warstwy = _warstwy_poligonowe()
        self.combo.clear()
        for lyr in self._warstwy:
            self.combo.addItem(lyr.name())
            sc = lyr.dataProvider().dataSourceUri().split('|')[0]
            self.combo.setItemData(self.combo.count() - 1, sc, Qt.ToolTipRole)
        i = next((i for i, lyr in enumerate(self._warstwy)
                  if lyr.name().upper() == 'WYDZ'), 0)
        if self._warstwy:
            self.combo.setCurrentIndex(i)

    def showEvent(self, event):
        super().showEvent(event)
        self._wczytaj_warstwy()

    def polaczona(self):
        return self.baza is not None

    def _odswiez(self):
        pol = self.polaczona()
        self.combo.setEnabled(not pol)
        self.btn_warstwy.setEnabled(not pol)
        self.btn_polacz.setEnabled(not pol)
        self.btn_rozlacz.setEnabled(pol)
        self.btn_karta.setEnabled(pol)
        self.btn_szczegoly.setEnabled(pol and bool(self._szczegoly))
        if not pol:
            self.lbl_status.setText('<i>Baza niepodłączona</i>')
            self.lbl_status.setToolTip('')
            return
        tryb = ('<span style="color:#c00000"><b>PODGLĄD</b> (.ldb)</span>'
                if self.tylko_odczyt else
                '<span style="color:#107010"><b>EDYCJA</b></span>')
        zg = ('<span style="color:#107010">zgodna z warstwą</span>'
              if not self._szczegoly else
              '<span style="color:#b36b00">niezgodności z warstwą</span>')
        self.lbl_status.setText(
            f'<b>{os.path.basename(self.baza_sc)}</b><br>'
            f'{self.lyr.name()} | {tryb}<br>'
            f'wydzieleń: {len(self.wydz)}<br>{zg}')
        self.lbl_status.setToolTip(self.baza_sc)

    # ------------------------------------------------------- połączenie

    def polacz(self):
        i = self.combo.currentIndex()
        if not (0 <= i < len(self._warstwy)) or sip.isdeleted(self._warstwy[i]):
            QMessageBox.warning(self, 'Brak warstwy',
                                'Wybierz warstwę wydzieleń.')
            return
        lyr = self._warstwy[i]
        if 'ADR_LES' not in [f.name() for f in lyr.fields()]:
            QMessageBox.warning(self, 'Brak pola',
                                f'Warstwa "{lyr.name()}" nie ma pola ADR_LES.')
            return

        start = ''
        sc = lyr.dataProvider().dataSourceUri().split('|')[0]
        if os.path.isfile(sc):
            start = os.path.dirname(os.path.dirname(sc))
        baza_sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę Taksatora', start, 'Access MDB (*.mdb)')
        if not baza_sc:
            return
        baza_sc = os.path.normpath(baza_sc)

        # blokada sprawdzana PRZED własnym połączeniem (które też tworzy .ldb)
        blokada = _plik_blokady(baza_sc)
        if blokada:
            QMessageBox.warning(
                self, 'Baza zablokowana',
                f'Obok bazy jest plik blokady:\n{blokada}\n\nBaza jest '
                'prawdopodobnie otwarta w innym programie (np. Taksatorze). '
                'Karta będzie TYLKO DO PODGLĄDU.\n\nJeśli żaden program '
                'nie używa bazy, plik mógł zostać po awarii - usuń go '
                'ręcznie.')

        baza = Baza(baza_sc, pomin_blokade=True)
        try:
            baza.polacz()
            slowniki = wczytaj_slowniki(baza)
            wydz = baza.pobierz_wydzielenia() or {}
        except Exception as e:
            baza.zamknij()
            QMessageBox.critical(self, 'Błąd bazy',
                                 f'Nie udało się połączyć z bazą:\n{e}')
            return

        ok, podsum, szczegoly = sprawdz_zgodnosc(lyr, wydz)
        if not ok:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle('Zgodność warstwy z bazą')
            box.setText(podsum + '\n\nMożna pracować dalej - wydzielenia '
                        'bez opisu w bazie pokażą pustą kartę.')
            box.setDetailedText(szczegoly)
            box.addButton('Kontynuuj', QMessageBox.AcceptRole)
            anuluj = box.addButton('Anuluj', QMessageBox.RejectRole)
            box.exec_()
            if box.clickedButton() is anuluj:
                baza.zamknij()
                return

        self.lyr = lyr
        self.baza = baza
        self.baza_sc = baza_sc
        # od tej chwili inne skrypty wtyczki nie połączą się z tą bazą
        zajmij_baze(baza_sc)
        self.tylko_odczyt = bool(blokada)
        self.slowniki = slowniki
        self.wydz = wydz
        self._szczegoly = '' if ok else podsum + '\n\n' + szczegoly
        self.max_h = 0
        self.kopia_zrobiona = False
        self.lyr.selectionChanged.connect(self._zaznaczenie)
        self._odswiez()
        self.iface.messageBar().pushSuccess(
            'Opis taksacyjny', f'Podłączono bazę {os.path.basename(baza_sc)}')
        self._zaznaczenie()

    def _karta_otwarta(self):
        return (self.karta is not None and not sip.isdeleted(self.karta)
                and self.karta.isVisible())

    def rozlacz(self, wymus=False):
        """False, gdy użytkownik anulował zamknięcie karty z niezapisanymi
        zmianami. wymus=True porzuca zmiany (np. usunięta warstwa)."""
        if self._karta_otwarta():
            if wymus:
                self.karta.porzuc_zmiany()
            if not self.karta.close():
                return False
        self.karta = None
        if self.lyr is not None and not sip.isdeleted(self.lyr):
            try:
                self.lyr.selectionChanged.disconnect(self._zaznaczenie)
            except (TypeError, RuntimeError):
                pass
        if self.baza is not None:
            self.baza.zamknij()
        if self.baza_sc:
            zwolnij_baze(self.baza_sc)
        self.lyr = None
        self.baza = None
        self.baza_sc = ''
        self.tylko_odczyt = False
        self.slowniki = {}
        self.wydz = {}
        self._szczegoly = ''
        self._odswiez()
        self._wczytaj_warstwy()
        return True

    def _usuwana_warstwa(self, layer_id):
        if self.lyr is not None and not sip.isdeleted(self.lyr) \
                and self.lyr.id() == layer_id:
            self.rozlacz(wymus=True)
            self.iface.messageBar().pushWarning(
                'Opis taksacyjny', 'Warstwa wydzieleń została usunięta - '
                'baza rozłączona (niezapisane zmiany porzucone).')

    # ------------------------------------------------------------ karta

    def _zaznaczenie(self, *_args):
        if not self.polaczona():
            return
        if self._karta_otwarta():
            self.karta.zmiana_zaznaczenia()
        elif len(self.lyr.selectedFeatureIds()) == 1:
            self.pokaz_karte()

    def pokaz_karte(self):
        if not self.polaczona():
            return
        if self._karta_otwarta():
            self.karta.raise_()
            self.karta.activateWindow()
            return
        self.karta = OknoOpisu(self)
        self.karta.show()

    def _pokaz_szczegoly(self):
        box = QMessageBox(self)
        box.setWindowTitle('Zgodność warstwy z bazą')
        box.setText(self._szczegoly.split('\n\n')[0])
        box.setDetailedText(self._szczegoly)
        box.exec_()

    # ------------------------------------------------------- zamknięcie

    def closeEvent(self, event):
        """Zamknięcie panelu = rozłączenie bazy (i zamknięcie karty)."""
        if self.polaczona() and not self.rozlacz():
            event.ignore()
            return
        event.accept()

    def zadokuj(self):
        """Lewa strona, pod panelem Warstw (Layers) - ta sama szerokość co
        Warstwy. Bez panelu Warstw - zwykle po lewej."""
        okno = self.iface.mainWindow()
        okno.addDockWidget(Qt.LeftDockWidgetArea, self)
        warstwy = okno.findChild(QDockWidget, 'Layers')
        if warstwy is not None and warstwy.isVisible()                 and not warstwy.isFloating():
            okno.splitDockWidget(warstwy, self, Qt.Vertical)

    def sprzataj(self):
        """Przy wyładowaniu wtyczki."""
        self.rozlacz(wymus=True)
        try:
            QgsProject.instance().layerWillBeRemoved.disconnect(
                self._usuwana_warstwa)
        except (TypeError, RuntimeError):
            pass
