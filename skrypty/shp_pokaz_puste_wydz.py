"""Pokaż puste wydzielenia - wydzielenia warstwy bez rodzaju powierzchni w
bazie.

Dla każdego poligonu warstwy wydzieleń (pole ADR_LES) sprawdza opis w bazie
(tylko F_ARODES.ARODES_TYP_CD = 'WYDZIEL'):
- BRAK OPISU W BAZIE - ADR_LES nie ma w F_ARODES (osobna warstwa pamięci,
  ta sama co w Edytorze opisu: "WYDZ bez opisu w bazie"),
- PUSTY OPIS W BAZIE - rekord w F_ARODES jest, ale brak rekordu F_SUBAREA
  albo F_SUBAREA bez rodzaju powierzchni (AREA_TYPE_CD pusty) - warstwa
  pamięci "WYDZ z pustym opisem".
Raport TXT i plik waypointów (Nawigator błędów) zapisywane obok bazy.

Wywołanie:
- z menu Narzędziowe (okienko: warstwa, domyślnie WYDZ z TOC + baza,
  domyślnie baza główna katalog wyżej),
- z panelu Edytora opisu (podłączona baza i wybrana warstwa, bez okienka).
Skrypt tylko czyta bazę.
"""
import glob
import os
import platform
from datetime import datetime

from PyQt5 import sip
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout,
)
from qgis.core import (
    Qgis, QgsFeature, QgsField, QgsFillSymbol, QgsGeometry, QgsMapLayerProxyModel,
    QgsProject, QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox

from . import waypointy
from .baza_wrapper import Baza, baza_zajeta

TYTUL = 'Pokaż puste wydzielenia'
ZRODLO_WP = 'Puste wydzielenia'

# nazwa jak w Edytorze opisu (opis_taksacyjny.NAZWA_BEZ_OPISU) - w trybie
# panelu tę warstwę prowadzi sam panel
NAZWA_BEZ_OPISU = 'WYDZ bez opisu w bazie'
NAZWA_PUSTY_OPIS = 'WYDZ z pustym opisem'

BRAK_OPISU = 'brak opisu w bazie'
BRAK_SUBAREA = 'brak F_SUBAREA'
BRAK_RODZAJU = 'brak rodzaju pow.'

SEKCJA_BRAK_OPISU = 'Brak opisu w bazie'
SEKCJA_PUSTY_OPIS = 'Pusty opis w bazie'

SQL_OPISY = """
    select A.ADRESS_FOREST, S.ARODES_INT_NUM, S.AREA_TYPE_CD
    from F_ARODES as A left join F_SUBAREA as S
        on A.ARODES_INT_NUM = S.ARODES_INT_NUM
    where A.ARODES_TYP_CD = 'WYDZIEL';
"""


def _txt(v):
    if v is None or str(v).strip() in ('', 'NULL', 'None'):
        return ''
    return str(v).strip()


def rozbij_adres(adr):
    """'0001    10    1-d' z adresu leśnego UPUL (jak w Edytorze opisu)."""
    if not adr or len(adr) < 22:
        return ''
    return (f'{adr[6:10].strip()}    {adr[11:13].strip()}    '
            f'{adr[13:17].strip()}-{adr[18:22].strip()}')


# -------------------------------------------------------------------- rdzeń

def opisy_z_bazy(cur):
    """{ADR_LES: przyczyna pustego opisu albo ''} dla wydzieleń bazy.
    Wydzielenie z kilkoma F_SUBAREA jest puste tylko, gdy żaden nie ma
    rodzaju powierzchni."""
    typy = {}
    for adr, sub_int, typ in cur.execute(SQL_OPISY).fetchall():
        adr = _txt(adr)
        if not adr:
            continue
        typy.setdefault(adr, [])
        # left join: brak F_SUBAREA -> S.ARODES_INT_NUM null (sam pusty
        # AREA_TYPE_CD tego nie odróżnia)
        if sub_int is not None:
            typy[adr].append(_txt(typ))
    wyn = {}
    for adr, lista in typy.items():
        if not lista:
            wyn[adr] = BRAK_SUBAREA
        elif not any(lista):
            wyn[adr] = BRAK_RODZAJU
        else:
            wyn[adr] = ''
    return wyn


def znajdz_puste(lyr, cur):
    """Porównanie warstwy z bazą. Zwraca słownik:
    'bez_opisu' / 'pusty_opis': [(ADR_LES, przyczyna, [geometrie])],
    'pusty_bez_poligonu': [(ADR_LES, przyczyna)] - puste opisy bazy, których
    nie ma na warstwie, 'pusty_adr': liczba poligonów z pustym ADR_LES,
    'wydz_warstwa' / 'wydz_baza': liczby wydzieleń."""
    opisy = opisy_z_bazy(cur)
    geom = {}
    pusty_adr = 0
    for f in lyr.getFeatures():
        adr = _txt(f['ADR_LES'])
        if not adr:
            pusty_adr += 1
            continue
        lista = geom.setdefault(adr, [])
        if f.hasGeometry():
            g = QgsGeometry(f.geometry())
            g.convertToMultiType()
            lista.append(g)

    bez_opisu, pusty_opis = [], []
    for adr in sorted(geom):
        if adr not in opisy:
            bez_opisu.append((adr, BRAK_OPISU, geom[adr]))
        elif opisy[adr]:
            pusty_opis.append((adr, opisy[adr], geom[adr]))
    pusty_bez_poligonu = sorted(
        (adr, prz) for adr, prz in opisy.items() if prz and adr not in geom)
    return {
        'bez_opisu': bez_opisu,
        'pusty_opis': pusty_opis,
        'pusty_bez_poligonu': pusty_bez_poligonu,
        'pusty_adr': pusty_adr,
        'wydz_warstwa': len(geom),
        'wydz_baza': len(opisy),
    }


# ----------------------------------------------------------- warstwy pamięci

def _warstwa_pamieci(nazwa, crs, styl, poprzednia=None):
    """Świeża warstwa pamięci - poprzednia o tej nazwie (albo wskazana)
    usuwana z projektu, żeby kolejne uruchomienie nie dokładało warstw."""
    prj = QgsProject.instance()
    do_usuniecia = [x.id() for x in prj.mapLayersByName(nazwa)]
    if poprzednia is not None and not sip.isdeleted(poprzednia) and \
            prj.mapLayer(poprzednia.id()) is not None:
        do_usuniecia.append(poprzednia.id())
    if do_usuniecia:
        prj.removeMapLayers(list(set(do_usuniecia)))
    lyr = QgsVectorLayer(f'MultiPolygon?crs={crs.authid()}', nazwa, 'memory')
    lyr.dataProvider().addAttributes([
        QgsField('ADR_LES', QVariant.String, '', 25),
        QgsField('ADRES', QVariant.String, '', 30),
        QgsField('PRZYCZYNA', QVariant.String, '', 30),
    ])
    lyr.updateFields()
    lyr.renderer().setSymbol(QgsFillSymbol.createSimple(styl))
    return lyr


def _wypelnij(lyr, lista):
    obiekty = []
    for adr, prz, geometrie in lista:
        for g in geometrie:
            nf = QgsFeature(lyr.fields())
            nf.setGeometry(g)
            nf['ADR_LES'] = adr
            nf['ADRES'] = rozbij_adres(adr)
            nf['PRZYCZYNA'] = prz
            obiekty.append(nf)
    lyr.dataProvider().addFeatures(obiekty)
    lyr.updateExtents()
    QgsProject.instance().addMapLayer(lyr)


def warstwa_pusty_opis(wynik, crs):
    lyr = _warstwa_pamieci(NAZWA_PUSTY_OPIS, crs, {
        'color': '255,140,0,70', 'style': 'f_diagonal',
        'outline_color': '255,140,0,255', 'outline_width': '0.8'})
    _wypelnij(lyr, wynik['pusty_opis'])
    return lyr


def warstwa_bez_opisu(wynik, crs):
    """Tylko tryb menu - w trybie panelu tę warstwę prowadzi Edytor (styl
    jak w opis_taksacyjny.odswiez_bez_opisu)."""
    lyr = _warstwa_pamieci(NAZWA_BEZ_OPISU, crs, {
        'color': '230,0,0,60', 'style': 'b_diagonal',
        'outline_color': '230,0,0,255', 'outline_width': '0.8'})
    _wypelnij(lyr, wynik['bez_opisu'])
    return lyr


# ------------------------------------------------------ raport i waypointy

def zbierz_waypointy(wynik):
    """Wiersze waypointów (Nawigator błędów, klucz ADR_LES) - sekcje
    "Brak opisu w bazie" i "Pusty opis w bazie"."""
    wiersze = []
    for sekcja, lista in ((SEKCJA_BRAK_OPISU, wynik['bez_opisu']),
                          (SEKCJA_PUSTY_OPIS, wynik['pusty_opis'])):
        for adr, prz, _g in lista:
            wiersze.append(waypointy.wiersz(
                ZRODLO_WP, sekcja, 'ADR_LES', adr,
                f'{rozbij_adres(adr)} - {prz}'))
    return wiersze


def podsumowanie(wynik):
    n_subarea = sum(1 for x in wynik['pusty_opis'] if x[1] == BRAK_SUBAREA)
    n_rodzaj = len(wynik['pusty_opis']) - n_subarea
    wiersze = [
        f'Warstwa: {wynik["wydz_warstwa"]} wydzieleń, '
        f'baza: {wynik["wydz_baza"]}.',
        f'Brak opisu w bazie (brak F_ARODES): {len(wynik["bez_opisu"])}',
        f'Pusty opis w bazie: {len(wynik["pusty_opis"])}',
        f'   - {BRAK_SUBAREA}: {n_subarea}',
        f'   - {BRAK_RODZAJU} (AREA_TYPE_CD): {n_rodzaj}',
    ]
    if wynik['pusty_bez_poligonu']:
        wiersze.append('Puste opisy w bazie bez poligonu na warstwie: '
                       f'{len(wynik["pusty_bez_poligonu"])}')
    if wynik['pusty_adr']:
        wiersze.append(f'Poligony z pustym ADR_LES: {wynik["pusty_adr"]}')
    return '\n'.join(wiersze)


def zapisz_raport(baza_sc, lyr, wynik):
    """Raport TXT + waypointy CSV obok bazy. Zwraca (raport, waypointy albo
    None)."""
    kat = os.path.dirname(baza_sc)
    nazwa = os.path.splitext(os.path.basename(baza_sc))[0]
    czas = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    rap_sc = os.path.join(kat, f'puste_wydzielenia_{nazwa}_{czas}.txt')
    lp, l = '=' * 72, '-' * 72
    with open(rap_sc, 'w', encoding='utf-8') as p:
        p.write(f'{TYTUL.upper()}\n{lp}\n')
        p.write(f'Data:    {datetime.now():%Y-%m-%d %H:%M:%S}\n')
        p.write(f'Baza:    {baza_sc}\n')
        p.write(f'Warstwa: {lyr.name()} '
                f'({lyr.dataProvider().dataSourceUri().split("|")[0]})\n')
        p.write(f'{lp}\n{podsumowanie(wynik)}\n')
        for tytul, lista in (
                ('BRAK OPISU W BAZIE (ADR_LES nie ma w F_ARODES)',
                 [(a, pr) for a, pr, _g in wynik['bez_opisu']]),
                ('PUSTY OPIS W BAZIE (brak rodzaju powierzchni)',
                 [(a, pr) for a, pr, _g in wynik['pusty_opis']]),
                ('PUSTE OPISY W BAZIE BEZ POLIGONU NA WARSTWIE',
                 wynik['pusty_bez_poligonu'])):
            if not lista:
                continue
            p.write(f'\n{l}\n{tytul} ({len(lista)})\n{l}\n')
            for adr, prz in lista:
                p.write(f'  {adr}\t{rozbij_adres(adr)}\t{prz}\n')

    wp_sc = None
    wiersze = zbierz_waypointy(wynik)
    if wiersze:
        wp_sc = os.path.join(
            kat, f'puste_wydzielenia_waypointy_{nazwa}_{czas}.csv')
        waypointy.zapisz(wp_sc, wiersze)
    return rap_sc, wp_sc


# ------------------------------------------------------------------ przebieg

def uruchom(iface, lyr, cur, baza_sc, warstwa_bez_opisu_tez=True,
            parent=None):
    """Kontrola + warstwy + raport. warstwa_bez_opisu_tez=False w trybie
    panelu (warstwę "bez opisu" prowadzi Edytor). Zwraca ścieżkę pliku
    waypointów albo None."""
    wynik = znajdz_puste(lyr, cur)
    warstwa_pusty_opis(wynik, lyr.crs())
    if warstwa_bez_opisu_tez:
        warstwa_bez_opisu(wynik, lyr.crs())
    rap_sc, wp_sc = zapisz_raport(baza_sc, lyr, wynik)

    ile = len(wynik['bez_opisu']) + len(wynik['pusty_opis'])
    iface.messageBar().pushMessage(
        TYTUL, f'Pustych wydzieleń: {ile}. Raport: {rap_sc}',
        Qgis.Success if ile == 0 else Qgis.Warning, 10)
    msg = QMessageBox(parent or iface.mainWindow())
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(TYTUL)
    msg.setText(podsumowanie(wynik) + '\n\nPokazać raport?')
    nie = msg.addButton('Nie', QMessageBox.RejectRole)
    msg.addButton('Tak', QMessageBox.AcceptRole)
    msg.exec_()
    if msg.clickedButton() is not nie and platform.system()[:3] == 'Win':
        os.startfile(rap_sc)
    return wp_sc


def uruchom_z_panelu(panel):
    """Przycisk w Edytorze opisu: podłączona baza i wybrana warstwa."""
    if not panel.polaczona() or sip.isdeleted(panel.lyr):
        return None
    try:
        wp_sc = uruchom(panel.iface, panel.lyr, panel.baza.cur,
                        panel.baza_sc, warstwa_bez_opisu_tez=False,
                        parent=panel)
    except Exception as e:
        QMessageBox.critical(panel, TYTUL, f'Błąd kontroli:\n{e}')
        return None
    panel.odswiez_bez_opisu()
    return wp_sc


# -------------------------------------------------------------- tryb menu

def baza_glowna(lyr):
    """Jedyna baza .mdb katalog wyżej niż pliki warstwy (jak
    znajdz_baze_do_wydz z poz=1) albo ''."""
    if lyr is None:
        return ''
    sc = lyr.dataProvider().dataSourceUri().split('|')[0]
    if not os.path.isfile(sc):
        return ''
    bazy = glob.glob(os.path.join(os.path.dirname(sc), '..', '*.mdb'))
    return os.path.normpath(bazy[0]) if len(bazy) == 1 else ''


class OknoPustychWydz(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle(TYTUL)
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel('Warstwa wydzieleń (pole ADR_LES):'))
        self.cbo = QgsMapLayerComboBox()
        self.cbo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        wydz = [x for x in QgsProject.instance().mapLayersByName('WYDZ')
                if isinstance(x, QgsVectorLayer)]
        if not wydz:
            wydz = [x for x in QgsProject.instance().mapLayers().values()
                    if x.name().upper() == 'WYDZ']
        if wydz:
            self.cbo.setLayer(wydz[0])
        lay.addWidget(self.cbo)

        lay.addWidget(QLabel('Baza Taksatora:'))
        wiersz = QHBoxLayout()
        self.ed_baza = QLineEdit()
        wiersz.addWidget(self.ed_baza, 1)
        btn = QPushButton('...')
        btn.setFixedWidth(30)
        btn.clicked.connect(self._wskaz_baze)
        wiersz.addWidget(btn)
        lay.addLayout(wiersz)

        przyciski = QDialogButtonBox()
        przyciski.addButton('Uruchom', QDialogButtonBox.AcceptRole)
        przyciski.addButton('Anuluj', QDialogButtonBox.RejectRole)
        przyciski.accepted.connect(self._ok)
        przyciski.rejected.connect(self.reject)
        lay.addWidget(przyciski)

        self.cbo.layerChanged.connect(self._baza_domyslna)
        self._baza_domyslna(self.cbo.currentLayer())

    def _baza_domyslna(self, lyr):
        self.ed_baza.setText(baza_glowna(lyr))

    def _wskaz_baze(self):
        start = self.ed_baza.text()
        if not start:
            lyr = self.cbo.currentLayer()
            sc = lyr.dataProvider().dataSourceUri().split('|')[0] \
                if lyr else ''
            if os.path.isfile(sc):
                start = os.path.dirname(os.path.dirname(sc))
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę Taksatora', start, 'Access MDB (*.mdb)')
        if sc:
            self.ed_baza.setText(os.path.normpath(sc))

    def _ok(self):
        lyr = self.cbo.currentLayer()
        if lyr is None:
            QMessageBox.warning(self, TYTUL, 'Wybierz warstwę wydzieleń.')
            return
        if 'ADR_LES' not in lyr.fields().names():
            QMessageBox.warning(self, TYTUL,
                                f'Warstwa "{lyr.name()}" nie ma pola ADR_LES.')
            return
        if not os.path.isfile(self.ed_baza.text()):
            QMessageBox.warning(self, TYTUL, 'Wskaż istniejący plik bazy.')
            return
        self.accept()


def pokaz_puste_wydzielenia(iface):
    """Wywołanie z menu Narzędziowe. Zwraca ścieżkę pliku waypointów albo
    None."""
    dlg = OknoPustychWydz(iface)
    if dlg.exec_() != QDialog.Accepted:
        return None
    lyr, baza_sc = dlg.cbo.currentLayer(), dlg.ed_baza.text()
    # skrypt tylko czyta - bazę podłączoną do Edytora opisu też można
    # sprawdzić (blokada chroni przed zapisem z dwóch miejsc naraz)
    baza = Baza(baza_sc, pomin_blokade=baza_zajeta(baza_sc))
    try:
        if not baza.polacz():
            QMessageBox.critical(iface.mainWindow(), TYTUL,
                                 'Nie udało się połączyć z bazą.')
            return None
        return uruchom(iface, lyr, baza.cur, baza_sc)
    except Exception as e:
        QMessageBox.critical(iface.mainWindow(), TYTUL,
                             f'Błąd kontroli:\n{e}')
        return None
    finally:
        baza.zamknij()
