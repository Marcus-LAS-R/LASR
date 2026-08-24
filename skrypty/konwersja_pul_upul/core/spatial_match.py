"""Wyznaczenie JEDNEGO adresu administracyjnego dla całej warstwy
wydzieleń (obręby ewidencyjne dla kierunku PUL->UPUL; w przyszłości
NADLESNICTWA.shp dla UPUL->PUL), na podstawie jej położenia geometrycznego
- NIE osobno dla każdego poligonu.

Warstwa wydzieleń jest wyłącznie lokalizatorem geometrycznym (przyjęte
założenie: całe nadleśnictwo/leśnictwo leży w jednym obrębie
ewidencyjnym) - żadne atrybuty tej warstwy (ODDZ/WYDZ/GRP) nie są
używane. ODDZ/WYDZ (litera wydzielenia) dla każdego wydzielenia w bazie
wynikowej pochodzą z parsowania adresu źródłowego PUL
(core/adres.rozbierz_adres_pul), nie z tej warstwy.

Wybór obrębu: sumuje powierzchnię nałożenia WSZYSTKICH poligonów
wydzielenia na każdy obręb referencyjny i wybiera ten o największej
łącznej powierzchni (nie punkt reprezentatywny pojedynczego poligonu -
odporność na wydzielenia leżące dokładnie na granicy). Reużywa już
istniejący, przetestowany silnik nakładania z shp_aktualizuj_ewidencje.py
zamiast pisać go od nowa.
"""

import re

from qgis.core import QgsCoordinateTransform, QgsProject

from ...shp_aktualizuj_ewidencje import _nakladajace_sie, _geometrie_oryg
from ...aktualizacja_upul.core.shp_standard import OBR_TERYT_KANDYDACI

# udział powierzchni najlepszego kandydata poniżej tego progu = wydzielenie
# leży na granicy >1 obrębu - dopasowanie mimo to wykonane (bierzemy
# dominujący obręb), ale trafia do sekcji ostrzeżeń raportu
PROG_GRANICZNY = 0.98

# format jpt_kod_je warstwy obreby_ewidencyjne.shp/OBR.shp: WOJ(2)POW(2)
# GMI(2)_RODZAJ_GMINY(1).OBREB(4) - zweryfikowany na materialy/PUL/shp
# na dwóch niezależnych plikach ("020102_2.0024" dla obrębu Pstrąże ->
# MUNICIPALITY_CD="022", COMMUNITY_CD="0024", zgodnie z F_COMMUNITY
# czystej bazy UPUL). Inny wzorzec (z dodatkowym ".reszta" na numer
# działki) obsługuje już przygotuj_baze_z_ewid._rozbierz_teryt() - ten
# tutaj jest dedykowany krótszej, obrębowej postaci jpt_kod_je.
_WZORZEC_OBREB_TERYT = re.compile(r'^(\d{2})(\d{2})(\d{2})_(\d)\.(\d{4})$')

# kandydaci na pole z nazwą obrębu - JPT_NAZWA_ dla PRG-GUGiK
# (obreby_ewidencyjne.shp/OBR.shp), G5NAZ dla surowego importu SWDE/EGiB
# (ta sama szerokość 30 zn. co F_COMMUNITY.COMMUNITY_NAME - potwierdzone
# w aktualizacja_upul.core.shp_standard.SCHEMAS["OBR"])
_NAZWA_KANDYDACI = ('JPT_NAZWA_', 'G5NAZ')


def _z_jpt_kod_je(kod):
    """Ścisłe parsowanie formatu jpt_kod_je (PRG-GUGiK)."""
    dopasowanie = _WZORZEC_OBREB_TERYT.match(kod)
    if not dopasowanie:
        return None
    woj, pow_, gmi, rodz, obreb = dopasowanie.groups()
    return (woj, pow_, gmi + rodz, obreb)


def _z_pozycji_teryt(kod):
    """Luźniejsze cięcie pozycyjne dla starszych formatów (IDOBREBU/G5NRO
    z surowego importu SWDE/EGiB) - ta sama formuła co
    aktualizacja_upul.core.shp_standard.konwertuj_warstwe() stosuje dla
    warstwy ODDZ: [0:4]=COUNTY+DISTRICT, [4:8] (bez '_')=MUNICIP,
    [-4:]=COMMUNITY."""
    if len(kod) < 8:
        return None
    county, district = kod[0:2], kod[2:4]
    municip = kod[4:8].replace('_', '')
    community = kod[-4:]
    if not (county.isdigit() and district.isdigit() and community.isdigit()):
        return None
    return (county, district, municip, community)


def _nazwa_z_obreb(feature, src_fields):
    for kandydat in _NAZWA_KANDYDACI:
        if kandydat not in src_fields:
            continue
        wartosc = feature[src_fields[kandydat]]
        if wartosc:
            return str(wartosc).strip()
    return ''


def klucz_teryt_z_obreb(feature):
    """ekstrakcja_klucza dla warstwy obrębów ewidencyjnych - próbuje po
    kolei kandydatów na pole z kodem TERYT obrębu (te same co
    OBR_TERYT_KANDYDACI: IDOBREBU, JPT_KOD_JE, G5NRO - warstwa może
    pochodzić z PRG-GUGiK/jpt_kod_je, np. obreby_ewidencyjne.shp/OBR.shp
    z materialy/PUL, albo z surowego importu SWDE/EGiB). Dla JPT_KOD_JE
    stosuje ścisły wzorzec (zweryfikowany na realnych danych), dla
    pozostałych - luźniejsze cięcie pozycyjne.

    Zwraca (klucz, nazwa) - klucz=(COUNTY_CD,DISTRICT_CD,MUNICIPALITY_CD,
    COMMUNITY_CD), nazwa=nazwa obrębu (pusty string, gdy pole nazwy nie
    istnieje w warstwie - potrzebna do F_COMMUNITY.COMMUNITY_NAME, wzorem
    przygotuj_baze_z_ewid.py, które też bierze nazwę wprost z warstwy
    ewidencyjnej zamiast zostawiać NULL). Zwraca None (całość), gdy żaden
    kandydat na kod TERYT nie pasuje."""
    src_fields = {f.name().upper(): f.name() for f in feature.fields()}
    for kandydat in OBR_TERYT_KANDYDACI:
        if kandydat not in src_fields:
            continue
        kod = feature[src_fields[kandydat]]
        if not kod:
            continue
        kod = str(kod)
        klucz = _z_jpt_kod_je(kod) if kandydat == 'JPT_KOD_JE' \
            else _z_pozycji_teryt(kod)
        if klucz is not None:
            return klucz, _nazwa_z_obreb(feature, src_fields)
    return None


class DopasowanieAdministracji:
    __slots__ = ('status', 'klucz_teryt', 'nazwa_obrebu', 'udzial')

    def __init__(self, status, klucz_teryt=None, nazwa_obrebu='', udzial=0.0):
        # 'ok' | 'graniczne' | 'brak_przeciecia'
        self.status = status
        self.klucz_teryt = klucz_teryt
        self.nazwa_obrebu = nazwa_obrebu
        self.udzial = udzial


def dopasuj_administracje(wydz_lyr, referencyjna_lyr, ekstrakcja_klucza,
                           postep=None):
    """Zwraca JEDNO DopasowanieAdministracji dla całej wydz_lyr (nie per
    poligon) - sumuje powierzchnię nałożenia wszystkich jej cech na każdy
    obiekt referencyjna_lyr i wybiera ten o największej łącznej
    powierzchni.

    ekstrakcja_klucza(feature_referencyjnej) -> (klucz, nazwa) albo None
    (gdy nie da się sparsować) - generyczne: dla przyszłego kierunku
    UPUL->PUL wystarczy podać NADLESNICTWA.shp i inną funkcję klucza
    (reg_cd,ins_cd + ins_name), bez zmian w tej funkcji."""
    transform = None
    if wydz_lyr.crs().authid() != referencyjna_lyr.crs().authid():
        transform = QgsCoordinateTransform(
            referencyjna_lyr.crs(), wydz_lyr.crs(), QgsProject.instance())

    ref_geom = _geometrie_oryg(referencyjna_lyr, transform)
    klucze_ref = {
        f.id(): ekstrakcja_klucza(f) for f in referencyjna_lyr.getFeatures()}

    nakladanie = _nakladajace_sie(wydz_lyr, ref_geom, postep)

    suma_pow = {}  # {oid_referencyjnej: laczna pow. nalozenia ze WSZYSTKICH cech wydz}
    for pary in nakladanie.values():
        for oid, pow in pary:
            suma_pow[oid] = suma_pow.get(oid, 0.0) + pow

    if not suma_pow:
        return DopasowanieAdministracji('brak_przeciecia')

    najlepszy_oid = max(suma_pow, key=suma_pow.get)
    znaleziono = klucze_ref.get(najlepszy_oid)
    if znaleziono is None:
        return DopasowanieAdministracji('brak_przeciecia')
    klucz, nazwa = znaleziono

    pow_wydz_total = sum(f.geometry().area() for f in wydz_lyr.getFeatures())
    udzial = suma_pow[najlepszy_oid] / pow_wydz_total if pow_wydz_total > 0 else 1.0
    status = 'ok' if udzial >= PROG_GRANICZNY else 'graniczne'
    return DopasowanieAdministracji(status, klucz, nazwa, udzial)
