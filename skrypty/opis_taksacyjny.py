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
  "Informacje różne" (SUBAREA_INFO); warstwy i gatunki (krok 3a: reguły,
  sortowanie i plan zapisu w opis_warstwy.py); zabiegi tylko podgląd,
- pola kodów: rozwijana lista albo wpisanie kodu lub numeru jak w
  Taksatorze (SO albo 1, D-STAN albo 92) - numery ze słowników TEJ bazy
  (kolumny *_NR, dla gatunków BUL_SPECIES_NR; numery rodzaju powierzchni
  różnią się między bazami),
- nic nie jest przeliczane (zasobność, przyrost - robi to Taksator PU),
- zapis pojedynczego wydzielenia w jednej transakcji; pakiet kopii (baza +
  pliki warstwy wydzieleń, Kopie_manipulacyjne/edycja_opisu_<czas>/) raz
  na połączenie i na żądanie ("Zapisz kopię bazy"), trzymane 5 ostatnich,
- dziennik zmian <baza>_dziennik_edycji.csv (pole przed/po, a przy
  usunięciu wydzielenia pełna zawartość jego rekordów jako JSON),
- usuwanie wydzielenia z bazy (Baza.usun_rekordy; TD, cechy, PNSW,
  rozliczenie znikają kaskadowo) - geometria warstw bez zmian, poligon
  oznaczany na warstwie pamięci "Opis - usunięte z bazy",
- okno karty tylko rośnie (maks. 90% ekranu, powyżej - przewijanie).
"""
import copy
import csv
import json
import os
import shutil
from collections import Counter
from datetime import datetime

from PyQt5 import sip
from PyQt5.QtCore import QEvent, QPoint, Qt, QTimer
from PyQt5.QtGui import (
    QBrush, QColor, QCursor, QDoubleValidator, QFont, QFontDatabase,
    QIntValidator,
)
from PyQt5.QtWidgets import (
    QAbstractItemDelegate, QAbstractItemView, QApplication, QComboBox,
    QCompleter, QDialog,
    QDialogButtonBox, QDockWidget, QMenu, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QStyledItemDelegate, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget,
)
from qgis.core import (
    QgsCoordinateTransform, QgsExpression, QgsFeature, QgsFeatureRequest,
    QgsField, QgsFillSymbol, QgsGeometry, QgsProject, QgsRectangle,
    QgsVectorLayer, QgsWkbTypes,
)
from PyQt5.QtCore import QVariant

from . import kopie_manipulacyjne
from . import opis_warstwy as ow
from .baza_wrapper import Baza, zajmij_baze, zwolnij_baze

SZARY = QColor(225, 225, 225)
ZMIENIONE = QColor(214, 234, 255)   # zmienione, niezapisane
BLEDNE = QColor(255, 196, 196)      # reguła twarda - blokuje zapis
OSTRZEGAWCZE = QColor(255, 240, 170)  # ostrzeżenie - zapis możliwy
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
    'PART_CD': ('F_PART_DIC', 'PART_CD', 'PART_NAME', 'PART_NR'),
    'SITE_CLASS_CD': ('F_SITE_CLASS_DIC', 'SITE_CLASS_CD', 'SITE_CLASS_NAME',
                      'SITE_CLASS_NR'),
    'MIXTURE_CD': ('F_MIXTURE_DIC', 'MIXTURE_CD', 'MIXTURE_NAME',
                   'MIXTURE_NR'),
    'DENSITY_CD': ('F_DENSITY_DIC', 'DENSITY_CD', 'DENSITY_NAME',
                   'DENSITY_NR'),
    'STOREY_CD': ('F_STOREY_DIC', 'STOREY_CD', 'STOREY_NAME', 'STOREY_NR'),
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

# warstwa i gatunki: (nagłówek, pole, typ edytora, słownik, miejsca po
# przecinku przy wyświetlaniu, szerokość); typ: 'kod', 'calk', 'liczba'.
# Zagęszczenie, lokalizacja, jakość techniczna i hodowlana pominięte - w
# danych Taksatora nieużywane (0%, krok 2).
KOLUMNY_WARSTWY = [
    ('Zmiesz.', 'MIXTURE_CD', 'kod', 'MIXTURE_CD', None, 62),
    ('Zwarcie', 'DENSITY_CD', 'kod', 'DENSITY_CD', None, 62),
    ('Zd.', 'STANDDENSITY_INDEX', 'liczba', None, 2, 46),
]
KOLUMNY_GATUNKI = [
    ('Kod', 'SPECIES_CD', 'kod', 'SPECIES_CD', None, 72),
    ('Udział', 'PART_CD', 'kod', 'PART_CD', None, 58),
    ('Wiek', 'SPECIES_AGE', 'calk', None, 0, 42),
    ('D 13', 'BHD', 'calk', None, 0, 42),
    ('Wys.', 'HEIGHT', 'calk', None, 0, 42),
    ('Bonit.', 'SITE_CLASS_CD', 'kod', 'SITE_CLASS_CD', None, 54),
    ('Zasob.', 'VOLUME', 'liczba', None, 0, 55),
]
KOLUMNY_ZABIEGI = [
    ('Grupa\nczynności', 'MEASURE_CD', None, 80, False),
    ('Pilność\nzabiegu', 'URGENCY', 'bool', 55, False),
    ('% pow.\nwydz.', 'PROC_AREA', 0, 50, False),
    ('Pow.', 'CUTTING_AREA', 4, 60, False),
    ('% grub.', 'LARGE_TIMBER_PERC', 0, 50, False),
    ('m3 grub.', 'LARGE_TIMBER_VALUE', 0, 60, True),
]


NAZWA_KOPII = 'edycja_opisu'
ILE_KOPII = 5  # tyle ostatnich pakietów kopii Edytora zostaje na dysku
NAZWA_BEZ_OPISU = 'WYDZ bez opisu w bazie'
# tabele z rekordami wydzielenia (V_TABLE_FIELD_KEY_RELATION) - do migawki
# w dzienniku przed usunięciem
TABELE_WYDZIELENIA = [
    'F_ARODES', 'F_SUBAREA', 'F_AROD_STOREY', 'F_STOREY_SPECIES',
    'F_AROD_CUE', 'F_AROD_GOAL', 'F_AROD_STAND_PEC', 'F_AROD_SPEC_AREA',
    'F_SPECIES_SPAREA', 'F_AROD_LAND_USE', 'F_AROD_CATEGORY',
    'F_AROD_DAMAGE', 'F_AROD_PHENOMENA', 'F_AROD_SOIL_SPEC', 'F_SET',
    'F_ERROR_HEAD',
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
        # URGENCY w bazie: 'T' = pilny, 'N' = zwykły
        return '☑' if str(v).strip().upper() in ('T', '1', 'TRUE') else '☐'
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


def sciezka_dziennika(baza_sc):
    return os.path.splitext(baza_sc)[0] + '_dziennik_edycji.csv'


def _dziennik_txt(v):
    if isinstance(v, list):
        return ', '.join(v)
    return '' if v is None else str(v)


def dopisz_do_dziennika(baza_sc, wiersze):
    """wiersze: (adr_les, operacja, pole, przed, po). CSV ';' z BOM (Excel)
    obok bazy. Zwraca False przy błędzie zapisu (zapis do bazy już się
    odbył - to tylko ostrzeżenie)."""
    sc = sciezka_dziennika(baza_sc)
    nowy = not os.path.isfile(sc)
    czas = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uzytkownik = os.environ.get('USERNAME', '')
    try:
        with open(sc, 'a', newline='',
                  encoding='utf-8-sig' if nowy else 'utf-8') as f:
            w = csv.writer(f, delimiter=';')
            if nowy:
                w.writerow(['czas', 'uzytkownik', 'adr_les', 'operacja',
                            'pole', 'przed', 'po'])
            for adr, operacja, pole, przed, po in wiersze:
                w.writerow([czas, uzytkownik, adr, operacja, pole,
                            _dziennik_txt(przed), _dziennik_txt(po)])
        return True
    except OSError:
        return False


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


def _int(v):
    return None if _pusty(v) else int(round(float(v)))


def _float(v, miejsca=None):
    if _pusty(v):
        return None
    f = float(v)
    return round(f, miejsca) if miejsca is not None else f


def _model_warstw(warstwy, gatunki):
    """Model warstw dla opis_warstwy (kody jako tekst, liczby int/float)."""
    wyn = []
    for w in warstwy:
        k = _txt(w.get('STOREY_CD'))
        gat = [{
            'SPEC_STOR_INT_NUM': g['SPEC_STOR_INT_NUM'],
            'SPECIES_CD': _txt(g.get('SPECIES_CD')),
            'PART_CD': _txt(g.get('PART_CD')),
            'SPECIES_AGE': _int(g.get('SPECIES_AGE')),
            'BHD': _int(g.get('BHD')),
            'HEIGHT': _int(g.get('HEIGHT')),
            'SITE_CLASS_CD': _txt(g.get('SITE_CLASS_CD')),
            'VOLUME': _float(g.get('VOLUME')),
        } for g in gatunki if _txt(g.get('STOREY_CD')) == k]
        wyn.append({
            'STOREY_CD': k,
            'MIXTURE_CD': _txt(w.get('MIXTURE_CD')),
            'DENSITY_CD': _txt(w.get('DENSITY_CD')),
            # REAL w Accessie (0.100000001) - zaokrąglenie do 2 miejsc
            'STANDDENSITY_INDEX': _float(w.get('STANDDENSITY_INDEX'), 2),
            'gatunki': gat,
        })
    return wyn


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


def okno_zgodnosci(parent, podsum, szczegoly, z_wyborem):
    """Raport zgodności warstwa-baza: podsumowanie + przewijana lista
    szczegółów (ok. 25 wierszy, okno rozciągalne). z_wyborem=True ->
    przyciski Kontynuuj/Anuluj, zwraca True dla Kontynuuj."""
    dlg = QDialog(parent)
    dlg.setWindowTitle('Zgodność warstwy z bazą')
    lay = QVBoxLayout(dlg)
    lbl = QLabel(podsum + ('\n\nMożna pracować dalej - wydzielenia bez '
                           'opisu w bazie pokażą pustą kartę.'
                           if z_wyborem else ''))
    lbl.setWordWrap(True)
    lay.addWidget(lbl)
    pole = QPlainTextEdit(szczegoly)
    pole.setReadOnly(True)
    pole.setLineWrapMode(QPlainTextEdit.NoWrap)
    # stała szerokość znaków - adresy leśne układają się w kolumny
    pole.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
    fm = pole.fontMetrics()
    # szerokość wg najdłuższej linii (nagłówki sekcji, adresy), max 900 px
    najdl = max([fm.width(x) for x in szczegoly.split('\n')[:1000]] + [0])
    pole.setMinimumSize(min(max(najdl + 50, fm.width('W' * 30) + 40), 900),
                        fm.lineSpacing() * 25 + 12)
    lay.addWidget(pole, 1)
    if z_wyborem:
        przyciski = QDialogButtonBox()
        przyciski.addButton('Kontynuuj', QDialogButtonBox.AcceptRole)
        przyciski.addButton('Anuluj', QDialogButtonBox.RejectRole)
    else:
        przyciski = QDialogButtonBox(QDialogButtonBox.Close)
    przyciski.accepted.connect(dlg.accept)
    przyciski.rejected.connect(dlg.reject)
    lay.addWidget(przyciski)
    return dlg.exec_() == QDialog.Accepted


# ------------------------------------------------------------ delegat edycji

class _DelegatTabeli(QStyledItemDelegate):
    """Edytor komórki: 'kod' - rozwijana lista "KOD | nr" z możliwością
    wpisania kodu albo numeru (podpowiedzi); 'calk'/'liczba' - zwykła
    linia (kontrola wartości przy zatwierdzeniu). Zmiana trafia do
    callback(wiersz, kolumna, tekst) - odroczona, bo może przebudować
    tabelę (liczba wierszy)."""

    def __init__(self, okno, specyfikacja, callback, po_enter=None,
                 podpowiedz=None):
        super().__init__(okno)
        self.okno = okno
        self.spec = specyfikacja  # [(typ, słownik), ...] per kolumna
        self.callback = callback
        # podpowiedz(wiersz, kolumna) -> tekst wstawiany do PUSTEJ komórki,
        # zatwierdzany wyłącznie Enterem (np. bonitacja z tablic)
        self.podpowiedz = podpowiedz
        # po_enter(wiersz, kolumna, w_edycji) - nawigacja Enterem; None =
        # domyślne zachowanie Qt
        self.po_enter = po_enter

    def eventFilter(self, editor, event):
        """Enter w edytorze: zatwierdź i przejdź dalej (po_enter); Esc -
        domyślnie: porzuć edycję komórki."""
        if self.po_enter is not None and event.type() == QEvent.KeyPress \
                and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if isinstance(editor, QComboBox) and editor.view().isVisible():
                return super().eventFilter(editor, event)
            wiersz = editor.property('wiersz')
            kolumna = editor.property('kolumna')
            editor.setProperty('enter', True)
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)
            # po odroczonym callback (ustaw_*) - kolejność kolejki zdarzeń
            QTimer.singleShot(0, lambda: self.po_enter(wiersz, kolumna, True))
            return True
        return super().eventFilter(editor, event)

    def createEditor(self, parent, option, index):
        typ, slow = self.spec[index.column()]
        if typ == 'usun':
            return None
        ed = self._edytor(parent, typ, slow)
        ed.setProperty('wiersz', index.row())
        ed.setProperty('kolumna', index.column())
        return ed

    def _edytor(self, parent, typ, slow):
        if typ != 'kod':
            return QLineEdit(parent)
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
        if not tekst and self.podpowiedz is not None:
            sugestia = self.podpowiedz(index.row(), index.column())
            if sugestia:
                tekst = sugestia
                editor.setProperty('podpowiedz', sugestia)
        if isinstance(editor, QComboBox):
            editor.setEditText(tekst)
            editor.lineEdit().selectAll()
        else:
            editor.setText(tekst)
            editor.selectAll()

    def setModelData(self, editor, model, index):
        tekst = editor.currentText() if isinstance(editor, QComboBox) \
            else editor.text()
        if tekst == (index.data() or ''):
            return  # bez zmian - nie przebudowuj tabeli
        if tekst == editor.property('podpowiedz') and \
                not editor.property('enter'):
            return  # podpowiedź przyjmowana tylko Enterem
        wiersz, kolumna = index.row(), index.column()
        QTimer.singleShot(0, lambda: self.callback(wiersz, kolumna, tekst))


def idz_do_komorki(tabela, r, c):
    """Przejście do komórki z otwarciem edytora (CurrentChanged). Enter,
    który zatwierdził podpowiedź listy, potrafi zamknąć świeżo otwarty
    edytor - dlatego po chwili sprawdzenie i ewentualnie ponowne otwarcie."""
    if sip.isdeleted(tabela):
        return
    tabela.setFocus()
    tabela.setCurrentCell(r, c)
    QTimer.singleShot(60, lambda: _otworz_edytor(tabela, r, c))


def _otworz_edytor(tabela, r, c):
    if sip.isdeleted(tabela) or \
            tabela.state() == QAbstractItemView.EditingState:
        return
    if (tabela.currentRow(), tabela.currentColumn()) != (r, c):
        return
    it = tabela.item(r, c)
    if it is not None and it.flags() & Qt.ItemIsEditable:
        tabela.setFocus()
        tabela.edit(tabela.model().index(r, c))


class _NowaWarstwaDialog(QDialog):
    """Szybkie dodanie warstwy z klawiatury: kod albo numer (NAL albo 6),
    Enter - dodaj, Esc - bez dodawania."""

    def __init__(self, okno, wolne):
        super().__init__(okno)
        self.setWindowTitle('Nowa warstwa')
        self.okno = okno
        self.wolne = wolne
        self.kod = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('Kod albo numer nowej warstwy\n'
                             '(Enter - dodaj, Esc - bez dodawania):'))
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        s = okno.slowniki.get('STOREY_CD')
        self.combo.addItems([s.pozycja(k) if s else k for k in wolne])
        comp = QCompleter(self.combo.model(), self.combo)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchStartsWith)
        self.combo.setCompleter(comp)
        self.combo.setCurrentIndex(-1)
        self.combo.lineEdit().clear()
        self.combo.lineEdit().returnPressed.connect(self._ok)
        lay.addWidget(self.combo)
        self.lbl = QLabel()
        self.lbl.setStyleSheet('color: #c00000;')
        lay.addWidget(self.lbl)

    def _ok(self):
        s = self.okno.slowniki.get('STOREY_CD')
        tekst = self.combo.currentText()
        kod = s.rozwiaz(tekst) if s else tekst.split(' | ')[0].strip()
        if kod not in self.wolne:
            self.lbl.setText(f'"{tekst}" - wybierz jedną z: '
                             + ', '.join(self.wolne))
            return
        self.kod = kod
        self.accept()

    def keyPressEvent(self, event):
        # Enter obsługuje pole (returnPressed), nie domyślny przycisk
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            return
        super().keyPressEvent(event)


def _tabela_edytowalna(kolumny, okno, callback, po_enter=None,
                       podpowiedz=None):
    """Tabela warstwy/gatunków; kolumny: (nagłówek, pole, typ, słownik,
    miejsca, szerokość)."""
    t = _tabela([k[0] for k in kolumny], [k[5] for k in kolumny])
    if not okno.tylko_odczyt:
        t.setItemDelegate(_DelegatTabeli(
            okno, [(k[2], k[3]) for k in kolumny], callback, po_enter,
            podpowiedz))
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(
            QAbstractItemView.CurrentChanged | QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed)
    return t


# ----------------------------------------------------------- grupa warstwy

class _GrupaWarstwy(QWidget):
    """Zwijana grupa jednej warstwy: nagłówek (kod, liczba gatunków,
    uwagi reguł, "Usuń warstwę"), pod nim tabela parametrów warstwy (lewa)
    i gatunków (prawa) - jak w Taksatorze. Dane: okno.dane['WARSTWY'][wi]."""

    def __init__(self, okno, wi, parent=None):
        super().__init__(parent)
        self.okno = okno
        self.wi = wi
        self.kod = okno.dane['WARSTWY'][wi]['STOREY_CD']
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)

        naglowek = QHBoxLayout()
        naglowek.setContentsMargins(0, 0, 0, 0)
        self.btn = QToolButton()
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn.setCheckable(True)
        self.btn.setStyleSheet(
            'QToolButton { border: none; font-weight: bold; }')
        self.btn.toggled.connect(self._przelacz)
        naglowek.addWidget(self.btn)
        self.lbl_uwagi = QLabel()
        naglowek.addWidget(self.lbl_uwagi)
        naglowek.addStretch(1)
        if not okno.tylko_odczyt:
            usun = QToolButton()
            usun.setText('Usuń warstwę')
            usun.setStyleSheet('QToolButton { color: #c62828; border: none; }')
            usun.clicked.connect(lambda: okno.usun_warstwe(self.wi))
            naglowek.addWidget(usun)
        lay.addLayout(naglowek)

        self.cialo = QWidget()
        hl = QHBoxLayout(self.cialo)
        hl.setContentsMargins(14, 0, 0, 0)
        hl.setSpacing(4)
        self.tw = _tabela_edytowalna(
            KOLUMNY_WARSTWY, okno,
            lambda r, c, t: okno.ustaw_warstwe(self.wi, KOLUMNY_WARSTWY[c][1], t),
            lambda r, c, e: self._enter('w', r, c, e))
        # zmieszania i zwarcia nie podaje się poza DRZEW (IP/IIP) - kolumny
        # ukryte, ale miejsce tabeli zostaje (tabele gatunków w jednej linii)
        pelna = self.tw.width()
        if self.kod not in ow.JAK_DRZEW:
            for c, k in enumerate(KOLUMNY_WARSTWY):
                if k[1] in ('MIXTURE_CD', 'DENSITY_CD'):
                    self.tw.setColumnHidden(c, True)
            self.tw.setFixedWidth(
                sum(k[5] for k in KOLUMNY_WARSTWY
                    if k[1] not in ('MIXTURE_CD', 'DENSITY_CD'))
                + 2 * self.tw.frameWidth())
        miejsce = QWidget()
        miejsce.setFixedWidth(pelna)
        ml = QVBoxLayout(miejsce)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.addWidget(self.tw, 0, Qt.AlignLeft | Qt.AlignTop)
        ml.addStretch(1)
        hl.addWidget(miejsce, 0, Qt.AlignTop)
        self.tg = _tabela_edytowalna(
            KOLUMNY_GATUNKI + [KOLUMNA_USUN], okno,
            lambda r, c, t: okno.ustaw_gatunek(
                self.wi, r, KOLUMNY_GATUNKI[c][1], t),
            lambda r, c, e: self._enter('g', r, c, e),
            lambda r, c: okno.podpowiedz_bonitacji(self.wi, r)
            if c < len(KOLUMNY_GATUNKI) and
            KOLUMNY_GATUNKI[c][1] == 'SITE_CLASS_CD' else None)
        self.tg.cellClicked.connect(self._klik_gatunku)
        hl.addWidget(self.tg, 0, Qt.AlignTop)
        if not okno.tylko_odczyt:
            # Enter bez otwartego edytora (drugi Enter na końcu wiersza)
            self.tw.installEventFilter(self)
            self.tg.installEventFilter(self)
        hl.addStretch(1)
        lay.addWidget(self.cialo)
        self.odswiez()
        self.ustaw(True)

    def odswiez(self):
        okno = self.okno
        w = okno.dane['WARSTWY'][self.wi]
        org = okno.oryginalna_warstwa(self.kod)
        wal = okno.walidacja

        self.tw.setRowCount(1)
        for c, (_n, pole, _t, slow, m, _s) in enumerate(KOLUMNY_WARSTWY):
            zm = org is None or org[pole] != w[pole]
            self.tw.setItem(0, c, okno.komorka(
                _fmt(w[pole], m), wal.get((self.wi, None, pole)), zm,
                slow, w[pole]))
        _dopasuj(self.tw)

        gat = w['gatunki']
        org_g = {g['SPEC_STOR_INT_NUM']: g for g in org['gatunki']} \
            if org else {}
        # dubel gatunek+wiek (GAT13) - cały wiersz na czerwono
        duble = {gi for (wi, gi, pole), lst in wal.items()
                 if wi == self.wi and pole == 'SPECIES_CD'
                 and any(k == 'GAT13' for _p, k, _t in lst)}
        n = len(gat) + (0 if okno.tylko_odczyt else 1)
        self.tg.setRowCount(n)
        kol_usun = len(KOLUMNY_GATUNKI)
        for r in range(n):
            g = gat[r] if r < len(gat) else None
            stary = org_g.get(g['SPEC_STOR_INT_NUM']) if g else None
            for c, (_n, pole, _t, slow, m, _s) in enumerate(KOLUMNY_GATUNKI):
                if g is None:
                    it = QTableWidgetItem('')
                    if c:  # nowy gatunek zaczyna się od kodu
                        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    else:
                        it.setToolTip('Wpisz kod albo numer gatunku, żeby '
                                      'dodać gatunek')
                else:
                    zm = stary is None or stary[pole] != g[pole]
                    kom = list(wal.get((self.wi, r, pole), []))
                    if r in duble and not any(p == ow.BLAD for p, *_ in kom):
                        kom.append((ow.BLAD, 'GAT13', 'Ten sam gatunek w tym '
                                    'samym wieku w warstwie'))
                    it = okno.komorka(_fmt(g[pole], m), kom, zm, slow, g[pole])
                self.tg.setItem(r, c, it)
            it = QTableWidgetItem('✕' if g is not None and
                                  not okno.tylko_odczyt else '')
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            it.setTextAlignment(Qt.AlignCenter)
            it.setForeground(QBrush(QColor(198, 40, 40)))
            if g is not None:
                it.setToolTip('Usuń gatunek (zmiana trafi do bazy po Zapisz)')
            self.tg.setItem(r, kol_usun, it)
        _dopasuj(self.tg)

        self.btn.setText(f'{self.kod}   ({len(gat)} gat.)')
        uwagi = wal.get((self.wi, None, None), [])
        bledy = len(ow.lista_bledow(
            {k: v for k, v in wal.items() if k[0] == self.wi},
            okno.dane['WARSTWY']))
        if bledy:
            self.lbl_uwagi.setText(f'błędy: {bledy}')
            self.lbl_uwagi.setStyleSheet('color: #c00000;')
        else:
            self.lbl_uwagi.setText('')
        self.lbl_uwagi.setToolTip('\n'.join(tx for _p, _k, tx in uwagi))

    def _przelacz(self, rozwiniety):
        self.btn.setArrowType(Qt.DownArrow if rozwiniety else Qt.RightArrow)
        self.cialo.setVisible(rozwiniety)

    def ustaw(self, rozwiniety):
        self.btn.setChecked(rozwiniety)
        self._przelacz(rozwiniety)

    # ---------------------------------------------------- usuwanie wiersza

    def _klik_gatunku(self, r, c):
        if c == len(KOLUMNY_GATUNKI) and not self.okno.tylko_odczyt and \
                r < len(self.okno.dane['WARSTWY'][self.wi]['gatunki']):
            QTimer.singleShot(0, lambda: self.okno.usun_gatunek(self.wi, r))

    # ------------------------------------------------------ nawigacja Enter

    def eventFilter(self, obiekt, event):
        if event.type() == QEvent.KeyPress and \
                event.key() in (Qt.Key_Return, Qt.Key_Enter) and \
                obiekt in (self.tw, self.tg) and \
                obiekt.state() != QAbstractItemView.EditingState:
            r, c = obiekt.currentRow(), obiekt.currentColumn()
            if r >= 0 and c >= 0:
                self._enter('w' if obiekt is self.tw else 'g', r, c, False)
                return True
        return super().eventFilter(obiekt, event)

    def _idz(self, tabela, r, c):
        idz_do_komorki(tabela, r, c)

    def _enter(self, tab, r, c, w_edycji):
        """Enter: następna wymagana komórka wiersza (reguły warstwy); na
        ostatniej - pierwszy Enter zatwierdza, drugi przechodzi do nowego
        wiersza gatunku. Parametry warstwy -> dalej gatunki."""
        okno = self.okno
        if okno.dane is None or sip.isdeleted(self) or \
                self.wi >= len(okno.dane['WARSTWY']):
            return
        w = okno.dane['WARSTWY'][self.wi]
        gat = w['gatunki']
        if tab == 'w':
            pola = ow.pola_wymagane_warstwy(w['STOREY_CD'])
            kolumny = [k[1] for k in KOLUMNY_WARSTWY]
            dalej = [x for x in pola if kolumny.index(x) > c]
            if dalej:
                self._idz(self.tw, 0, kolumny.index(dalej[0]))
            else:
                self._idz(self.tg, 0, 0)
            return
        if r >= len(gat):
            # Enter na pustym wierszu (trzeci na końcu warstwy): następna
            # warstwa, a za ostatnią - okienko nowej warstwy
            okno.po_ostatnim_wierszu(self.wi)
            return
        pola = ow.pola_wymagane_gatunku(w['STOREY_CD'], gat[r])
        kolumny = [k[1] for k in KOLUMNY_GATUNKI]
        dalej = [x for x in pola if kolumny.index(x) > c]
        if dalej:
            self._idz(self.tg, r, kolumny.index(dalej[0]))
        elif not w_edycji:
            self._idz(self.tg, len(gat), 0)  # drugi Enter - nowy wiersz


# kolumna z przyciskiem usunięcia wiersza gatunku (✕)
KOLUMNA_USUN = ('', '_USUN', 'usun', None, None, 22)
SZEROKOSC_GRUPY = (14 + sum(k[5] for k in KOLUMNY_WARSTWY)
                   + sum(k[5] for k in KOLUMNY_GATUNKI) + KOLUMNA_USUN[5]
                   + 4 + 4 * 2)


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
        self.walidacja = {}

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
        dane['WARSTWY'] = _model_warstw(warstwy, gatunki)
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
        self.lbl_walidacja = QLabel()
        gora.addWidget(self.lbl_walidacja)
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
        self.t_opis.setItemDelegate(_DelegatTabeli(
            self, [('kod' if k[2] in ('kod', 'lista') else 'liczba', k[3])
                   for k in KOLUMNY_OPIS],
            lambda r, c, t: self.ustaw_pole(KOLUMNY_OPIS[c][1], t, r),
            lambda r, c, e: self._enter_opis(r, c, e)))
        if not self.tylko_odczyt:
            self.t_opis.installEventFilter(self)
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

        # --- przyciski na dole okna (z dala od zamykania okna); usuwanie
        # po przeciwnej stronie niż Zapisz
        self.pasek = QHBoxLayout()
        self.btn_usun = QPushButton('Usuń wydzielenie')
        self.btn_usun.setToolTip(
            'Usuwa z bazy wydzielenie z całym opisem (geometria zostaje)')
        self.btn_usun.setStyleSheet(
            'QPushButton { color: white; background: #c62828; '
            'padding: 3px 10px; } '
            'QPushButton:disabled { background: #e8b4b4; }')
        self.btn_usun.clicked.connect(self.usun_wydzielenie)
        self.pasek.addWidget(self.btn_usun)
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
        self.walidacja = {}
        self.lbl_walidacja.setText('')
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

    def oryginalna_warstwa(self, kod):
        if self.oryginal is None:
            return None
        return next((w for w in self.oryginal['WARSTWY']
                     if w['STOREY_CD'] == kod), None)

    def komorka(self, tekst, komunikaty, zmienione, slow=None, wartosc=None):
        """Komórka z kolorem: błąd > ostrzeżenie > zmienione; podpowiedź -
        komunikaty reguł i opis kodu ze słownika."""
        it = QTableWidgetItem(tekst)
        komunikaty = komunikaty or []
        poziomy = {p for p, *_ in komunikaty}
        tlo = BLEDNE if ow.BLAD in poziomy else \
            OSTRZEGAWCZE if ow.OSTRZ in poziomy else \
            ZMIENIONE if zmienione else None
        if tlo is not None:
            it.setBackground(QBrush(tlo))
            # jasne tło - ciemny tekst (czytelne także w ciemnym motywie)
            it.setForeground(QBrush(QColor(20, 20, 20)))
        tip = [('BŁĄD' if p == ow.BLAD else 'Uwaga') +
               (f' {k}' if k else '') + f': {tx}' for p, k, tx in komunikaty]
        s = self.slowniki.get(slow) if slow else None
        if s is not None and wartosc:
            tip.append(s.opis(str(wartosc)))
        if tip:
            it.setToolTip('\n'.join(tip))
        if self.tylko_odczyt:
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        return it

    def _przelicz(self):
        self.walidacja = ow.waliduj(self.dane['WARSTWY'],
                                    self.dane['AREA_TYPE_CD'])
        _b, ostrz = ow.policz(self.walidacja)
        bledy = len(ow.lista_bledow(self.walidacja, self.dane['WARSTWY']))
        tekst = []
        if bledy:
            tekst.append(f'<span style="color:#c00000">błędy: {bledy}</span>')
        if ostrz:
            tekst.append(f'<span style="color:#9a7000">ostrzeżenia: {ostrz}'
                         '</span>')
        self.lbl_walidacja.setText('  '.join(tekst))
        wydz = self.walidacja.get(('wydz', None, None), [])
        self.lbl_walidacja.setToolTip('\n'.join(tx for _p, _k, tx in wydz))

    def _odbuduj_grupy(self, rozwiniete=None):
        """Grupy warstw od nowa (po dodaniu/usunięciu warstwy albo
        wczytaniu). rozwiniete: {kod: bool} - stan do zachowania."""
        self._wyczysc_warstwy()
        for wi in range(len(self.dane['WARSTWY'])):
            grupa = _GrupaWarstwy(self, wi)
            if rozwiniete is not None:
                grupa.ustaw(rozwiniete.get(grupa.kod, True))
            grupa.btn.toggled.connect(
                lambda _r: QTimer.singleShot(0, self._dopasuj_okno))
            self.lay_warstw.addWidget(grupa)
            self.grupy.append(grupa)
        if not self.dane['WARSTWY']:
            self.lay_warstw.addWidget(QLabel('  (brak warstw)'))
        if not self.tylko_odczyt:
            obecne = {w['STOREY_CD'] for w in self.dane['WARSTWY']}
            wolne = [k for k in ow.PRAKTYCZNE if k not in obecne]
            if wolne:
                btn = QToolButton()
                btn.setText('+ Warstwa')
                btn.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(btn)
                for k in wolne:
                    menu.addAction(k, lambda k=k: self.dodaj_warstwe(k))
                btn.setMenu(menu)
                wiersz = QHBoxLayout()
                wiersz.setContentsMargins(0, 0, 0, 0)
                wiersz.addWidget(btn)
                wiersz.addStretch(1)
                kontener = QWidget()
                kontener.setLayout(wiersz)
                self.lay_warstw.addWidget(kontener)

    def _stan_grup(self):
        return {g.kod: g.btn.isChecked() for g in self.grupy
                if not sip.isdeleted(g)}

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

        self._przelicz()
        self._odbuduj_grupy()

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
                    it.setForeground(QBrush(QColor(20, 20, 20)))
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
        if pole == 'AREA_TYPE_CD':  # WAR33 zależy od rodzaju powierzchni
            self._przelicz()
        self._status('')
        self._odswiez_przyciski()
        QTimer.singleShot(0, self._dopasuj_okno)

    def _wartosc(self, typ, slow, tekst):
        """(ok, wartość) z tekstu komórki; przy błędzie komunikat w statusie."""
        tekst = (tekst or '').strip()
        if not tekst:
            return True, ('' if typ == 'kod' else None)
        if typ == 'kod':
            s = self.slowniki.get(slow)
            kod = s.rozwiaz(tekst) if s else None
            if kod is None:
                self._blad(f'Nieznany kod/numer: "{tekst}"')
                return False, None
            return True, kod
        try:
            v = float(tekst.replace(',', '.'))
        except ValueError:
            self._blad(f'"{tekst}" to nie liczba')
            return False, None
        if v < 0:
            self._blad('Wartość nie może być ujemna')
            return False, None
        if typ == 'calk':
            if not v.is_integer():
                self._blad(f'"{tekst}" - wymagana liczba całkowita')
                return False, None
            return True, int(v)
        return True, v

    def _po_zmianie_warstwy(self, wi):
        self._przelicz()
        if 0 <= wi < len(self.grupy):
            self.grupy[wi].odswiez()
        self._status('')
        self._odswiez_przyciski()
        QTimer.singleShot(0, self._dopasuj_okno)

    def ustaw_warstwe(self, wi, pole, tekst):
        if sip.isdeleted(self) or self.dane is None or self.tylko_odczyt:
            return
        _n, _p, typ, slow, _m, _s = next(
            k for k in KOLUMNY_WARSTWY if k[1] == pole)
        ok, v = self._wartosc(typ, slow, tekst)
        if not ok:
            return
        self.dane['WARSTWY'][wi][pole] = v
        self._po_zmianie_warstwy(wi)

    def ustaw_gatunek(self, wi, gi, pole, tekst):
        if sip.isdeleted(self) or self.dane is None or self.tylko_odczyt:
            return
        gat = self.dane['WARSTWY'][wi]['gatunki']
        _n, _p, typ, slow, _m, _s = next(
            k for k in KOLUMNY_GATUNKI if k[1] == pole)
        ok, v = self._wartosc(typ, slow, tekst)
        if not ok:
            return
        if gi >= len(gat):
            if pole != 'SPECIES_CD' or not v:
                return
            gat.append({'SPEC_STOR_INT_NUM': None, 'SPECIES_CD': v,
                        'PART_CD': '', 'SPECIES_AGE': None, 'BHD': None,
                        'HEIGHT': None, 'SITE_CLASS_CD': '', 'VOLUME': None})
        else:
            gat[gi][pole] = v
            # wiersz znika dopiero, gdy wyczyszczono wszystkie jego komórki
            if all(ow.pusty(gat[gi][p]) for p in ow.POLA_GATUNKU):
                del gat[gi]
        self._po_zmianie_warstwy(wi)

    def podpowiedz_bonitacji(self, wi, gi):
        """Bonitacja z tablic (gatunek, wiek, wysokość) do pustej komórki."""
        if self.dane is None or wi >= len(self.dane['WARSTWY']):
            return None
        gat = self.dane['WARSTWY'][wi]['gatunki']
        if gi >= len(gat):
            return None
        g = gat[gi]
        return ow.sugeruj_bonitacje(
            self.panel.tablica_bonit, self.panel.grupy_bonit,
            g['SPECIES_CD'], g['SPECIES_AGE'], g['HEIGHT'])

    def usun_gatunek(self, wi, gi):
        """Przycisk ✕ w wierszu gatunku."""
        if sip.isdeleted(self) or self.dane is None or self.tylko_odczyt:
            return
        gat = self.dane['WARSTWY'][wi]['gatunki']
        if 0 <= gi < len(gat):
            del gat[gi]
            self._po_zmianie_warstwy(wi)

    def idz_do_warstwy(self, wi):
        """Pierwsze wymagane pole warstwy: parametr (Zmiesz./Zd.) albo, gdy
        warstwa nie ma parametrów (PRZES), kod pierwszego gatunku."""
        if wi >= len(self.grupy):
            return
        g = self.grupy[wi]
        g.ustaw(True)
        self.przewijanie.ensureWidgetVisible(g)
        pola = ow.pola_wymagane_warstwy(g.kod)
        if pola:
            kolumny = [k[1] for k in KOLUMNY_WARSTWY]
            idz_do_komorki(g.tw, 0, kolumny.index(pola[0]))
        else:
            idz_do_komorki(g.tg, 0, 0)

    def po_ostatnim_wierszu(self, wi):
        if wi + 1 < len(self.dane['WARSTWY']):
            self.idz_do_warstwy(wi + 1)
        else:
            self.nowa_warstwa_z_klawiatury(wi)

    def nowa_warstwa_z_klawiatury(self, wi=-1):
        obecne = {w['STOREY_CD'] for w in self.dane['WARSTWY']}
        wolne = [k for k in ow.PRAKTYCZNE if k not in obecne]
        if not wolne or self.tylko_odczyt:
            return
        dlg = _NowaWarstwaDialog(self, wolne)
        if 0 <= wi < len(self.grupy):
            tg = self.grupy[wi].tg
            dlg.move(tg.mapToGlobal(QPoint(0, tg.height())))
        if dlg.exec_() != QDialog.Accepted or not dlg.kod:
            return
        self.dodaj_warstwe(dlg.kod)
        nowy = next(i for i, w in enumerate(self.dane['WARSTWY'])
                    if w['STOREY_CD'] == dlg.kod)
        QTimer.singleShot(0, lambda: self.idz_do_warstwy(nowy))

    # -------------------------------------------- Enter w opisie wydzielenia

    def _enter_opis(self, r, c, _w_edycji):
        """Opis wydzielenia: Enter - następna kolumna; w cechach/TD po
        wpisanym kodzie niżej (kolejny kod), na pustym - następna kolumna;
        po ostatniej kolumnie - pierwsza warstwa (albo nowa warstwa)."""
        if self.dane is None or self.tylko_odczyt:
            return
        _n, pole, typ, _s = KOLUMNY_OPIS[c]
        if typ == 'lista' and r < len(self.dane[pole]):
            idz_do_komorki(self.t_opis, r + 1, c)
        elif c + 1 < len(KOLUMNY_OPIS):
            idz_do_komorki(self.t_opis, 0, c + 1)
        elif self.dane['WARSTWY']:
            self.idz_do_warstwy(0)
        else:
            self.nowa_warstwa_z_klawiatury(-1)

    def eventFilter(self, obiekt, event):
        if obiekt is self.t_opis and event.type() == QEvent.KeyPress and \
                event.key() in (Qt.Key_Return, Qt.Key_Enter) and \
                self.t_opis.state() != QAbstractItemView.EditingState:
            r, c = self.t_opis.currentRow(), self.t_opis.currentColumn()
            if r >= 0 and c >= 0:
                self._enter_opis(r, c, False)
                return True
        return super().eventFilter(obiekt, event)

    def _nr_warstw(self):
        s = self.slowniki.get('STOREY_CD')
        return {k: float(n) for k, n in (s.kod_nr.items() if s else [])}

    def dodaj_warstwe(self, kod):
        if self.dane is None or self.tylko_odczyt:
            return
        if any(w['STOREY_CD'] == kod for w in self.dane['WARSTWY']):
            self._blad(f'Warstwa {kod} już jest w tym wydzieleniu')
            return
        stan = self._stan_grup()
        self.dane['WARSTWY'].append({
            'STOREY_CD': kod, 'MIXTURE_CD': '', 'DENSITY_CD': '',
            'STANDDENSITY_INDEX': None, 'gatunki': []})
        nr = self._nr_warstw()
        self.dane['WARSTWY'].sort(key=lambda w: ow.KOLEJNOSC_SPECJALNA.get(
            w['STOREY_CD'], nr.get(w['STOREY_CD'], 99.0)))
        stan[kod] = True
        self._przelicz()
        self._odbuduj_grupy(stan)
        self._status(f'dodano warstwę {kod} - wpisz gatunki')
        self._odswiez_przyciski()
        QTimer.singleShot(0, self._dopasuj_okno)

    def usun_warstwe(self, wi):
        if self.dane is None or self.tylko_odczyt:
            return
        w = self.dane['WARSTWY'][wi]
        odp = QMessageBox.question(
            self, 'Usuń warstwę',
            f"Usunąć warstwę {w['STOREY_CD']} ({len(w['gatunki'])} gat.)?\n"
            'Zmiana trafi do bazy dopiero po "Zapisz".',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if odp != QMessageBox.Yes:
            return
        stan = self._stan_grup()
        del self.dane['WARSTWY'][wi]
        self._przelicz()
        self._odbuduj_grupy(stan)
        self._odswiez_przyciski()
        QTimer.singleShot(0, self._dopasuj_okno)

    def _lista_bledow(self):
        """Błędy twarde bez powtórzeń (do okna przy zapisie)."""
        return ow.lista_bledow(self.walidacja, self.dane['WARSTWY'])

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
        self.btn_usun.setVisible(not self.tylko_odczyt)
        self.btn_usun.setEnabled(self.dane is not None and self.aint is not None)
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
        stan = self._stan_grup()
        self.dane = copy.deepcopy(self.oryginal)
        self._wypelnij_opis()
        self._przelicz()
        self._odbuduj_grupy(stan)
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

        self._przelicz()
        bledy = self._lista_bledow()
        if bledy:
            QMessageBox.warning(
                self, 'Nie zapisano - błędy w opisie',
                'Popraw błędy (czerwone komórki) i zapisz ponownie:\n\n- ' +
                '\n- '.join(bledy[:20]) + ('\n- ...' if len(bledy) > 20 else ''))
            return False

        if not self.panel.kopia_sesji():
            return self._blad('Nie udało się zrobić kopii bazy - nie zapisano')

        d, o, aint = self.dane, self.oryginal, self.aint
        plan_warstw, dziennik_warstw = [], []
        if d['WARSTWY'] != o['WARSTWY']:
            nowe = ow.posortuj(copy.deepcopy(d['WARSTWY']), self._nr_warstw())
            plan_warstw, dziennik_warstw = ow.plan_zapisu(
                aint, o['WARSTWY'], nowe)
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
            for sql, parametry in plan_warstw:
                cur.execute(sql, parametry)
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

        pola = POLA_SUBAREA + ['FOREST_PEC_CD', 'TD']
        self._do_dziennika(
            [(self.adr, 'ZMIANA', p, o[p], d[p]) for p in pola if d[p] != o[p]]
            + [(self.adr, *w) for w in dziennik_warstw])

        wynik = self._wczytaj(aint)
        if wynik:
            self._wypelnij(*wynik)
        self._status('zapisano', '#107010')
        self.iface.messageBar().pushSuccess(
            'Opis taksacyjny', f'Zapisano zmiany: {self.adr}')
        return True

    def _do_dziennika(self, wiersze):
        if wiersze and not dopisz_do_dziennika(self.baza_sc, wiersze):
            self.iface.messageBar().pushWarning(
                'Opis taksacyjny', 'Nie udało się dopisać do dziennika '
                f'{sciezka_dziennika(self.baza_sc)} (zmiana w bazie zapisana)')

    def _migawka(self, aint):
        """Pełna zawartość rekordów wydzielenia - do dziennika przed
        usunięciem (odtworzenie ręczne bez sięgania do kopii bazy)."""
        wyn = []
        for tabela in TABELE_WYDZIELENIA:
            try:
                wiersze = self._wiersze(
                    f'select * from {tabela} where ARODES_INT_NUM = ?', (aint,))
            except Exception:
                continue
            if wiersze:
                wyn.append((tabela, json.dumps(
                    wiersze, ensure_ascii=False, default=str)))
        return wyn

    def usun_wydzielenie(self):
        if self.tylko_odczyt or self.aint is None or self.dane is None:
            return
        adr, aint = self.adr, self.aint
        odp = QMessageBox.question(
            self, 'Usuń wydzielenie',
            f'Usunąć z bazy wydzielenie\n{adr}\nz całym opisem (warstwy, '
            'gatunki, zabiegi, TD, cechy, PNSW)?\n\nGeometria na warstwie '
            'zostaje bez zmian.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if odp != QMessageBox.Yes:
            return
        if not self.panel.kopia_sesji():
            self._blad('Nie udało się zrobić kopii bazy - nic nie usunięto')
            return

        migawka = self._migawka(aint)
        if not self.baza.usun_rekordy([aint]):
            QMessageBox.critical(
                self, 'Błąd usuwania',
                'Usuwanie nie powiodło się - wycofano, w bazie nic się nie '
                'zmieniło (szczegóły w logu Las-R).')
            return

        self._do_dziennika(
            [(adr, 'USUNIECIE', tabela, dane, '') for tabela, dane in migawka])
        self.wydz.pop(adr, None)
        self.panel.przelicz_zgodnosc()  # też warstwa "WYDZ bez opisu"
        self.dane = self.oryginal = None
        self._pokaz('wydzielenie usunięte z bazy (geometria bez zmian)')
        self.iface.messageBar().pushSuccess(
            'Opis taksacyjny', f'Usunięto z bazy: {adr}')

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

    TYTUL = 'Edytor opisu taksacyjnego'

    def __init__(self, iface):
        super().__init__(self.TYTUL, iface.mainWindow())
        # nowa nazwa - stara ('LasR_PanelOpisuTaks') mogła zostać w
        # zapamiętanym przez QGIS układzie w rozbitym miejscu (splitDockWidget
        # z Layers w pierwszej wersji)
        self.setObjectName('LasR_EdytorOpisuTaks')
        self.iface = iface
        self.lyr = None
        self.baza = None
        self.baza_sc = ''
        self.tylko_odczyt = False
        self.slowniki = {}
        self.wydz = {}
        self.karta = None
        self.tablica_bonit, self.grupy_bonit = {}, {}
        self._podglad = None
        self.max_h = 0
        self.kopia_zrobiona = False
        self._szczegoly = ''
        self._warstwy = []
        # przeliczenie zgodności po zmianach na warstwie - z opóźnieniem,
        # żeby seryjne kasowanie poligonów nie liczyło jej przy każdym
        self._timer_zgodnosci = QTimer(self)
        self._timer_zgodnosci.setSingleShot(True)
        self._timer_zgodnosci.setInterval(500)
        self._timer_zgodnosci.timeout.connect(self.przelicz_zgodnosc)
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

        self.btn_kopia = QPushButton('Zapisz kopię bazy')
        self.btn_kopia.setToolTip(
            'Kopia bazy i plików warstwy wydzieleń do Kopie_manipulacyjne '
            f'(zostaje {ILE_KOPII} ostatnich kopii Edytora)')
        self.btn_kopia.clicked.connect(self.zrob_kopie)
        lay.addWidget(self.btn_kopia)

        self.btn_podglad = QPushButton('Podglądnij opis (PPM)')
        self.btn_podglad.setCheckable(True)
        self.btn_podglad.setToolTip(
            'Po włączeniu przytrzymanie prawego przycisku myszy na '
            'wydzieleniu pokazuje przy kursorze skrót opisu z bazy')
        self.btn_podglad.toggled.connect(self._przelacz_podglad)
        lay.addWidget(self.btn_podglad)

        # miejsce na kolejne funkcje panelu
        self.lay_dodatki = QVBoxLayout()
        lay.addLayout(self.lay_dodatki)
        lay.addStretch(1)
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
        self.btn_kopia.setEnabled(pol)
        self.btn_szczegoly.setEnabled(pol)
        self.btn_podglad.setEnabled(pol)
        if not pol and self.btn_podglad.isChecked():
            self.btn_podglad.setChecked(False)
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
        if not ok and not okno_zgodnosci(self, podsum, szczegoly, True):
            baza.zamknij()
            return

        self.lyr = lyr
        self.baza = baza
        self.baza_sc = baza_sc
        # od tej chwili inne skrypty wtyczki nie połączą się z tą bazą
        zajmij_baze(baza_sc)
        self.tylko_odczyt = bool(blokada)
        self.slowniki = slowniki
        self.tablica_bonit, self.grupy_bonit = \
            ow.wczytaj_tablice_bonitacji(baza.cur)
        self.wydz = wydz
        self._szczegoly = '' if ok else podsum + '\n\n' + szczegoly
        self.max_h = 0
        self.kopia_zrobiona = False
        self.lyr.selectionChanged.connect(self._zaznaczenie)
        for sygnal in self._sygnaly_warstwy():
            sygnal.connect(self._zmiana_warstwy)
        self._odswiez()
        self.odswiez_bez_opisu()
        self.iface.messageBar().pushSuccess(
            'Opis taksacyjny', f'Podłączono bazę {os.path.basename(baza_sc)}')
        self._zaznaczenie()

    def _sygnaly_warstwy(self):
        """Zmiany warstwy wydzieleń wpływające na zgodność z bazą (także
        w buforze edycji, przed zapisem warstwy)."""
        return (self.lyr.featureAdded, self.lyr.featureDeleted,
                self.lyr.attributeValueChanged, self.lyr.afterCommitChanges,
                self.lyr.afterRollBack)

    def _zmiana_warstwy(self, *_args):
        self._timer_zgodnosci.start()

    def przelicz_zgodnosc(self):
        """Zgodność warstwa-baza na bieżącym stanie warstwy i liście
        wydzieleń bazy (aktualizowanej przy usuwaniu w Edytorze)."""
        if not self.polaczona() or sip.isdeleted(self.lyr):
            return
        ok, podsum, szczegoly = sprawdz_zgodnosc(self.lyr, self.wydz)
        self._szczegoly = '' if ok else podsum + '\n\n' + szczegoly
        self._odswiez()
        self.odswiez_bez_opisu()

    def zrob_kopie(self):
        """Pakiet: baza + pliki warstwy wydzieleń. Zwraca ścieżkę folderu
        albo None. Liczy się też jako kopia sesji."""
        if not self.polaczona():
            return None
        folder = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
            self.baza_sc, [self.lyr], NAZWA_KOPII)
        if folder is None:
            QMessageBox.critical(
                self, 'Kopia bazy',
                'Nie udało się zrobić kopii bazy (szczegóły w logu Las-R).')
            return None
        self.kopia_zrobiona = True
        self._rotuj_kopie(os.path.dirname(folder))
        self.iface.messageBar().pushSuccess(
            'Opis taksacyjny', f'Kopia bazy: {folder}')
        return folder

    def kopia_sesji(self):
        """Automatyczny pakiet kopii raz na połączenie (przed pierwszą
        zmianą). False - kopia się nie udała, nie wolno zapisywać."""
        return self.kopia_zrobiona or self.zrob_kopie() is not None

    @staticmethod
    def _rotuj_kopie(kat_kopii):
        """Zostawia ILE_KOPII najnowszych pakietów Edytora (nazwy z czasem
        RRRR-MM-DD_GG-MM-SS sortują się chronologicznie); kopie innych
        skryptów nietknięte."""
        try:
            foldery = sorted(
                d for d in os.listdir(kat_kopii)
                if d.startswith(NAZWA_KOPII + '_')
                and os.path.isdir(os.path.join(kat_kopii, d)))
        except OSError:
            return
        for d in foldery[:-ILE_KOPII]:
            shutil.rmtree(os.path.join(kat_kopii, d), ignore_errors=True)

    def odswiez_bez_opisu(self):
        """Warstwa pamięci z poligonami wydzieleń, których ADR_LES nie ma w
        bazie (w tym usuniętych w Edytorze) - czerwone kreskowanie,
        odświeżana razem ze zgodnością. Warstwa wydzieleń bez zmian."""
        if not self.polaczona() or sip.isdeleted(self.lyr):
            return
        prj = QgsProject.instance()
        nowe = []
        for f in self.lyr.getFeatures():
            adr = _txt(f['ADR_LES'])
            if adr and adr not in self.wydz and f.hasGeometry():
                g = QgsGeometry(f.geometry())
                g.convertToMultiType()
                nowe.append((adr, g))
        lyr = getattr(self, '_lyr_bez_opisu', None)
        zywa = lyr is not None and not sip.isdeleted(lyr) and \
            prj.mapLayer(lyr.id()) is not None
        if not nowe and not zywa:
            return
        if not zywa:
            lyr = QgsVectorLayer(
                f'MultiPolygon?crs={self.lyr.crs().authid()}',
                NAZWA_BEZ_OPISU, 'memory')
            lyr.dataProvider().addAttributes(
                [QgsField('ADR_LES', QVariant.String, '', 25)])
            lyr.updateFields()
            lyr.renderer().setSymbol(QgsFillSymbol.createSimple({
                'color': '230,0,0,60', 'style': 'b_diagonal',
                'outline_color': '230,0,0,255', 'outline_width': '0.8'}))
            prj.addMapLayer(lyr)
            self._lyr_bez_opisu = lyr
        lyr.dataProvider().truncate()
        obiekty = []
        for adr, g in nowe:
            nf = QgsFeature(lyr.fields())
            nf.setGeometry(g)
            nf['ADR_LES'] = adr
            obiekty.append(nf)
        lyr.dataProvider().addFeatures(obiekty)
        lyr.updateExtents()
        lyr.triggerRepaint()

    def _usun_warstwe_bez_opisu(self):
        lyr = getattr(self, '_lyr_bez_opisu', None)
        if lyr is not None and not sip.isdeleted(lyr) and \
                QgsProject.instance().mapLayer(lyr.id()) is not None:
            QgsProject.instance().removeMapLayer(lyr.id())
        self._lyr_bez_opisu = None

    # --------------------------------------------------- podgląd pod PPM

    def _kanwa(self):
        try:
            return self.iface.mapCanvas()
        except AttributeError:
            return None

    def _przelacz_podglad(self, wlaczony):
        kanwa = self._kanwa()
        if kanwa is None:
            return
        if wlaczony:
            kanwa.viewport().installEventFilter(self)
        else:
            kanwa.viewport().removeEventFilter(self)
            self._schowaj_podglad()

    def eventFilter(self, obiekt, event):
        """Przy włączonym podglądzie prawy przycisk mapy należy do podglądu
        (menu kontekstowe mapy wyłączone); lewy - bez zmian."""
        if not self.btn_podglad.isChecked():
            return super().eventFilter(obiekt, event)
        typ = event.type()
        if typ == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            self._pokaz_podglad(event.pos())
            return True
        if typ == QEvent.MouseButtonRelease and \
                event.button() == Qt.RightButton:
            self._schowaj_podglad()
            return True
        if typ == QEvent.ContextMenu:
            return True
        return super().eventFilter(obiekt, event)

    def _wydzielenie_pod(self, pos):
        """ADR_LES poligonu warstwy wydzieleń pod punktem ekranu."""
        kanwa = self._kanwa()
        if kanwa is None or not self.polaczona() or sip.isdeleted(self.lyr):
            return None
        pt = kanwa.getCoordinateTransform().toMapCoordinates(pos)
        tr = QgsCoordinateTransform(kanwa.mapSettings().destinationCrs(),
                                    self.lyr.crs(), QgsProject.instance())
        try:
            pt = tr.transform(pt)
        except Exception:
            return None
        g = QgsGeometry.fromPointXY(pt)
        zapytanie = QgsFeatureRequest().setFilterRect(
            QgsRectangle(pt.x(), pt.y(), pt.x(), pt.y()))
        for f in self.lyr.getFeatures(zapytanie):
            if f.hasGeometry() and f.geometry().contains(g):
                return _txt(f['ADR_LES'])
        return None

    def _tresc_podgladu(self, adr):
        """HTML okienka podglądu: adres, rodzaj pow., TSL, warstwa główna
        (DRZEW albo ZADRZEW) z gatunkami na udziale + domieszki MJS/PJD
        (PJD na czerwono), pod spodem jeden wiersz na każdą inną warstwę."""
        naglowek = f'<b>{rozbij_adres(adr) or adr}</b>'
        if adr not in self.wydz:
            return naglowek + '<br><i>brak opisu w bazie</i>'
        aint = self.wydz[adr]
        cur = self.baza.cur
        sub = cur.execute('select AREA_TYPE_CD, SITE_TYPE_CD from F_SUBAREA '
                          'where ARODES_INT_NUM = ?', (aint,)).fetchone()
        warstwy = [(_txt(r[0]), r[1], r[2]) for r in cur.execute(
            'select STOREY_CD, DENSITY_CD, STANDDENSITY_INDEX from '
            'F_AROD_STOREY where ARODES_INT_NUM = ? order by '
            'STOREY_RANK_ORDER', (aint,)).fetchall()]
        gatunki = {}
        for g in cur.execute(
                'select STOREY_CD, SPECIES_CD, PART_CD, SPECIES_AGE from '
                'F_STOREY_SPECIES where ARODES_INT_NUM = ? order by '
                'SPECIES_RANK_ORDER', (aint,)).fetchall():
            gatunki.setdefault(_txt(g[0]), []).append(
                (_txt(g[1]), _txt(g[2]), g[3]))
        kody = [w[0] for w in warstwy]
        glowna = 'DRZEW' if 'DRZEW' in kody else \
            'ZADRZEW' if 'ZADRZEW' in kody else None

        linie = [naglowek]
        if sub:
            linie.append(f'Rodz. pow.: <b>{_txt(sub[0])}</b> &nbsp; '
                         f'TSL: <b>{_txt(sub[1])}</b>')
        tabela = ''
        if glowna is None:
            linie.append('<i>brak warstwy DRZEW / ZADRZEW</i>')
        else:
            w = next(x for x in warstwy if x[0] == glowna)
            linie.append(f'{glowna}: zwarcie <b>{_txt(w[1]) or "-"}</b> '
                         f'&nbsp; zadrz. <b>{_fmt(w[2], 2) or "-"}</b>')
            gat = gatunki.get(glowna, [])
            na_udziale = [g for g in gat if g[1].isdigit()] if \
                glowna == 'DRZEW' else gat
            wiersze = ''.join(
                f'<tr><td>{g[0]}</td><td>{g[1]}</td>'
                f'<td align="right">{_fmt(g[2], 0)}</td></tr>'
                for g in na_udziale[:15])
            if len(na_udziale) > 15:
                wiersze += (f'<tr><td colspan="3">+{len(na_udziale) - 15} '
                            'dalszych</td></tr>')
            domieszki = []
            mjs = sum(1 for g in gat if g[1] == 'MJS')
            pjd = sum(1 for g in gat if g[1] == 'PJD')
            if mjs:
                domieszki.append(f'+{mjs} inne MJS')
            if pjd:
                domieszki.append(f'+{pjd} inne PJD')
            if domieszki:
                wiersze += (f'<tr><td colspan="3"><i>{", ".join(domieszki)}'
                            '</i></td></tr>')
            tabela = (
                '<table cellspacing="0" cellpadding="1" style="margin-top:3px">'
                '<tr><th align="left">Kod&nbsp;</th><th align="left">Udział'
                '&nbsp;</th><th align="right">Wiek</th></tr>' + wiersze +
                '</table>')

        inne = ''
        for kod, _zw, zd in warstwy:
            if kod == glowna:
                continue
            gat = gatunki.get(kod, [])
            na_udziale = [g for g in gat if g[1].isdigit()] or \
                [g for g in gat if not g[1]]
            pokazane = na_udziale[:4]
            reszta = len(gat) - len(pokazane)
            tekst = ', '.join(g[0] for g in pokazane)
            if reszta > 0:
                tekst += f' + {reszta} inne'
            inne += (f'<tr><td><b>{kod}</b>&nbsp;</td>'
                     f'<td>{_fmt(zd, 2)}&nbsp;</td><td>{tekst}</td></tr>')
        if inne:
            inne = ('<table cellspacing="0" cellpadding="1" '
                    'style="margin-top:4px">' + inne + '</table>')
        return '<br>'.join(linie) + tabela + inne

    def _pokaz_podglad(self, pos):
        adr = self._wydzielenie_pod(pos)
        if adr is None:
            return
        try:
            tresc = self._tresc_podgladu(adr)
        except Exception as e:
            tresc = f'<b>{adr}</b><br><i>błąd odczytu: {e}</i>'
        if self._podglad is None or sip.isdeleted(self._podglad):
            self._podglad = QLabel(None, Qt.ToolTip)
            self._podglad.setTextFormat(Qt.RichText)
            self._podglad.setMargin(6)
            self._podglad.setStyleSheet(
                'QLabel { background: #fffdf0; color: #1a1a1a; '
                'border: 1px solid #8a8a8a; }')
        self._podglad.setText(tresc)
        self._podglad.adjustSize()
        punkt = QCursor.pos() + QPoint(18, 12)
        ekran = QApplication.desktop().availableGeometry(punkt)
        punkt.setX(min(punkt.x(), ekran.right() - self._podglad.width()))
        punkt.setY(min(punkt.y(), ekran.bottom() - self._podglad.height()))
        self._podglad.move(punkt)
        self._podglad.show()

    def _schowaj_podglad(self):
        if self._podglad is not None and not sip.isdeleted(self._podglad):
            self._podglad.hide()

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
        self._timer_zgodnosci.stop()
        if self.lyr is not None and not sip.isdeleted(self.lyr):
            try:
                self.lyr.selectionChanged.disconnect(self._zaznaczenie)
            except (TypeError, RuntimeError):
                pass
            for sygnal in self._sygnaly_warstwy():
                try:
                    sygnal.disconnect(self._zmiana_warstwy)
                except (TypeError, RuntimeError):
                    pass
        self._usun_warstwe_bez_opisu()
        if self.btn_podglad.isChecked():
            self.btn_podglad.setChecked(False)
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
        """Przeliczenie zgodności (i warstwy "WYDZ bez opisu") na żądanie."""
        self.przelicz_zgodnosc()
        if not self._szczegoly:
            QMessageBox.information(self, 'Zgodność warstwy z bazą',
                                    'Warstwa i baza są zgodne.')
            return
        podsum, _, szczegoly = self._szczegoly.partition('\n\n')
        okno_zgodnosci(self, podsum, szczegoly, False)

    # ------------------------------------------------------- zamknięcie

    def closeEvent(self, event):
        """Zamknięcie panelu = rozłączenie bazy (i zamknięcie karty)."""
        if self.polaczona() and not self.rozlacz():
            event.ignore()
            return
        event.accept()

    def zadokuj(self):
        """Dołożenie na dół lewej kolumny paneli - bez dzielenia/wyciągania
        innych paneli (Layers, Browser, ich zakładek). Wołane raz, przy
        starcie wtyczki (panel ukryty) - dzięki temu QGIS odtwarza panel w
        zapamiętanym miejscu i nie zostawia pustego miejsca w układzie."""
        self.iface.mainWindow().addDockWidget(Qt.LeftDockWidgetArea, self)
        self.hide()

    def pokaz(self):
        """Pokazanie panelu z menu: zadokowany panel jest za każdym razem
        wkładany na nowo na dół lewej kolumny (nie trafi w martwe miejsce
        odtworzonego układu), pływający zostaje tam, gdzie jest. Wysokość
        tylko taka, jakiej potrzebuje zawartość."""
        okno = self.iface.mainWindow()
        if not self.isFloating():
            okno.removeDockWidget(self)
            okno.addDockWidget(Qt.LeftDockWidgetArea, self)
        self.show()
        self.raise_()
        QTimer.singleShot(0, self._dopasuj_wysokosc)

    def _dopasuj_wysokosc(self):
        if sip.isdeleted(self) or self.isFloating() or not self.isVisible():
            return
        h = self.widget().sizeHint().height() + 30
        self.iface.mainWindow().resizeDocks([self], [h], Qt.Vertical)

    def sprzataj(self):
        """Przy wyładowaniu wtyczki."""
        self.rozlacz(wymus=True)
        try:
            QgsProject.instance().layerWillBeRemoved.disconnect(
                self._usuwana_warstwa)
        except (TypeError, RuntimeError):
            pass
