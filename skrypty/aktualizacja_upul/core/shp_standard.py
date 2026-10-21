"""Konwersja shapefile'i ze starego standardu struktury pól na standard
obowiązujący obecnie w LAS-R.

Definicje docelowych schematów (`SCHEMAS`) są przepisane 1:1 z wzorcowych
plików w `materialy/wzory_SHP/*.dbf` (to jest źródło prawdy - w razie
wątpliwości sprawdzać tam, nie w tym pliku). Mapowania starych nazw pól na
nowe (`FIELD_MAP`) są odtworzone dodatkowo z istniejących skryptów, które
budują te warstwy "od zera" - `przygotuj_dzkat.py`, `przygotuj_ls.py`,
`shp_dopisz_kody.py` / `shp_przygCiecieStUPUL.py` (WYDZ_POL),
`shp_przygCiecie.py` (WYDZ geometria bazowa, PNSW, OBR→ODDZ).

Część typów (OBR, GMIN, EWID, KLU, UZYTKI) to w nowym standardzie dalej
"surowe" warstwy z importu SWDE/EGiB - zachowują oryginalne pola `G5*`
(identyczne w starym i nowym standardzie, więc mapują się same przez
dopasowanie nazwy), z dopisanymi `LOKID`/`STARTOB`/`STARTWOB` (metadane
importu, niedostępne w starych plikach - zawsze "brak źródła") oraz, dla
KLU/UZYTKI, wyliczanymi `AU`/`SQ`/`KLU`.

Nie każde pole nowego standardu ma odpowiednik w starych plikach — część
danych (np. GRP, NIELES, WIEK, STL, ZABIEG) pochodzi normalnie z bazy
taksatora, nie z atrybutów SHP. Takie pola zostają puste, a konwersja
zgłasza je w raporcie jako brak źródła, zamiast zgadywać wartość.
"""

import os
import re

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsField, QgsFields, QgsFeature, QgsVectorFileWriter,
)


# kod liczbowy wojewodztwa (COUNTY) -> litera (COUNTY_L), jak w
# shp_przygCiecie.py / baza_rozlicz_pow_wydz.py
SL_WOJ = {
    "02": "D", "04": "C", "06": "L", "08": "F", "10": "E", "12": "K",
    "14": "W", "16": "O", "18": "R", "20": "B", "22": "G", "24": "S",
    "26": "T", "28": "N", "30": "P", "32": "Z",
}


# Zrodlo prawdy: materialy/wzory_SHP/*.dbf - wzorcowe puste/przykladowe
# pliki w aktualnie obowiazujacym standardzie. Struktury ponizej sa
# przepisane 1:1 z tych plikow (pomijajac pola "layer"/"path" - to
# artefakty narzedzia, ktorym te wzorce zapisano, nie czesc standardu).
#
# nazwa pola, typ ('String'/'Double'/'Int'), dlugosc, precyzja (tylko Double)
SCHEMAS = {
    "DZKAT": [
        ("COUNTY", "String", 2, None),
        ("DISTRICT", "String", 2, None),
        ("MUNICIP", "String", 3, None),
        ("COMMUNITY", "String", 4, None),
        ("PARCELNR", "String", 20, None),
        ("PARCELID", "String", 50, None),
        ("GRP", "String", 2, None),
        ("ARK", "String", 12, None),
        ("NIELES", "String", 3, None),
        ("UWAGI", "String", 150, None),
        ("PARCEL_AR", "Double", 11, 4),
        ("PARCEL_POW", "Double", 11, 4),
    ],
    "LS": [
        ("COUNTY", "String", 2, None),
        ("DISTRICT", "String", 2, None),
        ("MUNICIP", "String", 3, None),
        ("COMMUNITY", "String", 4, None),
        ("PARCELNR", "String", 20, None),
        ("PARCELID", "String", 50, None),
        ("GRP", "String", 2, None),
        ("ARK", "String", 12, None),
        ("NIELES", "String", 3, None),
        ("UWAGI", "String", 150, None),
        ("PARCEL_AR", "Double", 11, 4),
        ("PARCEL_POW", "Double", 11, 4),
        ("AU", "String", 10, None),
        ("SQ", "String", 10, None),
        ("SPRAWDZ", "String", 150, None),
        ("LANDID", "String", 50, None),
        ("LAND_AR", "Double", 11, 4),
        ("LAND_POW", "Double", 11, 4),
    ],
    # geometria bazowa wydzieleń, bez opisu taksacyjnego - jak tworzy ją
    # shp_przygCiecie.py (multiparttosingleparts z LS + dopisane pola),
    # zanim "Dopisz kody" doda opis (patrz WYDZ_POL)
    "WYDZ": [
        ("COUNTY", "String", 2, None),
        ("DISTRICT", "String", 2, None),
        ("MUNICIP", "String", 3, None),
        ("COMMUNITY", "String", 4, None),
        ("GRP", "String", 2, None),
        ("COUNTY_L", "String", 1, None),
        ("ODDZ", "String", 6, None),
        ("WYDZ", "String", 4, None),
        ("ADR_LES", "String", 25, None),
        ("POW_GRAF", "Double", 11, 4),
        ("ID", "Int", None, None),
    ],
    # WYDZ + pelny opis taksacyjny (po "Dopisz kody" / shp_przygCiecieStUPUL)
    # - unia WYDZ_POL.dbf i WYDZ_DOPISANE.dbf z wzory_SHP (ten drugi ma
    # dodatkowo POKRYWA, ktorego w tym pierwszym zabraklo)
    "WYDZ_POL": [
        ("COUNTY", "String", 2, None),
        ("DISTRICT", "String", 2, None),
        ("MUNICIP", "String", 3, None),
        ("COMMUNITY", "String", 4, None),
        ("GRP", "String", 2, None),
        ("COUNTY_L", "String", 1, None),
        ("ODDZ", "String", 6, None),
        ("WYDZ", "String", 4, None),
        ("ADR_LES", "String", 25, None),
        ("POW_GRAF", "Double", 11, 4),
        ("ID", "Int", None, None),
        ("L_EWID", "String", 1, None),
        ("UDZIAL", "String", 5, None),
        ("GAT", "String", 10, None),
        ("WIEK", "Int", None, None),
        ("ZADRZEW", "Double", 11, 1),
        ("POW_WYDZ", "String", 10, None),
        ("TYP_POW", "String", 20, None),
        ("STRUKTUR", "String", 20, None),
        ("SLMN_KOL", "Int", None, None),
        ("STL", "String", 20, None),
        ("POKRYWA", "String", 20, None),
        ("ZABIEG", "String", 20, None),
        ("POW_ZAB", "Double", 11, 4),
        ("ODNOW", "String", 20, None),
        ("POW_ODN", "Double", 11, 4),
        ("AGROT", "Double", 11, 4),
        ("PIEL", "Double", 11, 4),
        # PRZEST nie wystepuje we wzorcowym pliku (opcjonalne, dopisywane
        # tylko gdy wlaczona flaga "przestoje" w shp_dopisz_kody.py)
        ("PRZEST", "Double", 11, 4),
        ("INNE", "String", 70, None),
    ],
    "PNSW": [
        ("ID", "Int", None, None),
        ("ADR_BDL", "String", 25, None),
        ("KOD_PNSW", "String", 12, None),
        ("NR_PNSW", "Int", None, None),
        ("NR_EW", "String", 25, None),
        ("ADR_ADM", "String", 25, None),
        ("POW_GRAF", "Double", 11, 4),
        ("MUNICIP", "String", 3, None),
        ("COMMUNITY", "String", 4, None),
    ],
    # "surowa" warstwa obrebow z importu ewidencyjnego (SWDE/EGiB) -
    # zachowuje oryginalne pola G5* (identyczne w starym i nowym
    # standardzie), dochodza tylko LOKID/STARTOB/STARTWOB
    "OBR": [
        ("G5NRO", "String", 25, None),
        ("G5PEW", "Double", 20, 5),
        ("G5NAZ", "String", 30, None),
        ("G5DTW", "String", 20, None),
        ("G5DTU", "String", 20, None),
        ("G5RJEW", "String", 40, None),
        ("LOKID", "String", 64, None),
        ("STARTOB", "String", 20, None),
        ("STARTWOB", "String", 20, None),
    ],
    # jednostka administracyjna (gmina) z importu ewidencyjnego - ten sam
    # wzorzec co OBR
    "GMIN": [
        ("G5IDJ", "String", 30, None),
        ("G5PEW", "Double", 20, 5),
        ("G5NAZ", "String", 90, None),
        ("G5DTW", "String", 20, None),
        ("G5DTU", "String", 20, None),
        ("LOKID", "String", 64, None),
        ("STARTOB", "String", 20, None),
        ("STARTWOB", "String", 20, None),
    ],
    # "surowa" warstwa dzialek ewidencyjnych z importu SWDE/EGiB, PRZED
    # przetworzeniem na biznesowy standard DZKAT (patrz "DZKAT" powyzej) -
    # np. stare pliki, ktore maja tylko pola G5IDD/NUMER/OBREB, bez
    # COUNTY_CD/MUNICIPALI itp.
    "EWID": [
        ("NUMER", "String", 15, None),
        ("OBREB", "String", 30, None),
        ("G5PEW", "Double", 20, 5),
        ("G5IDD", "String", 50, None),
        ("G5RZN", "String", 15, None),
        ("G5DWW", "String", 15, None),
        ("G5DZP", "String", 1, None),
        ("LOKID", "String", 64, None),
        ("STARTOB", "String", 20, None),
        ("STARTWOB", "String", 20, None),
    ],
    # docelowy uklad MUNICIP/COMMUNITY/ODDZ - jak generuje shp_przygCiecie.py
    # z warstwy OBR (fuzzy-match kodu TERYT). Dla starych plikow nazwanych
    # "ODDZ" (ktore zwykle maja juz pole ODDZ wprost) logika w
    # konwertuj_warstwe() probuje najpierw dopasowania 1:1, a dopiero
    # potem TERYT jako fallback
    "ODDZ": [
        ("MUNICIP", "String", 3, None),
        ("COMMUNITY", "String", 4, None),
        ("ODDZ", "String", 6, None),
    ],
    # "surowa" warstwa klasoużytkow z importu SWDE/EGiB (G5OZU/G5OZK/G5PEW/
    # G5IDK - identyczne nazwy w starym i nowym standardzie) + dopisane
    # AU/SQ/KLU, tak jak robi to przygotuj_ls.py na warstwie KLU
    "KLU": [
        ("G5OZU", "String", 5, None),
        ("G5OZK", "String", 5, None),
        ("G5PEW", "Double", 20, 5),
        ("G5IDK", "String", 30, None),
        ("LOKID", "String", 64, None),
        ("STARTOB", "String", 20, None),
        ("STARTWOB", "String", 20, None),
        ("SQ", "String", 10, None),
        ("AU", "String", 10, None),
        ("KLU", "String", 15, None),
    ],
    # jw. ale UZYTKI_92 w starym standardzie ma tylko kod uzytku (G5OFU),
    # bez klasy glebowej - stad osobny, wezszy typ zamiast wspolnego KLU
    "UZYTKI": [
        ("G5OFU", "String", 5, None),
        ("G5PEW", "Double", 20, 5),
        ("IDUZYTKU", "String", 30, None),
        ("LOKID", "String", 64, None),
        ("STARTOB", "String", 20, None),
        ("STARTWOB", "String", 20, None),
        ("AU", "String", 10, None),
    ],
}

# nowe pole -> lista kandydatow starych nazw (kolejnosc = priorytet),
# dopasowanie bez wzgledu na wielkosc liter
FIELD_MAP = {
    "DZKAT": {
        "COUNTY": ["COUNTY_CD", "COUNTY"],
        "DISTRICT": ["DISTRICT_CD", "DISTRICT_C", "DISTRICT"],
        "MUNICIP": ["MUNICIPALITY_CD", "MUNICIPALI", "MUNICIP"],
        "COMMUNITY": ["COMMUNITY_CD", "COMMUNITY_", "COMMUNITY"],
        "PARCELNR": ["PARCEL_NR", "NUMER", "PARCELNR"],
        # zalozenie: REG_SHEET_ (arkusz mapy ewidencyjnej) ~ ARK - do
        # zweryfikowania na realnych danych, stad tez trafia do raportu
        "ARK": ["REG_SHEET_NR", "REG_SHEET_", "ARK"],
        "PARCEL_AR": ["PARCEL_AREA", "PARCEL_ARE", "PARCEL_AR"],
    },
    "LS": {
        "COUNTY": ["COUNTY_CD", "COUNTY"],
        "DISTRICT": ["DISTRICT_CD", "DISTRICT_C", "DISTRICT"],
        "MUNICIP": ["MUNICIPALITY_CD", "MUNICIPALI", "MUNICIP"],
        "COMMUNITY": ["COMMUNITY_CD", "COMMUNITY_", "COMMUNITY"],
        "PARCELNR": ["PARCEL_NR", "NUMER", "PARCELNR"],
        "ARK": ["REG_SHEET_NR", "REG_SHEET_", "ARK"],
        "PARCEL_AR": ["PARCEL_AREA", "PARCEL_ARE", "PARCEL_AR"],
        "AU": ["AREA_USE_CD", "AREA_USE_C", "AU"],
        "SQ": ["SOIL_QUALITY_CD", "SOIL_QUALI", "SQ"],
        "LANDID": ["G5IDD", "LANDID"],
        "LAND_AR": ["LAND_USE_AREA", "LAND_USE_A", "LAND_AR"],
        "LAND_POW": ["POW_GRAF_L", "POW_GRAF", "LAND_POW"],
    },
    "WYDZ": {
        "COUNTY": ["COUNTY_CD", "COUNTY"],
        "DISTRICT": ["DISTRICT_CD", "DISTRICT_C", "DISTRICT"],
        "MUNICIP": ["MUNICIPALITY_CD", "MUNICIPALI", "MUNICIP"],
        "COMMUNITY": ["COMMUNITY_CD", "COMMUNITY_", "COMMUNITY"],
        "ODDZ": ["ODDZ"],
        "WYDZ": ["WYDZ"],
        "ADR_LES": ["ADR_LES"],
        "POW_GRAF": ["POW_GRAF_W", "POW_GRAF"],
    },
    "WYDZ_POL": {
        "COUNTY": ["COUNTY_CD", "COUNTY"],
        "DISTRICT": ["DISTRICT_CD", "DISTRICT_C", "DISTRICT"],
        "MUNICIP": ["MUNICIPALITY_CD", "MUNICIPALI", "MUNICIP"],
        "COMMUNITY": ["COMMUNITY_CD", "COMMUNITY_", "COMMUNITY"],
        "ODDZ": ["ODDZ"],
        "WYDZ": ["WYDZ"],
        "ADR_LES": ["ADR_LES"],
        "POW_GRAF": ["POW_GRAF_W", "POW_GRAF"],
        "UDZIAL": ["PART_CD", "UDZIAL"],
        "GAT": ["SPECIES_CD", "GAT"],
        "TYP_POW": ["AREA_TYPE_CD", "AREA_TYPE", "TYP_POW"],
        "STRUKTUR": ["STAND_STRUCT_CD", "STAND_STRU", "STRUKTUR"],
        "SLMN_KOL": ["SLMN_KOL"],
        # STANDDENSI = wspolczynnik zadrzewienia (0.1-1.0), potwierdzone
        # na probce WYDZ_POL.dbf
        "ZADRZEW": ["STANDDENSITY_INDEX", "STANDDENSI", "ZADRZEW"],
        # SUB_AREA w starych danych to powierzchnia poddzialu (ha), nie
        # "powierzchnia poddzialkowa" w sensie topologicznym - stad POW_WYDZ
        "POW_WYDZ": ["SUB_AREA", "POW_WYDZ"],
    },
    "PNSW": {
        "KOD_PNSW": ["KOD", "KOD_PNSW"],
        "POW_GRAF": ["POW", "POW_GRAF"],
        "NR_PNSW": ["NR_PNSW"],
        "NR_EW": ["NR_EW"],
        "ADR_BDL": ["ADR_BDL"],
        "ADR_ADM": ["ADR_ADM"],
    },
    # G5OZU/G5OZK sa identyczne w starym i nowym standardzie (self-name
    # w _zbuduj_mapowanie juz to zalatwia) - tu tylko dodatkowe kandydaci
    # dla wyliczanych AU/SQ
    "KLU": {
        "AU": ["G5OZU", "G5OFU", "OFU", "AU"],
        "SQ": ["G5OZK", "SQ"],
    },
    # obreby z PRG (GUGiK) zamiast EGiB: jpt_kod_je = "040708_2.0019"
    # (jak G5NRO), jpt_nazwa_ = nazwa obrebu
    "OBR": {
        "G5NRO": ["G5NRO", "JPT_KOD_JE"],
        "G5NAZ": ["G5NAZ", "JPT_NAZWA_"],
    },
    "UZYTKI": {
        "AU": ["G5OFU", "G5OZU", "OFU", "AU"],
        # stare pliki (UZYTKI_92) maja ten identyfikator pod nazwa G5IDT
        "IDUZYTKU": ["G5IDT", "IDUZYTKU"],
    },
}

# kandydaci na pole z kodem TERYT obrebu (dla ODDZ, gdy nie ma wprost
# MUNICIP/COMMUNITY) - jak w shp_przygCiecie.py
OBR_TERYT_KANDYDACI = ["IDOBREBU", "JPT_KOD_JE", "G5NRO"]


# obecnosc ktoregos z tych pol w zrodle oznacza, ze to juz WYDZ z opisem
# taksacyjnym (WYDZ_POL), a nie geometria bazowa (WYDZ)
_WYDZ_POL_ZNACZNIKI = {
    "PART_CD", "SPECIES_CD", "AREA_TYPE", "AREA_TYPE_CD", "STAND_STRU",
    "STAND_STRUCT_CD", "UDZIAL", "GAT", "TYP_POW", "STRUKTUR",
}

def zgadnij_typ(nazwa, pola=None):
    """Zgaduje typ docelowy na podstawie nazwy warstwy/pliku i - jesli
    podano - listy jej pol (uzytkownik i tak potwierdza/poprawia wybor w
    dialogu).

    `pola`: opcjonalna lista nazw pol zrodlowej warstwy - pozwala odróżnić
    WYDZ (geometria bazowa) od WYDZ_POL (z opisem taksacyjnym), bo obie
    czesto maja "WYDZ" w nazwie pliku. Plik nazwany "DZKAT" zawsze zgaduje
    sie jako DZKAT (nawet jesli ma tylko "surowe" pola importu SWDE/EGiB,
    bez COUNTY/MUNICIP) - raport i tak pokaze co konkretnie brakuje; EWID
    trzeba wybrac recznie albo nazwac plik wprost "EWID".
    """
    n = nazwa.upper()
    pola_upper = {p.upper() for p in (pola or [])}

    if "DZKAT" in n:
        return "DZKAT"
    if "EWID" in n:
        return "EWID"
    if n.startswith("LS") or "_LS" in n or "LSY" in n:
        return "LS"
    if "WYDZ" in n:
        if _WYDZ_POL_ZNACZNIKI & pola_upper or "POL" in n or "OPS" in n:
            return "WYDZ_POL"
        return "WYDZ"
    if "PNSW" in n:
        return "PNSW"
    if "GMIN" in n:
        return "GMIN"
    if "OBR" in n:
        return "OBR"
    if "ODDZ" in n:
        return "ODDZ"
    if "UZYTKI" in n:
        return "UZYTKI"
    if "KLU" in n:
        return "KLU"
    return None


def _stworz_pola(typ):
    qf = QgsFields()
    for nazwa, typ_pola, dlugosc, precyzja in SCHEMAS[typ]:
        if typ_pola == "String":
            qf.append(QgsField(nazwa, QVariant.String, len=dlugosc))
        elif typ_pola == "Double":
            qf.append(QgsField(
                nazwa, QVariant.Double, "double", dlugosc, precyzja))
        elif typ_pola == "Int":
            qf.append(QgsField(nazwa, QVariant.Int))
    return qf


def _typ_pola(typ, nazwa_pola):
    for n, t, dl, pr in SCHEMAS[typ]:
        if n == nazwa_pola:
            return t, dl
    return "String", None


def folder_startowy_dla_wyboru(warstwy):
    """Folder, w ktorym ma domyslnie otwierac sie okno wyboru folderu
    wyjsciowego - jeden poziom wyzej niz folder z plikiem pierwszej
    warstwy wejsciowej majacej zrodlo na dysku."""
    for lyr in warstwy:
        try:
            sciezka = lyr.dataProvider().dataSourceUri().split("|")[0]
        except Exception:  # nopep8
            continue
        if sciezka and os.path.isfile(sciezka):
            return os.path.dirname(os.path.dirname(sciezka))
    return ""


def _wyjsciowa_sciezka(lyr, folder_wyjsciowy):
    """Nie tworzy folderu wyjsciowego - musi juz istniec (decyzja o
    utworzeniu nowego folderu nalezy jawnie do uzytkownika, patrz dialog
    konwersji: pyta o potwierdzenie zanim cokolwiek utworzy)."""
    try:
        sciezka = lyr.dataProvider().dataSourceUri().split("|")[0]
    except Exception:  # nopep8
        return None
    if not sciezka or not os.path.isfile(sciezka):
        return None
    if not folder_wyjsciowy or not os.path.isdir(folder_wyjsciowy):
        return None
    nazwa_pliku = os.path.basename(sciezka)
    return os.path.join(folder_wyjsciowy, nazwa_pliku)


# teksty, ktore stare narzedzia wpisywaly do DBF zamiast pustej wartosci
# (str(None) w Pythonie, str(NULL) w PyQGIS) - Kruszwica: STAND_STRU='None'
_TEKSTY_PUSTE = {"", "NONE", "NULL"}


def _pusta(wartosc):
    """None, QGIS NULL (pusty QVariant - tak OGR oddaje puste pola SHP),
    pusty/bialy string albo literalne "None"/"NULL"."""
    if wartosc is None:
        return True
    if isinstance(wartosc, QVariant):
        return wartosc.isNull()
    return isinstance(wartosc, str) and \
        wartosc.strip().upper() in _TEKSTY_PUSTE


def _tekst(wartosc):
    """Zamienia wartosc pola (w tym QGIS/Python NULL) na string do
    dalszych operacji tekstowych - NULL/None -> pusty string, NIE
    literalne "None"/"NULL" (str() na NULL-u daje wlasnie te napisy, ktore
    bez tej funkcji trafialy wprost do PARCELID/MUNICIP/COUNTY - Kruszwica:
    COUNTY='NU', PARCELID='NUNUNULNULL.NULL')."""
    return "" if _pusta(wartosc) else str(wartosc).strip()


def _rzutuj(wartosc, typ_pola):
    """Rzutuje surowa wartosc ze starej warstwy na typ pola docelowego.
    Zwraca (wartosc, blad albo None)."""
    tekst = _tekst(wartosc)

    if typ_pola == "Double":
        if tekst == "":
            return 0.0, None
        try:
            return float(tekst.replace(",", ".")), None
        except ValueError:
            return 0.0, f"nie udalo sie zrzutowac na liczbe: {wartosc!r}"

    if typ_pola == "Int":
        if tekst == "":
            return 0, None
        try:
            return int(float(tekst)), None
        except ValueError:
            return 0, f"nie udalo sie zrzutowac na liczbe calkowita: {wartosc!r}"

    return tekst, None


# znaki, ktore pojawiaja sie, gdy tekst UTF-8 odczytano jako Windows-1250
# i zapisano ponownie jako UTF-8 (np. "Ł" = C5 81 -> "Ĺ" + U+0081) -
# pierwsze bajty sekwencji UTF-8 polskich liter/ó w CP1250 plus znaki C1
_ZNACZNIKI_MOJIBAKE = set("ĹÄĂÂ") | {chr(c) for c in range(0x80, 0xA0)}


def _napraw_mojibake(tekst):
    """Odwraca podwojne kodowanie (UTF-8 przeczytane jako CP1250 i
    zapisane znow w UTF-8): "LZ-Ĺ\\x81" -> "LZ-Ł". Zwraca tekst bez zmian,
    gdy nie wyglada na zepsuty albo odwrocenie nie daje poprawnego UTF-8
    (np. prawdziwe "Ĺ" w tekscie - po zakodowaniu w CP1250 samotny bajt
    C5 nie jest poprawnym UTF-8)."""
    if not tekst or not (_ZNACZNIKI_MOJIBAKE & set(tekst)):
        return tekst
    bajty = bytearray()
    for ch in tekst:
        try:
            bajty += ch.encode("cp1250")
        except UnicodeEncodeError:
            # bajty niezdefiniowane w CP1250 (0x81, 0x83, 0x88, 0x90, 0x98)
            # przeszly przez Windows 1:1 jako U+0081 itd.
            if ord(ch) < 0x100:
                bajty.append(ord(ch))
            else:
                return tekst
    try:
        naprawiony = bytes(bajty).decode("utf-8")
    except UnicodeDecodeError:
        return tekst
    return naprawiony


def _zbuduj_mapowanie(typ, src_fields_upper):
    """src_fields_upper: {NAZWA_WIELKIMI: oryginalna_nazwa}

    Dla kazdego pola docelowego zbiera WSZYSTKIE istniejace w zrodle
    kolumny-kandydatow (znane stare warianty nazwy z FIELD_MAP, a na koncu
    ZAWSZE takze dokladnie ta sama nazwa co docelowa), w kolejnosci
    priorytetu. Wartosc bierze sie per obiekt z pierwszej NIEPUSTEJ -
    stare DZKAT bywaja zlaczeniem EGiB z pustymi kolumnami LS (Kruszwica:
    PARCEL_NR puste, numer w NUMER).

    Zwraca {nowe: [stare, ...]} (pusta lista = brak kolumny w zrodle).
    """
    mapa = FIELD_MAP.get(typ, {})
    mapowanie = {}
    for nazwa, _t, _dl, _pr in SCHEMAS[typ]:
        kandydaci = mapa.get(nazwa, []) + [nazwa]
        istniejace = []
        for k in kandydaci:
            oryg = src_fields_upper.get(k.upper())
            if oryg and oryg not in istniejace:
                istniejace.append(oryg)
        mapowanie[nazwa] = istniejace
    return mapowanie


def _dz_lacznik(county, district, municip, community, ark, parcelnr):
    if ark not in ("", " "):
        return county + district + municip + community + "." + ark + \
            "." + parcelnr
    return county + district + municip + community + "." + parcelnr


# identyfikator dzialki EGiB: WWPPGG_R.OOOO[.ARKUSZ].NUMER, np.
# 040706_5.0006.384 albo 160908_5.0127.AR_1.217/17
_WZORZEC_G5IDD = re.compile(
    r"^(\d{2})(\d{2})(\d{2})_(\d)\.(\d{4})\.(?:(.+)\.)?([^.]+)$")


def rozbij_g5idd(g5idd):
    """Zwraca dict COUNTY/DISTRICT/MUNICIP/COMMUNITY/ARK/PARCELNR z
    identyfikatora dzialki EGiB albo None, gdy nie pasuje do wzorca."""
    m = _WZORZEC_G5IDD.match(_tekst(g5idd))
    if not m:
        return None
    return {
        "COUNTY": m.group(1),
        "DISTRICT": m.group(2),
        "MUNICIP": m.group(3) + m.group(4),
        "COMMUNITY": m.group(5),
        "ARK": m.group(6) or "",
        "PARCELNR": m.group(7),
    }


# kolumny z identyfikatorem dzialki EGiB w roznych formach danych
# (SWDE/EGiB: G5IDD, eksport z GML: idDzialki, stare SHP: IDENTYFIKA)
_KANDYDACI_G5IDD = ["G5IDD", "IDDZIALKI", "ID_DZIALKI", "IDENTYFIKA"]
# kolumny z adresem lesnym (WYDZ/WYDZ_POL i zlaczenia z nimi)
_KANDYDACI_ADR_LES = ["ADR_LES", "ADRES_LES", "ADR_LESNY", "ADRES_LESN"]
# powierzchnia ewidencyjna dzialki (EGiB) - w m2 albo ha, patrz
# _pow_ewid_ha
_KANDYDACI_POW_EWID = ["G5PEW", "POW_EWID", "POW_EW"]

_SL_WOJ_ODWR = {litera: kod for kod, litera in SL_WOJ.items()}

# adres lesny: litera wojewodztwa + powiat(2) + gmina z rodzajem(3) +
# obreb(4) + "-..." np. "C070640006-051   -b   -00"
_WZORZEC_ADR_LES = re.compile(r"^([A-Z])(\d{2})(\d{3})(\d{4})-")


def rozbij_adr_les(adr_les):
    """Zwraca dict COUNTY/DISTRICT/MUNICIP/COMMUNITY z adresu lesnego albo
    None, gdy nie pasuje do wzorca albo litera wojewodztwa jest nieznana."""
    m = _WZORZEC_ADR_LES.match(_tekst(adr_les).upper())
    if not m or m.group(1) not in _SL_WOJ_ODWR:
        return None
    return {
        "COUNTY": _SL_WOJ_ODWR[m.group(1)],
        "DISTRICT": m.group(2),
        "MUNICIP": m.group(3),
        "COMMUNITY": m.group(4),
    }


def _pow_ewid_ha(wartosc, geometria):
    """Powierzchnia ewidencyjna w ha z wartosci w m2 albo ha. Jednostke
    rozpoznaje po porownaniu z powierzchnia geometrii (SWDE: G5PEW w m2,
    ale bywaja eksporty w ha): blizej geometrii po podzieleniu przez
    10000 -> m2. None, gdy wartosc pusta/0 albo zadna jednostka nie pasuje
    (rozjazd > 2x - wtedy lepiej nie wpisywac niz wpisac zle)."""
    try:
        pew = float(_tekst(wartosc).replace(",", "."))
    except ValueError:
        return None
    if pew <= 0:
        return None
    geom_ha = geometria.area() / 10000 if geometria else 0
    if geom_ha <= 0:
        return None
    for kandydat in (pew / 10000, pew):
        if 0.5 <= kandydat / geom_ha <= 2:
            return round(kandydat, 4)
    return None


def _ustaw(nf, typ, nazwa, wartosc, obiekt, raport):
    """Wpisuje wartosc do pola docelowego z rzutowaniem i przycieciem do
    dlugosci (z wpisem w raporcie)."""
    typ_pola, dlugosc = _typ_pola(typ, nazwa)
    wartosc, blad = _rzutuj(wartosc, typ_pola)
    if blad and len(raport["bledy"]) < 50:
        raport["bledy"].append(f"obiekt {obiekt}: {nazwa} ({blad})")
    if typ_pola == "String" and dlugosc and len(wartosc) > dlugosc:
        if len(raport["bledy"]) < 50:
            raport["bledy"].append(
                f"obiekt {obiekt}: {nazwa} przycięte do {dlugosc} znaków "
                f"(było: {wartosc!r})")
        wartosc = wartosc[:dlugosc]
    nf[nazwa] = wartosc


def konwertuj_warstwe(lyr, typ, folder_wyjsciowy):  # noqa
    """Konwertuje pojedyncza warstwe na nowy standard `typ`, zapisujac
    wynik do `folder_wyjsciowy` (wybrany przez uzytkownika w dialogu).

    Zwraca dict raportu: nazwa, typ, sciezka, obiekty, pola_zmapowane
    (lista par (nowe, opis zrodla)), pola_brakujace (lista opisow),
    naprawione (lista opisow naprawionych polskich znakow, max 50),
    liczba_naprawionych, bledy (lista opisow).
    """
    raport = {
        "nazwa": lyr.name(),
        "typ": typ,
        "sciezka": None,
        "obiekty": 0,
        "pola_zmapowane": [],
        "pola_brakujace": [],
        "naprawione": [],
        "liczba_naprawionych": 0,
        "bledy": [],
    }

    if typ not in SCHEMAS:
        raport["bledy"].append(f"Nieznany typ docelowy: {typ}")
        return raport

    sciezka_wy = _wyjsciowa_sciezka(lyr, folder_wyjsciowy)
    if sciezka_wy is None:
        raport["bledy"].append(
            "Warstwa nie ma pliku źródłowego (nie jest to warstwa SHP na "
            "dysku), albo folder wyjściowy nie istnieje/nie wskazano go "
            "- pominięto"
        )
        return raport

    src_fields_upper = {f.name().upper(): f.name() for f in lyr.fields()}
    qf = _stworz_pola(typ)
    pola_docelowe = [n for n, _t, _d, _p in SCHEMAS[typ]]
    pola_liczbowe = [n for n, t, _d, _p in SCHEMAS[typ] if t != "String"]

    writer = QgsVectorFileWriter(
        sciezka_wy, "UTF-8", qf, lyr.wkbType(), lyr.crs(), "ESRI Shapefile")
    if writer.hasError() != QgsVectorFileWriter.NoError:
        raport["bledy"].append(
            "Nie udało się utworzyć pliku wyjściowego: " +
            str(writer.errorMessage())
        )
        return raport

    mapowanie = _zbuduj_mapowanie(typ, src_fields_upper)
    # pole docelowe -> {opis zrodla: liczba obiektow}; z tego na koncu
    # raport zmapowanych/brakujacych (brak = zadne zrodlo nic nie dalo)
    uzyte = {n: {} for n in pola_docelowe}

    def licz(nazwa, zrodlo):
        uzyte[nazwa][zrodlo] = uzyte[nazwa].get(zrodlo, 0) + 1

    # ODDZ: MUNICIP/COMMUNITY z "golego" kodu TERYT obrebu (idobrebu/
    # jpt_kod_je/g5nro), gdy nie ma ich wprost - tak jak robi to
    # shp_przygCiecie.py. Samo ODDZ nigdy nie da sie wyliczyc z danych
    # obrebu - zawsze wymaga uzupelnienia (np. "Zanumeruj oddziały").
    kandydat_teryt = None
    if typ == "ODDZ":
        kandydat_teryt = next(
            (src_fields_upper[k] for k in OBR_TERYT_KANDYDACI
             if k in src_fields_upper), None)

    def pierwsza_kolumna(kandydaci):
        return next((src_fields_upper[k] for k in kandydaci
                     if k in src_fields_upper), None)

    # DZKAT/LS: skladowe adresu dzialki z G5IDD, gdy kolumny COUNTY_CD
    # itp. sa puste albo ich nie ma
    pole_g5idd = (
        pierwsza_kolumna(_KANDYDACI_G5IDD) if typ in ("DZKAT", "LS")
        else None)
    pola_z_g5idd = (
        "COUNTY", "DISTRICT", "MUNICIP", "COMMUNITY", "ARK", "PARCELNR")
    # dalej puste skladowe adresu administracyjnego -> z adresu lesnego
    # (Kruszwica, WYDZ_POL: COUNTY_CD itp. puste, adres w ADR_LES)
    pole_adr_les = pierwsza_kolumna(_KANDYDACI_ADR_LES)
    pola_z_adr_les = [
        n for n in ("COUNTY", "DISTRICT", "MUNICIP", "COMMUNITY")
        if n in pola_docelowe]
    if not pola_z_adr_les:
        pole_adr_les = None
    # DZKAT: PARCEL_AR z powierzchni ewidencyjnej (G5PEW), gdy puste. Nie
    # dla LS - tam G5PEW to powierzchnia konturu uzytku, nie dzialki
    pole_pow_ewid = (
        pierwsza_kolumna(_KANDYDACI_POW_EWID) if typ == "DZKAT" else None)

    for feat in lyr.getFeatures():
        nf = QgsFeature(qf)
        nf.setGeometry(feat.geometry())
        obiekt = feat.id()

        # liczby bez zrodla = 0, nie NULL (NULL w DBF to "*****")
        for n in pola_liczbowe:
            nf[n] = 0

        for nowe, stare_lista in mapowanie.items():
            for stare in stare_lista:
                wartosc = feat[stare]
                # 0 w kolumnie liczbowej traktowane jak brak - SHP nie ma
                # pustych liczb, stare narzedzia wpisywaly 0 (Kruszwica:
                # PARCEL_ARE=0 w 508 dzialkach); wynik i tak domyslnie 0
                if _pusta(wartosc) or (
                        isinstance(wartosc, (int, float))
                        and not isinstance(wartosc, bool) and wartosc == 0):
                    continue
                if isinstance(wartosc, str):
                    naprawiony = _napraw_mojibake(wartosc)
                    if naprawiony != wartosc:
                        raport["liczba_naprawionych"] += 1
                        if len(raport["naprawione"]) < 50:
                            raport["naprawione"].append(
                                f"obiekt {obiekt}: {stare}: {wartosc!r} -> "
                                f"{naprawiony!r}")
                        wartosc = naprawiony
                _ustaw(nf, typ, nowe, wartosc, obiekt, raport)
                licz(nowe, stare)
                break

        if pole_g5idd:
            czesci = rozbij_g5idd(feat[pole_g5idd])
            if czesci:
                for n in pola_z_g5idd:
                    if not _tekst(nf[n]) and czesci[n]:
                        _ustaw(nf, typ, n, czesci[n], obiekt, raport)
                        licz(n, f"{pole_g5idd} (rozbite)")

        if pole_adr_les and any(not _tekst(nf[n]) for n in pola_z_adr_les):
            czesci = rozbij_adr_les(feat[pole_adr_les])
            if czesci:
                for n in pola_z_adr_les:
                    if not _tekst(nf[n]):
                        _ustaw(nf, typ, n, czesci[n], obiekt, raport)
                        licz(n, f"{pole_adr_les} (rozbite)")

        if pole_pow_ewid and not nf["PARCEL_AR"]:
            pow_ha = _pow_ewid_ha(feat[pole_pow_ewid], feat.geometry())
            if pow_ha:
                nf["PARCEL_AR"] = pow_ha
                licz("PARCEL_AR", f"{pole_pow_ewid} (pow. ewid., w ha)")

        if kandydat_teryt:
            val = _tekst(feat[kandydat_teryt])
            if val:
                if not _tekst(nf["MUNICIP"]):
                    nf["MUNICIP"] = val[4:8].replace("_", "")
                    licz("MUNICIP", f"{kandydat_teryt} (kod TERYT, wyliczone)")
                if not _tekst(nf["COMMUNITY"]):
                    nf["COMMUNITY"] = val[-4:]
                    licz("COMMUNITY",
                         f"{kandydat_teryt} (kod TERYT, wyliczone)")

        # WYDZ/WYDZ_POL: COUNTY_L z tabeli wojewodztw na podstawie COUNTY
        if "COUNTY_L" in pola_docelowe and not _tekst(nf["COUNTY_L"]):
            litera = SL_WOJ.get(_tekst(nf["COUNTY"]), "")
            if litera:
                nf["COUNTY_L"] = litera
                licz("COUNTY_L", "(wyliczone z COUNTY wg tabeli województw)")

        # DZKAT: 1 obiekt = 1 cała działka, więc PARCEL_POW da się bezpiecznie
        # policzyć wprost z geometrii (tak jak w przygotuj_dzkat.py). W LS
        # geometria pojedynczego obiektu to tylko fragment użytku, więc tak
        # liczymy co najwyżej LAND_POW (powierzchnia tego fragmentu), nie
        # PARCEL_POW (powierzchnia całej działki).
        pole_pow = {"DZKAT": "PARCEL_POW", "LS": "LAND_POW"}.get(typ)
        if pole_pow and not nf[pole_pow]:
            nf[pole_pow] = round(feat.geometry().area() / 10000, 4)
            licz(pole_pow, "(wyliczone z geometrii)")

        # KLU = AU+SQ (jak dopisuje przygotuj_ls.py), gdy brak gotowego KLU
        if typ == "KLU" and not _tekst(nf["KLU"]):
            klu = (_tekst(nf["AU"]) + _tekst(nf["SQ"]))[:15]
            if klu:
                nf["KLU"] = klu
                licz("KLU", "(wyliczone z AU+SQ)")

        # PARCELID ze skladowych identycznie jak w przygotuj_dzkat.py /
        # przygotuj_ls.py, gdy pusty w zrodle
        if typ in ("DZKAT", "LS") and not _tekst(nf["PARCELID"]) \
                and _tekst(nf["PARCELNR"]):
            nf["PARCELID"] = _dz_lacznik(
                _tekst(nf["COUNTY"]),
                _tekst(nf["DISTRICT"]),
                _tekst(nf["MUNICIP"]),
                _tekst(nf["COMMUNITY"]),
                _tekst(nf["ARK"]),
                _tekst(nf["PARCELNR"]),
            )[:50]
            licz("PARCELID", "(wyliczone z COUNTY+DISTRICT+MUNICIP+"
                             "COMMUNITY+ARK+PARCELNR)")

        writer.addFeature(nf)
        raport["obiekty"] += 1

    del writer

    for nazwa in pola_docelowe:
        zrodla = uzyte[nazwa]
        if not zrodla:
            puste = mapowanie[nazwa]
            raport["pola_brakujace"].append(
                nazwa + (f" (kolumna {', '.join(puste)} pusta we wszystkich "
                         "obiektach)" if puste else ""))
        elif len(zrodla) == 1:
            raport["pola_zmapowane"].append((nazwa, next(iter(zrodla))))
        else:
            raport["pola_zmapowane"].append((nazwa, " / ".join(
                f"{z} ({ile} ob.)" for z, ile in zrodla.items())))

    raport["sciezka"] = sciezka_wy
    return raport


# --- automatyczne zgadywanie kodowania odczytu warstwy ---------------------
#
# Pliki .cpg starych shapefile'i bywaja bledne (potwierdzone na probce
# materialy/shp_stary_standard - .cpg deklaruje "UTF-8", a surowe bajty w
# DBF sa w rzeczywistosci Windows-1250), wiec zamiast im ufac probkujemy
# realne wartosci tekstowe i sprawdzamy, ktore z typowych dla polskich
# danych kodowan daje sensowny tekst. Zgadujemy dla KAZDEJ warstwy osobno -
# w jednym zestawie bywaja pliki w roznych kodowaniach (Kruszwica: DZKAT/
# ODDZ w UTF-8, OBREBY_AFT z PRG w CP1250; wspolne zgadywanie wybieralo
# ISO-8859-2, jedyne, ktore "nie wywalalo sie" na zadnym pliku).

KANDYDACI_KODOWAN = ["CP1250", "UTF-8", "ISO-8859-2", "CP852"]

_POLSKIE_ZNAKI = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
# znaki sterujace (C0 poza tab/lf/cr oraz C1 0x80-0x9F) i znak zastepczy -
# ich obecnosc po dekodowaniu oznacza prawie na pewno zle dobrane
# kodowanie (np. UTF-8 albo CP1250 czytane jako ISO-8859-2)
_ZNAKI_SMIECIOWE = {chr(c) for c in range(32) if c not in (9, 10, 13)}
_ZNAKI_SMIECIOWE |= {chr(c) for c in range(0x80, 0xA0)}
_ZNAKI_SMIECIOWE.add("�")


def _probka_wartosci(lyr, ile_obiektow=5000):
    """Zwraca liste stringow z pol tekstowych warstwy, odczytanych tak,
    zeby zachowac oryginalne bajty (kodowanie ISO-8859-1 mapuje kazdy
    bajt 1:1 na znak, wiec `wartosc.encode('ISO-8859-1')` odtwarza
    dokladnie to, co bylo w pliku, niezaleznie od prawdziwego kodowania)
    - do testowania kandydujacych kodowan. Tylko wartosci z bajtami
    >= 0x80 - czysty ASCII wyglada tak samo w kazdym kodowaniu."""
    poprzednie = lyr.dataProvider().encoding()
    lyr.dataProvider().setEncoding("ISO-8859-1")

    pola_tekstowe = [f.name() for f in lyr.fields() if not f.isNumeric()]
    wartosci = []
    if pola_tekstowe:
        for i, feat in enumerate(lyr.getFeatures()):
            if i >= ile_obiektow:
                break
            for p in pola_tekstowe:
                w = feat[p]
                if _pusta(w):
                    continue
                w = str(w)
                if any(ord(ch) >= 0x80 for ch in w):
                    wartosci.append(w)

    lyr.dataProvider().setEncoding(poprzednie)
    return wartosci


def _ocen_kodowanie(wartosci, kodowanie):
    """Probuje zdekodowac probke (stringi z `_probka_wartosci`) danym
    kodowaniem. Zwraca (liczba_bledow_dekodowania, liczba_polskich_znakow,
    liczba_smieciowych_znakow)."""
    bledy = 0
    polskie = 0
    smieci = 0
    for w in wartosci:
        raw = w.encode("ISO-8859-1", errors="replace")
        try:
            dekodowane = raw.decode(kodowanie, errors="strict")
        except (UnicodeDecodeError, LookupError):
            bledy += 1
            continue
        polskie += sum(1 for ch in dekodowane if ch in _POLSKIE_ZNAKI)
        smieci += sum(1 for ch in dekodowane if ch in _ZNAKI_SMIECIOWE)
    return bledy, polskie, smieci


def zgadnij_kodowanie_warstwy(lyr):
    """Zgaduje kodowanie jednej warstwy. Zwraca nazwe z
    `KANDYDACI_KODOWAN` albo None, gdy warstwa nie ma zadnych znakow
    spoza ASCII (wtedy kodowanie nie ma znaczenia).

    1. Cala probka poprawnym UTF-8 -> UTF-8: przypadkowy tekst w CP1250
       praktycznie nigdy nie jest poprawnym UTF-8 (polska litera w CP1250
       to pojedynczy bajt >= 0x80, ktory w UTF-8 musi miec bajt
       kontynuacji 0x80-0xBF zaraz po sobie).
    2. W przeciwnym razie: najmniej bledow dekodowania > najmniej znakow
       smieciowych (C0/C1) > najwiecej polskich znakow > kolejnosc w
       KANDYDACI_KODOWAN (przy remisie CP1250)."""
    wartosci = _probka_wartosci(lyr)
    if not wartosci:
        return None
    if _ocen_kodowanie(wartosci, "UTF-8")[0] == 0:
        return "UTF-8"
    wyniki = [
        (kandydat,) + _ocen_kodowanie(wartosci, kandydat)
        for kandydat in KANDYDACI_KODOWAN
    ]
    wyniki.sort(key=lambda w: (w[1], w[3], -w[2]))
    return wyniki[0][0]


def zgadnij_kodowanie(warstwy):
    """Zgaduje kodowanie dla kazdej warstwy z listy osobno. Zwraca liste
    wynikow `zgadnij_kodowanie_warstwy` (rownolegla do `warstwy`)."""
    return [zgadnij_kodowanie_warstwy(lyr) for lyr in warstwy]


def probka_do_podgladu(warstwy, ile=30):
    """Zwraca do `ile` unikalnych surowych wartosci tekstowych z grupy
    warstw (ISO-8859-1 - zachowuje oryginalne bajty), z priorytetem dla
    wartosci zawierajacych bajty >= 0x80 (najbardziej informatywne przy
    recznym porownywaniu kodowan - czysty ASCII wyglada tak samo pod
    kazdym z nich)."""
    wszystkie = []
    for lyr in warstwy:
        wszystkie += _probka_wartosci(lyr)

    unikalne = list(dict.fromkeys(wszystkie))
    nieascii = [w for w in unikalne if any(ord(ch) >= 0x80 for ch in w)]
    ascii_ = [w for w in unikalne if w not in nieascii]
    return (nieascii + ascii_)[:ile]


def zdekoduj_probke(wartosci, kodowania=None):
    """Dla kazdej wartosci z `wartosci` (string ISO-8859-1 = surowe bajty)
    zwraca liste slownikow {kodowanie: zdekodowany_tekst_albo_opis_bledu},
    po jednym na kazde kodowanie z `kodowania` (domyslnie
    KANDYDACI_KODOWAN) - do wizualnego porownania w dialogu."""
    kodowania = kodowania or KANDYDACI_KODOWAN
    wynik = []
    for w in wartosci:
        raw = w.encode("ISO-8859-1", errors="replace")
        wiersz = {}
        for kod in kodowania:
            try:
                wiersz[kod] = raw.decode(kod, errors="strict")
            except (UnicodeDecodeError, LookupError):
                wiersz[kod] = "— błąd dekodowania —"
        wynik.append(wiersz)
    return wynik
