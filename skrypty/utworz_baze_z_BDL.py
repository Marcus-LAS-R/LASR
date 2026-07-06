import os
import re
import datetime

import openpyxl

from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QMessageBox
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsProject,
)

from .baza_wrapper import Baza
from .baza_dopisz_wydz import DopiszWydzielenia
from .ui.ui_utworz_baze_z_BDL import Ui_Dialog

# litera wojewodztwa (COUNTY_L, pierwszy znak ADR_LES) -> 2-cyfrowy kod
# TERYT (COUNTY) - ta sama tablica co w baza_dopisz_wydz.DopiszWydzielenia,
# zduplikowana tutaj (mala prywatna stala, zgodnie z konwencja projektu
# zamiast importu w poprzek modulow po jeden slownik)
_SL_WOJ = {
    "D": "02", "C": "04", "L": "06", "F": "08", "E": "10", "K": "12",
    "W": "14", "O": "16", "R": "18", "B": "20", "G": "22", "S": "24",
    "T": "26", "N": "28", "P": "30", "Z": "32",
}

_WYMAGANE_TABELE = [
    'F_ARODES', 'F_SUBAREA', 'F_AROD_STOREY', 'F_STOREY_SPECIES',
    'F_AROD_STAND_PEC', 'F_COMMUNITY',
]

_WYMAGANE_XLSX = [
    'generalData.xlsx', 'generalData2.xlsx', 'layer.xlsx', 'layerSpecies.xlsx',
]

# warstwa OBR bywa albo juz przetworzona (pola MUNICIP/COMMUNITY wprost),
# albo surowa PZGiK/EGiB czy PRG/GUGiK - wtedy trzeba MUNICIP/COMMUNITY
# rozbic ze zlozonego kodu jednostki, ktory bywa pod jedna z tych nazw pol
# (dopasowanie bez wzgledu na wielkosc liter, jak w shp_przygCiecie.py)
_KANDYDACI_KOD_OBR = ('idobrebu', 'jpt_kod_je', 'g5nro')
# kandydaci na pole z nazwa obrebu - sprawdzane w tej kolejnosci, pierwsze
# niepuste wygrywa (nawet jesli wyglada jak powtorzenie kodu - w miastach
# to normalny, prawdziwy zapis)
_KANDYDACI_NAZWA_OBR = ('g5naz', 'jpt_nazwa_', 'nazwawlasn')
# format zlozonego kodu jednostki: WOJ(2)POW(2)GMI(2)_RODZ(1).OBREB(4),
# np. "320101_1.0002" (Pekanino: MUNICIP=022 [gmina 02 + rodzaj 2],
# COMMUNITY=0021)
_WZORZEC_KOD_OBR = re.compile(r'^(\d{2})(\d{2})(\d{2})_(\d)\.(\d{4})$')


# ---------------------------------------------------------------------
# czyszczenie / konwersja wartosci
# ---------------------------------------------------------------------

def _wyczysc_kod(wartosc):
    """ BDL zwraca pola kodowe jako "KOD:opis" (albo sam ":" gdy puste) -
    zostaje tylko czesc przed pierwszym dwukropkiem. """
    if wartosc is None:
        return None
    tekst = str(wartosc)
    if ':' in tekst:
        tekst = tekst.split(':', 1)[0]
    tekst = tekst.strip()
    return tekst or None


def _do_liczby(wartosc):
    """ BDL zwraca liczby w polskim formacie (przecinek) - "5,74" -> 5.74. """
    if wartosc in (None, ''):
        return None
    try:
        return float(str(wartosc).replace(',', '.'))
    except ValueError:
        return None


def _do_int(wartosc):
    liczba = _do_liczby(wartosc)
    return int(liczba) if liczba is not None else None


def _klucz_aint(wartosc):
    try:
        return int(wartosc)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------
# odczyt XLSX (openpyxl - nie pandas, jak w reszcie wtyczki)
# ---------------------------------------------------------------------

def _wczytaj_xlsx(sciezka):
    """ Zwraca liste dict {naglowek: wartosc} - pierwszy wiersz arkusza to
    naglowki. Pusta lista, jesli plik nie istnieje. """
    if not os.path.isfile(sciezka):
        return []
    wb = openpyxl.load_workbook(sciezka, read_only=True, data_only=True)
    ws = wb.active
    wiersze = ws.iter_rows(values_only=True)
    naglowki = next(wiersze, None)
    if not naglowki:
        return []
    return [dict(zip(naglowki, wiersz)) for wiersz in wiersze]


def _zbuduj_slownik_po_aint(wiersze):
    """ {aint: [wiersz, ...]} - grupuje wiersze o tym samym 'aint' (moze
    byc 1:N, np. layerSpecies ma wiele gatunkow na wydzielenie). """
    sl = {}
    for w in wiersze:
        aint = _klucz_aint(w.get('aint'))
        if aint is None:
            continue
        sl.setdefault(aint, []).append(w)
    return sl


# ---------------------------------------------------------------------
# rozbior ADR_LES (format jak w shp_adr_les.py/shp_doliterkuj.py)
# ---------------------------------------------------------------------

def _rozbierz_adr_les(adr):
    """ 25-znakowy adres lesny -> dict z COUNTY_L/COUNTY/DISTRICT/MUNICIP/
    COMMUNITY/GRP/ODDZ/WYDZ, albo None jesli adres ma zla dlugosc. COUNTY
    (2-cyfrowy kod TERYT wojewodztwa) wyliczany przez _SL_WOJ z COUNTY_L
    (litera) - nie jest fizycznie czescia samego ADR_LES. """
    if not adr or len(adr) != 25:
        return None
    county_l = adr[0:1]
    return {
        'county_l': county_l,
        'county': _SL_WOJ.get(county_l),
        'district': adr[1:3],
        'municip': adr[3:6],
        'community': adr[6:10],
        'grp': adr[11:13].strip(),
        'oddz': adr[13:17].strip(),
        'wydz': adr[18:22].strip(),
    }


# ---------------------------------------------------------------------
# budowa list do dialogu
# ---------------------------------------------------------------------

def _zbuduj_liste_wlasnosci(cechy):
    """ Posortowana lista unikalnych wartosci owner_cat_ wystepujacych w
    warstwie (pomija puste, przycina spacje z pol o stalej szerokosci). """
    wartosci = {
        str(f['owner_cat_']).strip()
        for f in cechy
        if f['owner_cat_'] not in (None, '') and str(f['owner_cat_']).strip()
    }
    return sorted(wartosci)


def _rozbij_kod_obr(kod):
    """ Rozbija zlozony kod jednostki ewidencyjnej/obrebu (pola typu
    IDOBREBU/jpt_kod_je/g5nro), format "WOJPOWGMI_RODZ.OBREB" np.
    "320101_1.0002" (PZGiK/EGiB, PRG/GUGiK), na (municip, community) w tej
    samej konwencji co ADR_LES: MUNICIP = GMI+RODZ (3 znaki), COMMUNITY =
    OBREB (4 znaki). Zwraca None, jesli kod nie pasuje do wzorca. """
    if not kod:
        return None
    dopasowanie = _WZORZEC_KOD_OBR.match(kod.strip())
    if not dopasowanie:
        return None
    _woj, _pow, gmi, rodz, obreb = dopasowanie.groups()
    return gmi + rodz, obreb


def _wczytaj_nazwy_obr(sciezka):
    """ Wczytuje warstwe OBR i buduje {(MUNICIP, COMMUNITY): nazwa}.
    Obsluguje dwa warianty spotykane w tym projekcie:
    1. juz przetworzona - pola MUNICIP/COMMUNITY wprost, nazwa w G5NAZ
       albo jpt_nazwa_ (jak w raport_wyles.py)
    2. surowa PZGiK/EGiB albo PRG/GUGiK - MUNICIP/COMMUNITY trzeba
       rozbic ze zlozonego kodu (IDOBREBU/jpt_kod_je/g5nro, patrz
       _rozbij_kod_obr)
    Nazwa brana jest wprost z pierwszego niepustego pola-kandydata - nawet
    jesli wyglada jak powtorzenie kodu jednostki (w miastach to normalny,
    prawdziwy zapis, nie blad danych). Zwraca (slownik, blad) - blad to
    czytelny komunikat gdy nie udalo sie znalezc potrzebnych pol w zadnym
    z dwoch wariantow, inaczej None. """
    if not sciezka or not os.path.isfile(sciezka):
        return {}, 'Nie wskazano warstwy OBR'
    warstwa = QgsVectorLayer(sciezka, 'obr', 'ogr')
    if not warstwa.isValid():
        return {}, 'Nie można wczytać wskazanej warstwy OBR'

    nazwy_pol = {f.name().lower(): f.name() for f in warstwa.fields()}
    ma_municip_community = 'municip' in nazwy_pol and 'community' in nazwy_pol
    pole_kod = next(
        (nazwy_pol[k] for k in _KANDYDACI_KOD_OBR if k in nazwy_pol), None)
    if not ma_municip_community and pole_kod is None:
        return {}, (
            'Warstwa OBR musi mieć pola MUNICIP i COMMUNITY albo pole '
            'z kodem jednostki (IDOBREBU/jpt_kod_je/g5nro)')

    pola_nazwy = [
        nazwy_pol[k] for k in _KANDYDACI_NAZWA_OBR if k in nazwy_pol]

    slownik = {}
    for f in warstwa.getFeatures():
        if ma_municip_community:
            municip = str(f[nazwy_pol['municip']]).strip()
            community = str(f[nazwy_pol['community']]).strip()
        else:
            kod = f[pole_kod]
            kod = str(kod).strip() if kod is not None else ''
            rozbite = _rozbij_kod_obr(kod)
            if rozbite is None:
                continue
            municip, community = rozbite

        nazwa = ''
        for pole in pola_nazwy:
            kandydat = f[pole]
            kandydat = str(kandydat).strip() if kandydat is not None else ''
            if kandydat:
                nazwa = kandydat
                break

        slownik[(municip, community)] = nazwa
    return slownik, None


def _zbuduj_liste_obrebow(cechy, nazwy_obr):
    """ -> posortowana lista (municip, community, etykieta, w_obr). Etykieta
    zawsze pokazuje nazwe (z warstwy OBR, jesli jest - inaczej surowy kod)
    ORAZ kody MUNICIP/COMMUNITY, zeby dalo sie rozroznic obreby nawet gdy
    nazwa jest pusta dla kilku roznych obrebow naraz. w_obr mowi, czy dany
    obreb w ogole wystepuje w warstwie OBR - uzywane do domyslnego
    zaznaczenia/kolejnosci w dialogu (obecne w OBR na gorze i zaznaczone,
    brakujace nizej i odznaczone). """
    grupy = {}
    for f in cechy:
        rozbite = _rozbierz_adr_les(f['adress_for'])
        if rozbite is None:
            continue
        klucz = (rozbite['municip'], rozbite['community'])
        if klucz in grupy:
            continue
        w_obr = klucz in nazwy_obr
        nazwa = nazwy_obr.get(klucz, '')
        etykieta = (nazwa or rozbite['municip'] + '-' + rozbite['community']) + \
            ', ' + rozbite['municip'] + ', ' + rozbite['community']
        grupy[klucz] = (etykieta, w_obr)
    return sorted(
        ((m, c, e, w) for (m, c), (e, w) in grupy.items()),
        key=lambda x: (not x[3], x[2]))


# ---------------------------------------------------------------------
# budowa wierszy docelowych (BEZ korekt +10/+3/+2/*1,2 - surowe wartosci)
# ---------------------------------------------------------------------

def _zbuduj_f_subarea_wiersz(aint, gd_by_aint, gd2_by_aint):
    """ Zwraca dict gotowy do wpisania (bez ARODES_INT_NUM - dopisywany
    przez wywolujacego), albo None gdy brak wiersza w generalData
    (traktowane jako brak kompletnych danych opisowych). """
    gd_lista = gd_by_aint.get(aint)
    if not gd_lista:
        return None
    gd = gd_lista[0]
    gd2 = (gd2_by_aint.get(aint) or [{}])[0]
    return {
        'AREA_TYPE_CD': _wyczysc_kod(gd.get('area_type_cd')),
        'SITE_TYPE_CD': _wyczysc_kod(gd.get('site_type_cd')),
        'STAND_STRUCT_CD': _wyczysc_kod(gd.get('stand_struct_cd')),
        'SUB_AREA': _do_liczby(gd.get('sub_area')),
        'ROTATION_AGE': _do_int(gd.get('rotation_age')),
        'VEG_COVER_CD': _wyczysc_kod(gd2.get('veg_cover_cd')),
        'CAUSE_CD': _wyczysc_kod(gd2.get('cause_cd')),
        'DAMAGE_DEGREE_CD': _wyczysc_kod(gd2.get('damage_degree')),
    }


def _zbuduj_f_arod_storey_wiersze(aint, ls_by_aint, layer_by_aint):
    """ Jeden wiersz na kazdy unikalny storey_cd wystepujacy w layerSpecies
    dla danego wydzielenia (odpowiednik dawnej layerSpecies2 - dedup w
    pamieci zamiast osobnej tabeli). STOREY_RANK_ORDER/STANDDENSITY_INDEX/
    MIXTURE_CD/DENSITY_CD dociagane z pierwszego pasujacego wiersza layer
    o tym samym (aint, storey_cd). """
    unikalne = []
    widziane = set()
    for w in ls_by_aint.get(aint, []):
        storey = _wyczysc_kod(w.get('storey_cd'))
        if storey in widziane:
            continue
        widziane.add(storey)
        unikalne.append(storey)

    l_po_storey = {}
    for w in layer_by_aint.get(aint, []):
        storey = _wyczysc_kod(w.get('storey_cd'))
        if storey not in l_po_storey:
            l_po_storey[storey] = w

    wynik = []
    for storey in unikalne:
        wl = l_po_storey.get(storey)
        kolej = _do_int(wl.get('kolej')) if wl else None
        wynik.append({
            'STOREY_CD': storey,
            'STOREY_RANK_ORDER': kolej + 1 if kolej is not None else None,
            'STANDDENSITY_INDEX':
                _do_liczby(wl.get('standdensity_index')) if wl else None,
            'MIXTURE_CD': _wyczysc_kod(wl.get('mixture_cd')) if wl else None,
            'DENSITY_CD': _wyczysc_kod(wl.get('density_cd')) if wl else None,
        })
    return wynik


def _zbuduj_f_storey_species_wiersze(aint, ls_by_aint):
    """ Jeden wiersz na kazdy wiersz layerSpecies (kazdy gatunek) - surowe
    wartosci, BEZ korekty wieku/pierśnicy/wysokosci/miazszosci. """
    wynik = []
    for w in ls_by_aint.get(aint, []):
        kolej = _do_int(w.get('kolej'))
        objetosc = _do_liczby(w.get('volume_beg'))
        wynik.append({
            'STOREY_CD': _wyczysc_kod(w.get('storey_cd')),
            'SPECIES_RANK_ORDER': kolej + 1 if kolej is not None else None,
            'SPECIES_CD': _wyczysc_kod(w.get('species_cd')),
            'PART_CD': _wyczysc_kod(w.get('part_cd')),
            'SPECIES_AGE': _do_int(w.get('species_age')),
            'BHD': _do_int(w.get('bhd')),
            'HEIGHT': _do_int(w.get('height')),
            'VOLUME': objetosc,
            'VOLUME_TEMP': objetosc,
            'SITE_CLASS_CD': _wyczysc_kod(w.get('site_class_cd')),
        })
    return wynik


def _zbuduj_f_arod_stand_pec_wiersz():
    """ Stala wartosc - jak oryginalna kwerenda (zawsze drzewostan
    naturalny). """
    return {'FOREST_PEC_CD': 'DRZ NAT', 'PEC_RANK_ORDER': '1'}


# ---------------------------------------------------------------------
# F_COMMUNITY - slownik obrebow (w czystej bazie zwykle PUSTY, w
# odroznieniu od F_COUNTY/F_DISTRICT/F_MUNICIPALITY, ktore sa juz
# wypelnione dla calej Polski - trzeba wiec dopisac brakujace obreby,
# zeby program taksatora w ogole dal sie uruchomic na tej bazie)
# ---------------------------------------------------------------------

def _potrzebne_community(cechy, nazwy_obr):
    """ {(county, district, municip, community): community_name} dla
    podanego zbioru cech - jedna kombinacja per obreb. Nazwa z warstwy
    OBR (patrz _wczytaj_nazwy_obr), pusta jesli OBR nie ma tego obrebu. """
    wynik = {}
    for f in cechy:
        rozbite = _rozbierz_adr_les(f['adress_for'])
        if rozbite is None or not rozbite['county']:
            continue
        klucz = (
            rozbite['county'], rozbite['district'],
            rozbite['municip'], rozbite['community'],
        )
        if klucz in wynik:
            continue
        wynik[klucz] = nazwy_obr.get(
            (rozbite['municip'], rozbite['community']), '')
    return wynik


def _dopisz_brakujace_community(baza, potrzebne):
    """ Dopisuje do F_COMMUNITY tylko te kombinacje (county, district,
    municip, community), ktorych tam jeszcze nie ma - nigdy nie nadpisuje
    ani nie dubluje istniejacych wpisow (czasem baza juz je ma). Zwraca
    liczbe dopisanych wierszy. """
    istniejace = {
        (r[0], r[1], r[2], r[3])
        for r in (baza.pobierz(
            'SELECT COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD '
            'FROM F_COMMUNITY') or [])
    }
    dopisano = 0
    for klucz, nazwa in potrzebne.items():
        if klucz in istniejace:
            continue
        if baza.wpisz_tab([
            'INSERT INTO F_COMMUNITY (COUNTY_CD, DISTRICT_CD, '
            'MUNICIPALITY_CD, COMMUNITY_CD, COMMUNITY_NAME) '
            'VALUES (?,?,?,?,?)',
            (klucz[0], klucz[1], klucz[2], klucz[3], nazwa),
        ]):
            istniejace.add(klucz)
            dopisano += 1
    return dopisano


# ---------------------------------------------------------------------
# kontrola tabel w bazie docelowej
# ---------------------------------------------------------------------

def _brakujace_tabele(baza):
    brakujace = []
    for nazwa in _WYMAGANE_TABELE:
        try:
            istnieje = any(
                r.table_name.upper() == nazwa.upper()
                for r in baza.cur.tables(
                    table=nazwa, tableType='TABLE').fetchall()
            )
        except Exception:
            istnieje = False
        if not istnieje:
            brakujace.append(nazwa)
    return brakujace


# ---------------------------------------------------------------------
# zapis SHP wybrane_BDL.shp
# ---------------------------------------------------------------------

def _zapisz_wybrane_shp(cechy, folder):
    """ Zapisuje <folder>/SHP/wybrane_BDL.shp - schemat jak
    materialy/.../SHP_szablon/WYDZ.shp, EPSG:2180, UTF-8. """
    kat_shp = os.path.join(folder, 'SHP')
    if not os.path.isdir(kat_shp):
        os.makedirs(kat_shp)

    warstwa = QgsVectorLayer('Polygon?crs=EPSG:2180', 'wybrane_bdl', 'memory')
    warstwa.dataProvider().addAttributes([
        QgsField('COUNTY', QVariant.String, len=2),
        QgsField('DISTRICT', QVariant.String, len=2),
        QgsField('MUNICIP', QVariant.String, len=3),
        QgsField('COMMUNITY', QVariant.String, len=4),
        QgsField('GRP', QVariant.String, len=2),
        QgsField('COUNTY_L', QVariant.String, len=1),
        QgsField('ODDZ', QVariant.String, len=6),
        QgsField('WYDZ', QVariant.String, len=4),
        QgsField('ADR_LES', QVariant.String, len=25),
        QgsField('POW_GRAF', QVariant.Double, 'double', 10, 4),
        QgsField('EDIT', QVariant.String, len=10),
        QgsField('arodes_int', QVariant.String, len=20),
    ])
    warstwa.updateFields()

    for f in cechy:
        adr = f['adress_for']
        rozbite = _rozbierz_adr_les(adr)
        if rozbite is None:
            continue
        nowa = QgsFeature(warstwa.fields())
        nowa.setGeometry(f.geometry())
        nowa.setAttributes([
            rozbite['county'],
            rozbite['district'],
            rozbite['municip'],
            rozbite['community'],
            rozbite['grp'],
            rozbite['county_l'],
            rozbite['oddz'],
            rozbite['wydz'],
            adr,
            f.geometry().area() / 10000,
            '',
            str(f['arodes_int']),
        ])
        warstwa.dataProvider().addFeature(nowa)

    warstwa.updateExtents()
    sciezka = os.path.join(kat_shp, 'wybrane_BDL.shp')
    QgsVectorFileWriter.writeAsVectorFormat(
        warstwa, sciezka, 'UTF-8',
        QgsCoordinateReferenceSystem('EPSG:2180'), 'ESRI Shapefile')
    return sciezka


# ---------------------------------------------------------------------
# dialog
# ---------------------------------------------------------------------

def _folder_ma_dane(folder):
    if not folder or not os.path.isdir(folder):
        return False
    if not os.path.isfile(os.path.join(folder, 'SHP', 'wszystko_BDL.shp')):
        return False
    return all(
        os.path.isfile(os.path.join(folder, nazwa))
        for nazwa in _WYMAGANE_XLSX
    )


def _znajdz_obr_w_toc():
    """ Jesli w bierzacym projekcie (TOC) jest wczytana dokladnie jedna
    warstwa o nazwie zaczynajacej sie od "OBR" (np. "OBR" albo "OBR2"),
    zwraca jej sciezke zrodlowa - do auto-uzupelnienia pola warstwy OBR w
    dialogu. Przy wiecej niz jednym kandydacie nie zgaduje (jak w
    baza_przeliterkuj.py::dopisz_oddzialy - "tylko jedna" warstwa). """
    kandydaci = [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if lyr.name().upper().startswith('OBR')
    ]
    if len(kandydaci) != 1:
        return ''
    try:
        sc = kandydaci[0].dataProvider().dataSourceUri().split('|')[0]
        return sc if sc and os.path.isfile(sc) else ''
    except Exception:
        return ''


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._cechy = []
        self._nazwy_obr = {}
        self._blad_obr = 'Nie wskazano warstwy OBR'

        obr_toc = _znajdz_obr_w_toc()
        if obr_toc:
            self.ui.lineEdit_obr.setText(obr_toc)

        self.ui.pushButton_folder.clicked.connect(self._wybierz_folder)
        self.ui.pushButton_baza.clicked.connect(self._wybierz_baze)
        self.ui.pushButton_obr.clicked.connect(self._wybierz_obr)
        self.ui.lineEdit_folder.textChanged.connect(self._na_zmiane_folderu)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj)
        self.ui.lineEdit_obr.textChanged.connect(self._na_zmiane_obr)
        self.ui.listWidget_wlasnosc.itemChanged.connect(self._aktualizuj)
        self.ui.listWidget_obreb.itemChanged.connect(self._aktualizuj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        if obr_toc:
            self._na_zmiane_obr()
        self._aktualizuj()

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder z danymi BDL',
            self.ui.lineEdit_folder.text().strip())
        if sc:
            self.ui.lineEdit_folder.setText(sc)

    def _wybierz_baze(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż czystą bazę docelową',
            os.path.dirname(self.ui.lineEdit_baza.text().strip()),
            'Access MDB (*.mdb)',
        )[0]
        if sc:
            self.ui.lineEdit_baza.setText(sc)

    def _wybierz_obr(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż warstwę OBR',
            os.path.dirname(self.ui.lineEdit_obr.text().strip()),
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_obr.setText(sc)

    def _na_zmiane_folderu(self):
        self._cechy = []

        folder = self.ui.lineEdit_folder.text().strip()
        if _folder_ma_dane(folder):
            warstwa = QgsVectorLayer(
                os.path.join(folder, 'SHP', 'wszystko_BDL.shp'),
                'wszystko_bdl', 'ogr')
            if warstwa.isValid():
                self._cechy = list(warstwa.getFeatures())

                self.ui.listWidget_wlasnosc.clear()
                for wartosc in _zbuduj_liste_wlasnosci(self._cechy):
                    item = QListWidgetItem(wartosc)
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Checked)
                    item.setData(Qt.UserRole, wartosc)
                    self.ui.listWidget_wlasnosc.addItem(item)

        self._odswiez_liste_obrebow()
        self._aktualizuj()

    def _na_zmiane_obr(self):
        self._nazwy_obr, self._blad_obr = _wczytaj_nazwy_obr(
            self.ui.lineEdit_obr.text().strip())
        self._odswiez_liste_obrebow()
        self._aktualizuj()

    def _odswiez_liste_obrebow(self):
        self.ui.listWidget_obreb.clear()
        if not self._cechy or self._blad_obr:
            return
        for municip, community, etykieta, w_obr in _zbuduj_liste_obrebow(
                self._cechy, self._nazwy_obr):
            item = QListWidgetItem(etykieta)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked if w_obr else Qt.Unchecked)
            item.setData(Qt.UserRole, (municip, community))
            self.ui.listWidget_obreb.addItem(item)

    def _ile_zaznaczonych(self, lista):
        return sum(
            1 for i in range(lista.count())
            if lista.item(i).checkState() == Qt.Checked
        )

    def _aktualizuj(self):
        ok = (
            bool(self._cechy) and
            bool(self.ui.lineEdit_baza.text().strip()) and
            self._blad_obr is None and
            self._ile_zaznaczonych(self.ui.listWidget_wlasnosc) > 0 and
            self._ile_zaznaczonych(self.ui.listWidget_obreb) > 0
        )
        self.ui.pushButton_ok.setEnabled(ok)

    def folder(self):
        return self.ui.lineEdit_folder.text().strip()

    def baza_sc(self):
        return self.ui.lineEdit_baza.text().strip()

    def obr_sc(self):
        return self.ui.lineEdit_obr.text().strip()

    def utworz_shp(self):
        return self.ui.checkBox_utworz_shp.isChecked()

    def wlasnosci_wybrane(self):
        lista = self.ui.listWidget_wlasnosc
        return {
            lista.item(i).data(Qt.UserRole)
            for i in range(lista.count())
            if lista.item(i).checkState() == Qt.Checked
        }

    def obreby_wybrane(self):
        lista = self.ui.listWidget_obreb
        return {
            lista.item(i).data(Qt.UserRole)
            for i in range(lista.count())
            if lista.item(i).checkState() == Qt.Checked
        }


def uruchom(iface):
    """ Pokazuje dialog wyboru folderu z danymi BDL, docelowej czystej
    bazy, warstwy OBR oraz filtrow (wlasnosc/obreb), po czym uruchamia
    UtworzBazeZBDL. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    return UtworzBazeZBDL(
        iface, dlg.folder(), dlg.baza_sc(), dlg.obr_sc(),
        dlg.wlasnosci_wybrane(), dlg.obreby_wybrane(), dlg.utworz_shp())


def UtworzBazeZBDL(iface, folder, baza_sc, obr_sc, wlasnosci, obreby,
                    utworz_shp):  # noqa
    """ Zamienia folder wyjsciowy pobierz_BDL.py (SHP/wszystko_BDL.shp +
    XLSX-y z opisami) w gotowe wiersze w czystej bazie Access wskazanej
    przez uzytkownika - F_ARODES (nowa hierarchia obreb/lesnictwo/oddzial/
    wydzielenie, przez baza_dopisz_wydz.DopiszWydzielenia), F_SUBAREA,
    F_AROD_STOREY, F_STOREY_SPECIES, F_AROD_STAND_PEC, oraz brakujace
    wpisy w slowniku F_COMMUNITY (w czystej bazie zwykle pusty, w
    odroznieniu od juz wypelnionych F_COUNTY/F_DISTRICT/F_MUNICIPALITY -
    bez tego program taksatora nie odpala sie na tej bazie). Nazwy
    obrebow (do etykiet w dialogu i do F_COMMUNITY.COMMUNITY_NAME) brane
    sa z warstwy OBR (obr_sc) - wymagane pola MUNICIP/COMMUNITY oraz nazwa
    (G5NAZ albo jpt_nazwa_), jak w raport_wyles.py. Bez korekty
    wieku/pierśnicy/wysokosci/miazszosci - surowe wartosci z BDL. """
    QgsMessageLog.logMessage(
        '------ UTWÓRZ BAZĘ Z BDL --------- ', 'Las-R', Qgis.Info)

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie udało się połączyć ze wskazaną bazą',
            Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    brakujace = _brakujace_tabele(baza)
    if brakujace:
        baza.zamknij()
        iface.messageBar().pushMessage(
            'BŁĄD',
            'W bazie brakuje wymaganych tabel: ' + ', '.join(brakujace),
            Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    nazwy_obr, blad_obr = _wczytaj_nazwy_obr(obr_sc)
    if blad_obr:
        baza.zamknij()
        iface.messageBar().pushMessage('BŁĄD', blad_obr, Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    sciezka_shp = os.path.join(folder, 'SHP', 'wszystko_BDL.shp')
    warstwa = QgsVectorLayer(sciezka_shp, 'wszystko_bdl', 'ogr')
    if not warstwa.isValid():
        baza.zamknij()
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie można wczytać ' + sciezka_shp, Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    cechy = list(warstwa.getFeatures())
    gd_by_aint = _zbuduj_slownik_po_aint(
        _wczytaj_xlsx(os.path.join(folder, 'generalData.xlsx')))
    gd2_by_aint = _zbuduj_slownik_po_aint(
        _wczytaj_xlsx(os.path.join(folder, 'generalData2.xlsx')))
    layer_by_aint = _zbuduj_slownik_po_aint(
        _wczytaj_xlsx(os.path.join(folder, 'layer.xlsx')))
    ls_by_aint = _zbuduj_slownik_po_aint(
        _wczytaj_xlsx(os.path.join(folder, 'layerSpecies.xlsx')))

    wybrane = []
    for f in cechy:
        if str(f['owner_cat_']).strip() not in wlasnosci:
            continue
        rozbite = _rozbierz_adr_les(f['adress_for'])
        if rozbite is None:
            continue
        if (rozbite['municip'], rozbite['community']) not in obreby:
            continue
        wybrane.append(f)

    if not wybrane:
        baza.zamknij()
        iface.messageBar().pushMessage(
            'BŁĄD', 'Brak wydzieleń spełniających wybrane filtry',
            Qgis.Warning, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    w_bazie = baza.pobierz_wydzielenia() or {}

    duplikaty = []
    do_przetworzenia = []
    for f in wybrane:
        if f['adress_for'] in w_bazie:
            duplikaty.append(f)
        else:
            do_przetworzenia.append(f)

    brak_danych = []
    do_dopisania = []
    for f in do_przetworzenia:
        aint = _klucz_aint(f['arodes_int'])
        if aint not in gd_by_aint:
            brak_danych.append(f)
        else:
            do_dopisania.append(f)

    sciezka_wybrane_shp = None
    if utworz_shp:
        sciezka_wybrane_shp = _zapisz_wybrane_shp(wybrane, folder)

    odp = QMessageBox.question(
        iface.mainWindow(),
        'Podsumowanie',
        'Do dopisania: ' + str(len(do_dopisania)) + ' wydzieleń\n'
        'Już w bazie (pominięte): ' + str(len(duplikaty)) + '\n'
        'Bez kompletnych danych opisowych (pominięte): ' +
        str(len(brak_danych)) + '\n\n'
        'Kontynuować zapis do bazy?',
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )

    bledy_zapisu = 0
    zapisano = 0
    community_dopisane = 0
    if odp == QMessageBox.Yes and do_dopisania:
        community_dopisane = _dopisz_brakujace_community(
            baza, _potrzebne_community(do_dopisania, nazwy_obr))

        warstwa_pam = QgsVectorLayer(
            'None?crs=EPSG:2180', 'do_dopisania', 'memory')
        warstwa_pam.dataProvider().addAttributes(
            [QgsField('ADR_LES', QVariant.String, len=25)])
        warstwa_pam.updateFields()
        for f in do_dopisania:
            nowa = QgsFeature(warstwa_pam.fields())
            nowa.setAttributes([f['adress_for']])
            warstwa_pam.dataProvider().addFeature(nowa)
        warstwa_pam.updateExtents()

        dw = DopiszWydzielenia(
            iface, wydz=warstwa_pam, baza=baza, wpisz_subarea=False)
        dw.wczytaj_wydz_shp()
        dw.wczytaj_wydz_baza()
        dw.dopisz_wydz()

        arod_map = baza.pobierz_wydzielenia() or {}

        for f in do_dopisania:
            adr = f['adress_for']
            nowy_int = arod_map.get(adr)
            if nowy_int is None:
                bledy_zapisu += 1
                continue
            aint = _klucz_aint(f['arodes_int'])

            subarea = _zbuduj_f_subarea_wiersz(aint, gd_by_aint, gd2_by_aint)
            if subarea is None:
                continue

            if not baza.wpisz_tab([
                'INSERT INTO F_SUBAREA (ARODES_INT_NUM, AREA_TYPE_CD, '
                'SITE_TYPE_CD, STAND_STRUCT_CD, SUB_AREA, ROTATION_AGE, '
                'VEG_COVER_CD, CAUSE_CD, DAMAGE_DEGREE_CD) '
                'VALUES (?,?,?,?,?,?,?,?,?)',
                (nowy_int, subarea['AREA_TYPE_CD'], subarea['SITE_TYPE_CD'],
                 subarea['STAND_STRUCT_CD'], subarea['SUB_AREA'],
                 subarea['ROTATION_AGE'], subarea['VEG_COVER_CD'],
                 subarea['CAUSE_CD'], subarea['DAMAGE_DEGREE_CD']),
            ]):
                bledy_zapisu += 1

            for pietro in _zbuduj_f_arod_storey_wiersze(
                    aint, ls_by_aint, layer_by_aint):
                if not baza.wpisz_tab([
                    'INSERT INTO F_AROD_STOREY (ARODES_INT_NUM, STOREY_CD, '
                    'STOREY_RANK_ORDER, STANDDENSITY_INDEX, MIXTURE_CD, '
                    'DENSITY_CD) VALUES (?,?,?,?,?,?)',
                    (nowy_int, pietro['STOREY_CD'],
                     pietro['STOREY_RANK_ORDER'],
                     pietro['STANDDENSITY_INDEX'], pietro['MIXTURE_CD'],
                     pietro['DENSITY_CD']),
                ]):
                    bledy_zapisu += 1

            for gatunek in _zbuduj_f_storey_species_wiersze(aint, ls_by_aint):
                if not baza.wpisz_tab([
                    'INSERT INTO F_STOREY_SPECIES (ARODES_INT_NUM, '
                    'STOREY_CD, SPECIES_RANK_ORDER, SPECIES_CD, PART_CD, '
                    'SPECIES_AGE, BHD, HEIGHT, VOLUME, VOLUME_TEMP, '
                    'SITE_CLASS_CD) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (nowy_int, gatunek['STOREY_CD'],
                     gatunek['SPECIES_RANK_ORDER'], gatunek['SPECIES_CD'],
                     gatunek['PART_CD'], gatunek['SPECIES_AGE'],
                     gatunek['BHD'], gatunek['HEIGHT'], gatunek['VOLUME'],
                     gatunek['VOLUME_TEMP'], gatunek['SITE_CLASS_CD']),
                ]):
                    bledy_zapisu += 1

            pec = _zbuduj_f_arod_stand_pec_wiersz()
            if not baza.wpisz_tab([
                'INSERT INTO F_AROD_STAND_PEC (FOREST_PEC_CD, '
                'ARODES_INT_NUM, PEC_RANK_ORDER) VALUES (?,?,?)',
                (pec['FOREST_PEC_CD'], nowy_int, pec['PEC_RANK_ORDER']),
            ]):
                bledy_zapisu += 1

            zapisano += 1

    czas = datetime.datetime.now().isoformat(
                    ).replace(':', '')[:-7].replace('-', '')

    wypis = (
        '---- UTWÓRZ BAZĘ Z BDL ----\n\n'
        'Folder: ' + folder + '\n'
        'Baza: ' + baza_sc + '\n\n'
        'Zapisano do bazy: ' + str(zapisano) + ' / ' +
        str(len(do_dopisania)) + ' do dopisania\n'
        'Dopisano brakujących obrębów do F_COMMUNITY: ' +
        str(community_dopisane) + '\n'
        'Błędy zapisu (pól/tabel): ' + str(bledy_zapisu) + '\n'
    )
    if sciezka_wybrane_shp:
        wypis += 'Warstwa: ' + sciezka_wybrane_shp + '\n'
    wypis += '\n'

    wypis += 'Już w bazie (pominięte - ' + str(len(duplikaty)) + '):\n'
    for f in duplikaty:
        wypis += '  ' + str(f['adress_for']) + '\n'

    wypis += '\nBez kompletnych danych opisowych (pominięte - ' + \
        str(len(brak_danych)) + '):\n'
    for f in brak_danych:
        wypis += '  ' + str(f['adress_for']) + '\n'

    sciezka_raportu = os.path.join(
        folder, 'raport_utworz_baze_' + czas + '.txt')
    with open(sciezka_raportu, 'w', encoding='utf-8') as plik:
        plik.write(wypis)

    baza.zamknij()

    message = QMessageBox()
    message.setIcon(QMessageBox.Information)
    message.setWindowTitle('Raport')
    message.setText('Zakończono. Czy pokazać raport?')
    message.addButton("Zamknij", QMessageBox.ActionRole)
    message.addButton("Zamknij i pokaż raport", QMessageBox.ActionRole)
    if message.exec_() == 1:
        os.startfile(sciezka_raportu)

    QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
    return True
