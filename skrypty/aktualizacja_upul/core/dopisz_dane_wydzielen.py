"""Dopisywanie danych do wydzieleń na podstawie starych punktów
(odpowiednik "Join attributes by location", ale zapisujący wynik od razu
do wskazanej warstwy docelowej zamiast tworzyć nową warstwę).

Dopasowanie jest przestrzenne typu punkt-w-poligonie: dla każdego obiektu
warstwy docelowej (WYDZ) szukamy punktów warstwy źródłowej
(WYDZ_PKT_stare) leżących w jego granicach. Wydzielenia, w których trafił
więcej niż jeden stary punkt (scalenie kilku starych wydzieleń w jedno
nowe) są pomijane i zgłaszane w raporcie - nie ma jednoznacznego wyboru,
którego punktu dane wpisać.
"""

from qgis.core import QgsSpatialIndex

TRYB_PUSTE = 'puste'
TRYB_NADPISZ = 'nadpisz'

_PUSTE_WARTOSCI = ('', ' ', 'NULL', None)


def _puste(wartosc):
    return wartosc in _PUSTE_WARTOSCI or (
        isinstance(wartosc, str) and wartosc.strip() == '')


def _etykieta_obiektu(f):
    """Krótki opis wydzielenia do raportu - ODDZ/WYDZ, jeśli warstwa ma
    takie pola, w przeciwnym razie numer obiektu (fid)."""
    nazwy_pol = {pole.name() for pole in f.fields()}
    if {'ODDZ', 'WYDZ'}.issubset(nazwy_pol):
        return f"{f['ODDZ']}{f['WYDZ']}"
    return f"fid={f.id()}"


def wykonaj(zrodlo_lyr, cel_lyr, wybor_pol):
    """Dopisuje dane z `zrodlo_lyr` (punkty) do `cel_lyr` (poligony).

    Args:
        zrodlo_lyr: Warstwa punktowa ze starymi danymi (np. WYDZ_PKT_stare).
        cel_lyr: Warstwa poligonowa, do której wpisujemy dane (np. WYDZ).
        wybor_pol: Lista (nazwa_pola, tryb) - tryb to TRYB_PUSTE (wpisuj
            tylko gdy pole docelowe jest puste) albo TRYB_NADPISZ (zawsze
            nadpisz wartością ze źródła).

    Returns:
        Słownik z podsumowaniem: zaktualizowane (int), scalenia_pominiete
        (lista etykiet), pola_pominiete (lista nazw pól spoza cel_lyr),
        zmiany_na_pole (słownik nazwa_pola -> liczba zmienionych wartości).
    """
    raport = {
        'zaktualizowane': 0,
        'scalenia_pominiete': [],
        'pola_pominiete': [],
        'zmiany_na_pole': {},
    }

    nazwy_pol_cel = {pole.name() for pole in cel_lyr.fields()}
    do_zapisu = []
    for nazwa, tryb in wybor_pol:
        if nazwa not in nazwy_pol_cel:
            raport['pola_pominiete'].append(nazwa)
            continue
        do_zapisu.append((nazwa, tryb))

    if not do_zapisu:
        return raport

    si = QgsSpatialIndex()
    zrodlo_pkt = {}
    for f in zrodlo_lyr.getFeatures():
        si.insertFeature(f)
        zrodlo_pkt[f.id()] = f

    fnm = cel_lyr.dataProvider().fieldNameMap()
    zmiany = {}
    zmiany_na_pole = {nazwa: 0 for nazwa, _ in do_zapisu}

    for f in cel_lyr.getFeatures():
        geom = f.geometry()
        kandydaci = si.intersects(geom.boundingBox())
        trafienia = [
            idk for idk in kandydaci
            if geom.contains(zrodlo_pkt[idk].geometry())
        ]

        if len(trafienia) == 0:
            continue
        if len(trafienia) > 1:
            raport['scalenia_pominiete'].append(_etykieta_obiektu(f))
            continue

        pkt = zrodlo_pkt[trafienia[0]]
        wpis = {}
        for nazwa, tryb in do_zapisu:
            if tryb == TRYB_PUSTE and not _puste(f[nazwa]):
                continue
            wpis[fnm[nazwa]] = pkt[nazwa]
            zmiany_na_pole[nazwa] += 1
        if wpis:
            zmiany[f.id()] = wpis

    if zmiany:
        cel_lyr.startEditing()
        for fid, wpis in zmiany.items():
            cel_lyr.dataProvider().changeAttributeValues({fid: wpis})
        cel_lyr.commitChanges()

    raport['zaktualizowane'] = len(zmiany)
    raport['zmiany_na_pole'] = zmiany_na_pole
    return raport
