"""STL i pokrywa (VEG_COVER_CD) dla punktów opis_pkt - wspólne dla
"Edytora warstw do opisów" (warstwa_opisow_dock.py, przy stawianiu punktu)
i "Dopisz opisy taksacyjne" (baza_dopisz_opisy_taks.py, uzupełnienie STL
dla punktów postawionych przed wprowadzeniem pola STL).

STL szukany w warstwie WYDZ_POL_stare (pole STL):
1. poligon, na którym leży punkt (niepuste STL),
2. inaczej najbliższy poligon z niepustym STL, nie dalej niż
   MAX_ODLEGLOSC metrów - odległość do granicy poligonu
   (QgsGeometry.distance, punkt w środku = 0), liczona w PUWG 1992
   niezależnie od układu warstw.

Polskie znaki w kodach (BMŚW, LŁ, BMWYŻŚW...): stare warstwy bez .cpg
albo z błędnym .cpg dają "krzaki". Dlatego:
- warstwa_do_odczytu: gdy wartości STL wyglądają na zepsute, warstwa jest
  czytana ponownie (osobna instancja, warstwa użytkownika bez zmian) w
  kodowaniu, przy którym wszystkie wartości są czyste,
- napraw_kod: przy zapisie do bazy wartość spoza słownika bazy jest
  naprawiana (ponowne odkodowanie albo dopasowanie bez ogonków / z '?' w
  miejscu polskiej litery) - tylko przy jednoznacznym trafieniu.
"""
import re

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature,
    QgsGeometry,
    QgsProject, QgsSpatialIndex, QgsVectorLayer, QgsWkbTypes,
)

NAZWA_ZRODLA_STL = 'WYDZ_POL_stare'
POLE_STL = 'STL'
MAX_ODLEGLOSC = 20.0

# grupy, dla których STL i pokrywy nie dopisujemy (pola zostają nietknięte)
GRUPY_BEZ_STL = ('L ENERG', 'LZ-Ł')

# pokrywa ustalana z samej grupy
POKRYWA_GRUPY = {
    'DROGI L': 'NAGA',
    'RETENCJA': 'NAGA',
    'ZRĄB': 'ZAD',
    'SUKCESJA': 'SZCH',
}
# INNE WYL - pokrywa z predefiniowanego tekstu INF_ROZNE (wartości z
# warstwa_opisow_dock.PRESETY_INF_ROZNE); inny tekst -> pytanie
POKRYWA_INNE_WYL = {
    'Grunt użytkowany rolniczo': 'ZAD',
    'Droga': 'NAGA',
    'Woda': 'NAGA',
    'Zabudowania': 'NAGA',
    'Teren przydomowy': 'ZAD',
}

# F_VEG_COVER_DIC (kolejność wg kolumny porządkowej słownika)
SLOWNIK_POKRYWY = [
    ('NAGA', 'naga'),
    ('ŚCIO', 'ściółka'),
    ('ZIEL', 'zielna'),
    ('MSZ', 'mszysta - kobierce'),
    ('MSZC', 'mszysta - czernicowa'),
    ('ZAD', 'zadarniona'),
    ('SZAD', 'silnie zadarniona'),
    ('SZCH', 'silnie zachwaszczona'),
]

_CRS_92 = QgsCoordinateReferenceSystem('EPSG:2180')

POLSKIE = 'ĄĆĘŁŃÓŚŹŻ'
_ODPOWIEDNIKI = {
    'A': 'Ą', 'C': 'Ć', 'E': 'Ę', 'L': 'Ł', 'N': 'Ń', 'O': 'Ó', 'S': 'Ś',
    'Z': 'ŹŻ',
}
_CZYSTY_KOD = re.compile(f'^[A-Z0-9 {POLSKIE}-]*$')
# kolejność prób odczytu warstwy o zepsutych wartościach
_KODOWANIA_WARSTWY = ('windows-1250', 'UTF-8', 'ISO-8859-2')
# pary (jak zapisano, jak błędnie odczytano) do odwracania "krzaków"
_KODOWANIA_NAPRAWY = ('utf-8', 'cp1250', 'cp1252', 'latin-1', 'iso8859_2')


def kod_czysty(wartosc):
    """Czy kod składa się wyłącznie z wielkich liter (w tym polskich),
    cyfr, spacji i myślnika - czyli nie ma w nim "krzaków"."""
    return bool(_CZYSTY_KOD.match(str(wartosc)))


def napraw_kod(wartosc, slownik):
    """(kod, naprawiony) dla wartości względem listy kodów słownika bazy:
    - wartość jest w słowniku -> (wartość, False),
    - jednoznaczna naprawa -> (kod ze słownika, True),
    - nie da się -> (None, False).
    Porównanie dokładne (wielkość liter, znaki) - nie jak w Accessie."""
    wartosc = str(wartosc).strip()
    slownik = {str(k).strip() for k in slownik if k is not None}
    if wartosc in slownik:
        return wartosc, False

    # 1. "krzaki" - tekst zapisany w jednym kodowaniu, odczytany w innym
    for zapis in _KODOWANIA_NAPRAWY:
        for odczyt in _KODOWANIA_NAPRAWY:
            if zapis == odczyt:
                continue
            try:
                kand = wartosc.encode(odczyt).decode(zapis)
            except (UnicodeError, LookupError):
                continue
            if kand in slownik:
                return kand, True

    # 2. bez ogonków / zgubiona polska litera ('?', znak zastępczy, krzaki).
    # Ciąg n kolejnych "śmieciowych" znaków = najpierw dokładnie n
    # zgubionych polskich liter ('LWY??W' -> LWYŻŚW), a gdy to nie daje
    # jednoznacznego trafienia - 1..n (jedna litera w UTF-8 odczytana jako
    # 1250 daje dwa znaki, np. 'LĹ�' -> LŁ)
    for dokladnie in (True, False):
        wzor = ''
        smieci = 0
        for znak in wartosc.upper() + '\0':
            dobry = ('A' <= znak <= 'Z' or znak in POLSKIE or znak.isdigit()
                     or znak in ' -\0')
            if not dobry:
                smieci += 1
                continue
            if smieci:
                zakres = smieci if dokladnie else f'1,{smieci}'
                wzor += f'[{POLSKIE}]{{{zakres}}}'
                smieci = 0
            if 'A' <= znak <= 'Z':
                wzor += f'[{znak}{_ODPOWIEDNIKI.get(znak, "")}]'
            elif znak != '\0':
                wzor += re.escape(znak)
        trafienia = [k for k in slownik if re.fullmatch(wzor, k)]
        if len(trafienia) == 1:
            return trafienia[0], True
    return None, False


def warstwa_do_odczytu(lyr):
    """(warstwa do czytania STL, komunikat albo ''). Gdy wartości STL
    warstwy mają "krzaki" (brak/zły .cpg), próbuje odczytać ten sam plik
    w innych kodowaniach i zwraca pierwszą czystą instancję."""
    pole = nazwa_pola_stl(lyr)
    if pole is None:
        return lyr, ''

    def _wartosci(warstwa):
        return {
            str(f[pole]).strip() for f in warstwa.getFeatures()
            if not _pusty(f[pole])
        }

    zle = sorted(w for w in _wartosci(lyr) if not kod_czysty(w))
    if not zle:
        return lyr, ''

    try:
        sciezka = lyr.dataProvider().dataSourceUri()
    except Exception:
        sciezka = ''
    if lyr.providerType() == 'ogr' and sciezka:
        for kodowanie in _KODOWANIA_WARSTWY:
            tmp = QgsVectorLayer(sciezka, lyr.name(), 'ogr')
            if not tmp.isValid():
                break
            tmp.setProviderEncoding(kodowanie)
            if all(kod_czysty(w) for w in _wartosci(tmp)):
                return tmp, (
                    f'Warstwa "{lyr.name()}" ma błędne kodowanie znaków '
                    f'(brak lub zły plik .cpg) - STL czytam jako '
                    f'{kodowanie}. Popraw .cpg warstwy.')

    return lyr, (
        f'Warstwa "{lyr.name()}" ma podejrzane wartości STL '
        f'({", ".join(zle[:5])}) - nie udało się dobrać kodowania. Takie '
        'STL zostaną naprawione albo odrzucone przy zapisie do bazy.')


def grupa_wymaga_stl(grupa):
    return grupa not in GRUPY_BEZ_STL


def pokrywa_domyslna(grupa, inf_rozne=''):
    """Kod pokrywy wynikający wprost z grupy (i tekstu INF_ROZNE dla
    INNE WYL), albo None - wtedy trzeba zapytać użytkownika (TURYST,
    INNE WYL z własnym tekstem). Dla GRUPY_BEZ_STL też None, ale tam
    pokrywy w ogóle nie ustalamy (patrz grupa_wymaga_stl)."""
    if grupa in POKRYWA_GRUPY:
        return POKRYWA_GRUPY[grupa]
    if grupa == 'INNE WYL':
        return POKRYWA_INNE_WYL.get((inf_rozne or '').strip())
    return None


def nazwa_pola_stl(lyr):
    """Rzeczywista nazwa pola STL w warstwie (bez względu na wielkość
    liter) albo None."""
    for pole in lyr.fields():
        if pole.name().upper() == POLE_STL:
            return pole.name()
    return None


def warstwy_zrodla_stl():
    """Warstwy poligonowe w TOC o nazwie WYDZ_POL_stare."""
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.name().upper() == NAZWA_ZRODLA_STL.upper()
        and lyr.geometryType() == QgsWkbTypes.PolygonGeometry
    ]


def _pusty(wartosc):
    return wartosc is None or str(wartosc).strip() in ('', 'NULL', 'None')


class ZrodloSTL:
    """Indeks poligonów warstwy źródłowej w EPSG:2180 - budowany raz,
    potem każde zapytanie o punkt to kilka porównań."""

    def __init__(self, lyr, odczyt=None):
        """lyr - warstwa z projektu (nazwa, życie obiektu), odczyt -
        ewentualna instancja tego samego pliku z poprawionym kodowaniem
        (warstwa_do_odczytu), z której czytane są obiekty."""
        self.lyr = lyr
        odczyt = odczyt or lyr
        self.pole = nazwa_pola_stl(odczyt)
        tr = QgsCoordinateTransform(
            odczyt.crs(), _CRS_92, QgsProject.instance())

        self._geom = {}
        self._stl = {}
        self._si_wszystkie = QgsSpatialIndex()
        self._si_z_stl = QgsSpatialIndex(
            QgsSpatialIndex.FlagStoreFeatureGeometries)
        for f in odczyt.getFeatures():
            g = f.geometry()
            if g is None or g.isEmpty():
                continue
            g = QgsGeometry(g)
            g.transform(tr)
            fid = f.id()
            self._geom[fid] = g
            self._si_wszystkie.addFeature(fid, g.boundingBox())
            wartosc = f[self.pole]
            if not _pusty(wartosc):
                self._stl[fid] = str(wartosc).strip()
                f92 = QgsFeature(fid)
                f92.setGeometry(g)
                self._si_z_stl.addFeature(f92)

    def wartosci(self):
        """Posortowane unikalne STL z warstwy - lista do ręcznego wyboru."""
        return sorted(set(self._stl.values()))

    def stl_dla_punktu(self, punkt_xy, crs_punktu):
        """STL dla punktu (QgsPointXY w crs_punktu) albo None, gdy ani
        poligon pod punktem, ani żaden w promieniu MAX_ODLEGLOSC nie ma
        niepustego STL."""
        g = QgsGeometry.fromPointXY(punkt_xy)
        g.transform(QgsCoordinateTransform(
            crs_punktu, _CRS_92, QgsProject.instance()))

        for fid in self._si_wszystkie.intersects(g.boundingBox()):
            if self._geom[fid].contains(g) and fid in self._stl:
                return self._stl[fid]

        najblizsze = self._si_z_stl.nearestNeighbor(g, 1, MAX_ODLEGLOSC)
        for fid in najblizsze:
            if self._geom[fid].distance(g) <= MAX_ODLEGLOSC:
                return self._stl[fid]
        return None
