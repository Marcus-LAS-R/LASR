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


def _tekst(wartosc):
    """Zamienia wartosc pola (w tym QGIS/Python NULL) na string do
    dalszych operacji tekstowych - NULL/None -> pusty string, NIE
    literalne "None" (str(None) w Pythonie daje wlasnie "None", co bez
    tej funkcji trafialoby wprost do PARCELID/MUNICIP/COUNTY_L przy
    nieuzupelnionych polach zrodlowych)."""
    return "" if wartosc is None else str(wartosc).strip()


def _rzutuj(wartosc, typ_pola):
    """Rzutuje surowa wartosc ze starej warstwy na typ pola docelowego.
    Zwraca (wartosc, blad albo None)."""
    tekst = "" if wartosc is None else str(wartosc).strip()

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


def _zbuduj_mapowanie(typ, src_fields_upper):
    """src_fields_upper: {NAZWA_WIELKIMI: oryginalna_nazwa}

    Dla kazdego pola docelowego probuje po kolei: znane stare warianty
    nazwy (FIELD_MAP), a na koncu ZAWSZE takze dokladnie te sama nazwe co
    docelowa - dzieki temu zrodlo, ktore juz ma czesc kolumn w nowym
    standardzie (albo plik wczesniej juz skonwertowany), zostaje
    przepisane 1:1 zamiast trafic do "brakujacych".
    """
    mapa = FIELD_MAP.get(typ, {})
    mapowanie = {}
    zmapowane = []
    brakujace = []

    for nazwa, _t, _dl, _pr in SCHEMAS[typ]:
        kandydaci = mapa.get(nazwa, []) + [nazwa]
        znaleziono = None
        for k in kandydaci:
            if k.upper() in src_fields_upper:
                znaleziono = src_fields_upper[k.upper()]
                break
        mapowanie[nazwa] = znaleziono
        if znaleziono:
            zmapowane.append((nazwa, znaleziono))
        else:
            brakujace.append(nazwa)

    return mapowanie, zmapowane, brakujace


def _dz_lacznik(county, district, municip, community, ark, parcelnr):
    if ark not in ("", " "):
        return county + district + municip + community + "." + ark + \
            "." + parcelnr
    return county + district + municip + community + "." + parcelnr


def konwertuj_warstwe(lyr, typ, folder_wyjsciowy):  # noqa
    """Konwertuje pojedyncza warstwe na nowy standard `typ`, zapisujac
    wynik do `folder_wyjsciowy` (wybrany przez uzytkownika w dialogu).

    Zwraca dict raportu: nazwa, typ, sciezka, obiekty, pola_zmapowane
    (lista par (nowe, stare)), pola_brakujace (lista nazw), bledy (lista
    opisow).
    """
    raport = {
        "nazwa": lyr.name(),
        "typ": typ,
        "sciezka": None,
        "obiekty": 0,
        "pola_zmapowane": [],
        "pola_brakujace": [],
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

    writer = QgsVectorFileWriter(
        sciezka_wy, "UTF-8", qf, lyr.wkbType(), lyr.crs(), "ESRI Shapefile")
    if writer.hasError() != QgsVectorFileWriter.NoError:
        raport["bledy"].append(
            "Nie udało się utworzyć pliku wyjściowego: " +
            str(writer.errorMessage())
        )
        return raport

    mapowanie, zmapowane, brakujace = _zbuduj_mapowanie(typ, src_fields_upper)
    raport["pola_zmapowane"] = zmapowane
    raport["pola_brakujace"] = brakujace

    # ODDZ: MUNICIP/COMMUNITY moga byc juz wprost w zrodle (nowy standard,
    # albo stary plik "ODDZ" ktory zwykle ma pole ODDZ wprost) - wtedy
    # zalatwia to _zbuduj_mapowanie powyzej. Jesli nie ma ich wprost,
    # sprobuj wyliczyc z "golego" kodu TERYT obrebu (idobrebu/jpt_kod_je/
    # g5nro), tak jak robi to shp_przygCiecie.py. Samo ODDZ nigdy nie da
    # sie wyliczyc z danych obrebu - zawsze wymaga uzupelnienia (np.
    # "Zanumeruj oddziały").
    kandydat_teryt = None
    uzyj_teryt_municip = False
    uzyj_teryt_community = False
    if typ == "ODDZ":
        for k in OBR_TERYT_KANDYDACI:
            if k in src_fields_upper:
                kandydat_teryt = src_fields_upper[k]
                break

    if kandydat_teryt:
        uzyj_teryt_municip = mapowanie.get("MUNICIP") is None
        uzyj_teryt_community = mapowanie.get("COMMUNITY") is None
        if uzyj_teryt_municip:
            raport["pola_brakujace"] = [
                x for x in raport["pola_brakujace"] if x != "MUNICIP"]
            raport["pola_zmapowane"].append(
                ("MUNICIP", f"{kandydat_teryt} (kod TERYT, wyliczone)"))
        if uzyj_teryt_community:
            raport["pola_brakujace"] = [
                x for x in raport["pola_brakujace"] if x != "COMMUNITY"]
            raport["pola_zmapowane"].append(
                ("COMMUNITY", f"{kandydat_teryt} (kod TERYT, wyliczone)"))

    czy_parcelid = typ in ("DZKAT", "LS") and mapowanie.get("PARCELID") is None

    # DZKAT: 1 obiekt = 1 cała działka, więc PARCEL_POW da się bezpiecznie
    # policzyć wprost z geometrii (tak jak w przygotuj_dzkat.py). W LS
    # geometria pojedynczego obiektu to tylko fragment użytku, więc tak
    # liczymy co najwyżej LAND_POW (powierzchnia tego fragmentu), nie
    # PARCEL_POW (powierzchnia całej działki).
    czy_parcel_pow_z_geom = (
        typ == "DZKAT" and mapowanie.get("PARCEL_POW") is None)
    czy_land_pow_z_geom = typ == "LS" and mapowanie.get("LAND_POW") is None
    czy_county_l_z_tabeli = (
        typ in ("WYDZ", "WYDZ_POL") and mapowanie.get("COUNTY_L") is None
        and mapowanie.get("COUNTY"))
    # KLU = zlozenie AU+SQ (jak dopisuje przygotuj_ls.py), tylko gdy zrodlo
    # nie ma juz gotowej kolumny KLU
    czy_klu_z_au_sq = typ == "KLU" and mapowanie.get("KLU") is None

    for feat in lyr.getFeatures():
        nf = QgsFeature(qf)
        nf.setGeometry(feat.geometry())

        for nowe, stare in mapowanie.items():
            if not stare:
                continue
            typ_pola, dlugosc = _typ_pola(typ, nowe)
            wartosc, blad = _rzutuj(feat[stare], typ_pola)
            if blad and len(raport["bledy"]) < 50:
                raport["bledy"].append(
                    f"obiekt {feat.id()}: {stare} -> {nowe} ({blad})")
            if typ_pola == "String" and dlugosc and len(str(wartosc)) > dlugosc:
                if len(raport["bledy"]) < 50:
                    raport["bledy"].append(
                        f"obiekt {feat.id()}: {nowe} przycięte do "
                        f"{dlugosc} znaków (było: {wartosc!r})"
                    )
                wartosc = str(wartosc)[:dlugosc]
            nf[nowe] = wartosc

        # dolicz WYDZ/WYDZ_POL: COUNTY_L z tabeli wojewodztw na podstawie
        # COUNTY, ale tylko gdy zrodlo nie mialo juz wprost kolumny COUNTY_L
        if czy_county_l_z_tabeli:
            nf["COUNTY_L"] = SL_WOJ.get(_tekst(nf["COUNTY"]), "")

        # MUNICIP/COMMUNITY wyliczone z "golego" kodu TERYT obrebu, gdy
        # nie bylo ich wprost w zrodle
        if uzyj_teryt_municip or uzyj_teryt_community:
            try:
                val = _tekst(feat[kandydat_teryt])
                if uzyj_teryt_municip:
                    nf["MUNICIP"] = val[4:8].replace("_", "")
                if uzyj_teryt_community:
                    nf["COMMUNITY"] = val[-4:]
            except Exception as e:  # nopep8
                if len(raport["bledy"]) < 50:
                    raport["bledy"].append(
                        f"obiekt {feat.id()}: nie udało się rozbić "
                        f"kodu TERYT: {e}"
                    )

        if czy_parcel_pow_z_geom:
            nf["PARCEL_POW"] = round(feat.geometry().area() / 10000, 4)
        if czy_land_pow_z_geom:
            nf["LAND_POW"] = round(feat.geometry().area() / 10000, 4)

        # KLU = AU+SQ, gdy zrodlo nie mialo juz gotowej kolumny KLU
        if czy_klu_z_au_sq:
            nf["KLU"] = (_tekst(nf["AU"]) + _tekst(nf["SQ"]))[:15]

        # dolicz PARCELID gdy brak w zrodle, ze skladowych identycznie jak
        # w przygotuj_dzkat.py / przygotuj_ls.py
        if czy_parcelid:
            try:
                lacznik = _dz_lacznik(
                    _tekst(nf["COUNTY"]),
                    _tekst(nf["DISTRICT"]),
                    _tekst(nf["MUNICIP"]),
                    _tekst(nf["COMMUNITY"]),
                    _tekst(nf["ARK"]),
                    _tekst(nf["PARCELNR"]),
                )
                nf["PARCELID"] = lacznik[:50]
            except Exception:  # nopep8
                pass

        writer.addFeature(nf)
        raport["obiekty"] += 1

    del writer

    if czy_parcelid:
        # PARCELID jednak zostal wyliczony (nie jest to "brak zrodla" tylko
        # pole dorobione automatycznie) - zaznacz to w raporcie
        raport["pola_brakujace"] = [
            x for x in raport["pola_brakujace"] if x != "PARCELID"]
        raport["pola_zmapowane"].append(
            ("PARCELID", "(wyliczone z COUNTY+DISTRICT+MUNICIP+"
                          "COMMUNITY+ARK+PARCELNR)"))

    if czy_parcel_pow_z_geom:
        raport["pola_brakujace"] = [
            x for x in raport["pola_brakujace"] if x != "PARCEL_POW"]
        raport["pola_zmapowane"].append(
            ("PARCEL_POW", "(wyliczone z geometrii)"))

    if czy_land_pow_z_geom:
        raport["pola_brakujace"] = [
            x for x in raport["pola_brakujace"] if x != "LAND_POW"]
        raport["pola_zmapowane"].append(
            ("LAND_POW", "(wyliczone z geometrii)"))

    if czy_county_l_z_tabeli:
        raport["pola_brakujace"] = [
            x for x in raport["pola_brakujace"] if x != "COUNTY_L"]
        raport["pola_zmapowane"].append(
            ("COUNTY_L", "(wyliczone z COUNTY wg tabeli województw)"))

    if czy_klu_z_au_sq:
        raport["pola_brakujace"] = [
            x for x in raport["pola_brakujace"] if x != "KLU"]
        raport["pola_zmapowane"].append(("KLU", "(wyliczone z AU+SQ)"))

    raport["sciezka"] = sciezka_wy
    return raport


# --- automatyczne zgadywanie kodowania odczytu grupy warstw ---------------
#
# Pliki .cpg starych shapefile'i bywaja bledne (potwierdzone na probce
# materialy/shp_stary_standard - .cpg deklaruje "UTF-8", a surowe bajty w
# DBF sa w rzeczywistosci Windows-1250), wiec zamiast im ufac probkujemy
# realne wartosci tekstowe i sprawdzamy, ktore z typowych dla polskich
# danych kodowan daje sensowny tekst.

KANDYDACI_KODOWAN = ["CP1250", "UTF-8", "ISO-8859-2", "CP852"]

_POLSKIE_ZNAKI = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
# znaki sterujace (poza tab/lf/cr) i znak zastepczy - ich obecnosc po
# dekodowaniu oznacza prawie na pewno zle dobrane kodowanie
_ZNAKI_SMIECIOWE = {chr(c) for c in range(32) if c not in (9, 10, 13)}
_ZNAKI_SMIECIOWE.add("�")


def _probka_wartosci(lyr, ile_obiektow=200):
    """Zwraca liste stringow z pol tekstowych warstwy, odczytanych tak,
    zeby zachowac oryginalne bajty (kodowanie ISO-8859-1 mapuje kazdy
    bajt 1:1 na znak, wiec `wartosc.encode('ISO-8859-1')` odtwarza
    dokladnie to, co bylo w pliku, niezaleznie od prawdziwego kodowania)
    - do testowania kandydujacych kodowan."""
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
                if w:
                    wartosci.append(str(w))

    lyr.dataProvider().setEncoding(poprzednie)
    return wartosci


def _ocen_kodowanie(wartosci, kodowanie):
    """Probuje zdekodowac probke (stringi z `_probka_wartosci`) danym
    kodowaniem. Zwraca (czy_bez_bledow, liczba_polskich_znakow,
    liczba_smieciowych_znakow)."""
    bez_bledow = True
    polskie = 0
    smieci = 0
    for w in wartosci:
        raw = w.encode("ISO-8859-1", errors="replace")
        try:
            dekodowane = raw.decode(kodowanie, errors="strict")
        except (UnicodeDecodeError, LookupError):
            bez_bledow = False
            continue
        polskie += sum(1 for ch in dekodowane if ch in _POLSKIE_ZNAKI)
        smieci += sum(1 for ch in dekodowane if ch in _ZNAKI_SMIECIOWE)
    return bez_bledow, polskie, smieci


def zgadnij_kodowanie(warstwy):
    """Zgaduje wspolne kodowanie dla grupy warstw (np. wszystkich
    zaznaczonych w dialogu konwersji) na podstawie probki wartosci
    tekstowych. Zwraca nazwe kodowania z `KANDYDACI_KODOWAN`, albo None,
    jesli nie udalo sie zebrac zadnej probki (np. same pola numeryczne
    albo warstwy bez obiektow)."""
    wszystkie_wartosci = []
    for lyr in warstwy:
        wszystkie_wartosci += _probka_wartosci(lyr)

    if not wszystkie_wartosci:
        return None

    wyniki = [
        (kandydat,) + _ocen_kodowanie(wszystkie_wartosci, kandydat)
        for kandydat in KANDYDACI_KODOWAN
    ]
    # priorytet: brak bledow dekodowania > najwiecej polskich znakow >
    # najmniej smieciowych znakow > kolejnosc w KANDYDACI_KODOWAN (stabilne
    # sortowanie - przy remisie wygrywa CP1250, historyczny domyslny
    # standard tego zestawu danych)
    wyniki.sort(key=lambda w: (not w[1], -w[2], w[3]))
    return wyniki[0][0]


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
