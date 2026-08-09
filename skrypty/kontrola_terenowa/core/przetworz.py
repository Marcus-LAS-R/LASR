"""Orkiestracja całego "Materiały do kontroli terenowej": łączy
core/ot.py, core/baza_finder.py, core/protokol.py, core/dzkat_kontrola.py,
core/docx_writer.py i core/kml_eksport.py w jeden przebieg wywoływany z
dialogu.

Przebieg:
1. wydz_layer to warstwa, która zawiera WYŁĄCZNIE kontrolowane
   wydzielenia (nie wymaga zaznaczenia ani obecności w TOC) - brane są
   wszystkie jej obiekty. Każdy jest przypisywany do Nadleśnictwa
   (przez zawieranie środka ciężkości w warstwie Nadleśnictw) i do
   konkretnej bazy .mdb (przez dopasowanie ADR_LES, patrz
   baza_finder.py) - wydzielenia bez dopasowania trafiają do
   `raport.niedopasowane_baza` / `raport.niedopasowane_nadl` zamiast
   przerywać całe przetwarzanie.
2. Numery działek (F_AROD_LAND_USE/F_PARCEL) są pobierane raz dla
   całej warstwy - używa ich i protokół (per grupa), i DZKAT_kontrola
   (dla całości).
3. OT.docx i protokół.docx są generowane albo w jednym pliku dla
   całości, albo osobno na Nadleśnictwo - niezależnie dla każdego z
   tych dwóch dokumentów (dwa osobne checkboxy w dialogu).
4. DZKAT_kontrola.shp (podzbiór DZKAT ograniczony do działek
   kontrolowanych wydzieleń) + KML - zawsze jeden wspólny eksport dla
   całości (OBR/wydz_layer/DZKAT_kontrola), zapisywany w katalogu
   docelowym (razem z OT i protokołami).
"""

import os

from qgis.core import QgsSpatialIndex

from ...baza_wrapper import Baza
from ...funkcje import isNone
from . import baza_finder, dzkat_kontrola, docx_writer, kml_eksport, protokol
from .kody import kod_obrebu
from .ot import GeneratorOT

NADL_BRAK = 'Nieprzypisane_do_Nadlesnictwa'


def _naglowek_obrebu(kod_obr, nazwy_obr):
    """'NAZWA (nr obrębu)' - zwykły tekst nad tabelą tego obrębu
    (core/ot_docx.py), nie wiersz w tabeli."""
    return nazwy_obr.get(kod_obr, '') + ' (' + kod_obr[-4:] + ')'


class Raport:
    def __init__(self):
        self.pliki_ot = []
        self.pliki_protokol = []
        self.plik_dzkat_kontrola = None
        self.bledy_kml = []
        self.niedopasowane_baza = []  # etykiety wydzielen bez bazy
        self.niedopasowane_nadl = []  # etykiety wydzielen bez Nadlesnictwa
        self.bledy_baz = []  # bledy polaczenia z bazami


def _bezpieczna_nazwa(tekst):
    return ''.join(c if c.isalnum() else '_' for c in tekst).strip('_') or 'brak_nazwy'


def _etykieta(feat):
    return isNone(feat['ADR_LES']) or ('fid=' + str(feat.id()))


def _przypisz_nadlesnictwa(wydz_features, nadl_layer, pole_nazwy):
    """Zwraca {feat.id(): nazwa_nadlesnictwa}; wydzielenia bez trafienia
    dostają NADL_BRAK."""
    si = QgsSpatialIndex(nadl_layer)
    przypisanie = {}

    for feat in wydz_features:
        srodek = feat.geometry().centroid()
        kandydaci = si.intersects(srodek.boundingBox())

        nazwa = None
        for fid in kandydaci:
            nfeat = nadl_layer.getFeature(fid)
            if nfeat.geometry().contains(srodek):
                nazwa = isNone(nfeat[pole_nazwy])
                break

        if nazwa is None:
            # brzeg wydzielenia moze nie zawierac wlasnego centroidu przy
            # nieregularnej geometrii - dobierz dowolne przecinajace sie
            kandydaci = si.intersects(feat.geometry().boundingBox())
            for fid in kandydaci:
                nfeat = nadl_layer.getFeature(fid)
                if nfeat.geometry().intersects(feat.geometry()):
                    nazwa = isNone(nfeat[pole_nazwy])
                    break

        przypisanie[feat.id()] = nazwa or NADL_BRAK

    return przypisanie


def _grupuj_wg_bazy(wpisy):
    arodes_wg_bazy = {}
    for feat, baza_sc, arodes_int_num in wpisy:
        arodes_wg_bazy.setdefault(baza_sc, []).append(arodes_int_num)
    return arodes_wg_bazy


def _generuj_ot(sciezka_baza, arodes_ids):
    baza = Baza(sciezka_baza)
    if not baza.polacz():
        return None, 'Nie udało się połączyć z bazą: ' + sciezka_baza
    try:
        wynik = GeneratorOT(baza, arodes_ids).generuj()
    finally:
        baza.zamknij()
    return wynik, None


def _pobierz_dzialki(sciezka_baza, arodes_ids):
    baza = Baza(sciezka_baza)
    if not baza.polacz():
        return None, 'Nie udało się połączyć z bazą: ' + sciezka_baza
    try:
        wynik = protokol.pobierz_dzialki(baza, arodes_ids)
    finally:
        baza.zamknij()
    return wynik, None


def uruchom(iface, wydz_layer, dzkat_layer, obr_layer, nadl_layer,
            pole_nazwy_nadl, katalog_bazami, katalog_docelowy,
            ot_razem, protokol_razem):
    raport = Raport()

    # wydz_layer to warstwa TYLKO z kontrolowanymi wydzieleniami -
    # brane sa wszystkie jej obiekty, bez zadnego wymogu zaznaczenia
    wydz_features = list(wydz_layer.getFeatures())

    # --- przypisanie do Nadlesnictwa i do bazy ---
    nadl_po_fid = _przypisz_nadlesnictwa(wydz_features, nadl_layer, pole_nazwy_nadl)

    sciezki_baz = baza_finder.znajdz_bazy(katalog_bazami)
    mapa_wydz, nazwy_gm, nazwy_obr, bledy_baz = baza_finder.zbuduj_mape_wydzielen(sciezki_baz)
    raport.bledy_baz = bledy_baz

    grupy_nadl = {}  # nazwa_nadl -> [(feat, baza_sc, arodes_int_num)]
    for feat in wydz_features:
        adr_les = isNone(feat['ADR_LES'])
        dopasowanie = mapa_wydz.get(adr_les)
        if dopasowanie is None:
            raport.niedopasowane_baza.append(_etykieta(feat))
            continue

        nazwa_nadl = nadl_po_fid.get(feat.id(), NADL_BRAK)
        if nazwa_nadl == NADL_BRAK:
            raport.niedopasowane_nadl.append(_etykieta(feat))

        baza_sc, arodes_int_num = dopasowanie
        grupy_nadl.setdefault(nazwa_nadl, []).append((feat, baza_sc, arodes_int_num))

    wszystkie_wpisy = [w for wpisy in grupy_nadl.values() for w in wpisy]

    # numery dzialek (F_AROD_LAND_USE/F_PARCEL) raz dla calego
    # zaznaczenia - uzywa ich i protokol (per grupa), i DZKAT_kontrola
    dzialki_wg_arodes = {}
    for baza_sc, arodes_ids in _grupuj_wg_bazy(wszystkie_wpisy).items():
        wynik, blad = _pobierz_dzialki(baza_sc, arodes_ids)
        if blad:
            raport.bledy_baz.append(blad)
            continue
        dzialki_wg_arodes.update(wynik)

    os.makedirs(katalog_docelowy, exist_ok=True)

    # --- OT ---
    kat_ot = os.path.join(katalog_docelowy, 'OT')
    os.makedirs(kat_ot, exist_ok=True)

    def _ot_dla_grupy(wpisy, etykieta_pliku, nazwa_naglowek):
        # grupuj najpierw wg obrebu, zeby: (a) wstawic naglowek "NAZWA
        # (nr)" przy kazdej zmianie obrebu, (b) GeneratorOT dostawal na
        # raz wydzielenia z jednego obrebu - ORDER_KEY z bazy poprawnie
        # sortuje oddzialy tylko w obrebie jednego obrebu, wiec mieszanie
        # kilku obrebow w jednym wywolaniu psuloby grupowanie "Razem"
        wpisy_wg_obr = {}
        for feat, baza_sc, arodes_int_num in wpisy:
            wpisy_wg_obr.setdefault(kod_obrebu(feat), []).append(
                (feat, baza_sc, arodes_int_num))

        grupy_obr = []  # [{'naglowek':, 'tabela_ot': [...]}]
        for kod_obr in sorted(wpisy_wg_obr):
            tabela_obr = []
            for baza_sc, arodes_ids in _grupuj_wg_bazy(wpisy_wg_obr[kod_obr]).items():
                wynik, blad = _generuj_ot(baza_sc, arodes_ids)
                if blad:
                    raport.bledy_baz.append(blad)
                    continue
                tabela_obr.extend(wynik)

            if tabela_obr:
                grupy_obr.append({
                    'naglowek': _naglowek_obrebu(kod_obr, nazwy_obr),
                    'tabela_ot': tabela_obr,
                })

        if not grupy_obr:
            return
        sciezka = os.path.join(kat_ot, 'opis_taksacyjny_' + etykieta_pliku + '.docx')
        docx_writer.zapisz_ot(sciezka, nazwa_naglowek, grupy_obr)
        raport.pliki_ot.append(sciezka)

    if ot_razem:
        _ot_dla_grupy(wszystkie_wpisy, 'wszystkie', 'Wszystkie')
    else:
        for nazwa_nadl, wpisy in grupy_nadl.items():
            _ot_dla_grupy(wpisy, _bezpieczna_nazwa(nazwa_nadl), nazwa_nadl)

    # --- protokol ---
    kat_protokol = os.path.join(katalog_docelowy, 'protokoly')
    os.makedirs(kat_protokol, exist_ok=True)

    def _protokol_dla_grupy(wpisy, etykieta_pliku, nazwa_naglowek):
        wpisy_feat_arodes = [(feat, arodes_int_num) for feat, _, arodes_int_num in wpisy]
        wiersze = protokol.zbuduj_dane_protokolu(
            wpisy_feat_arodes, dzialki_wg_arodes, nazwy_obr, nazwy_gm)
        if not wiersze:
            return
        sciezka = os.path.join(kat_protokol, 'protokol_kontroli_' + etykieta_pliku + '.docx')
        docx_writer.zapisz_protokol(sciezka, nazwa_naglowek, wiersze)
        raport.pliki_protokol.append(sciezka)

    if protokol_razem:
        _protokol_dla_grupy(wszystkie_wpisy, 'wszystkie', 'Wszystkie')
    else:
        for nazwa_nadl, wpisy in grupy_nadl.items():
            _protokol_dla_grupy(wpisy, _bezpieczna_nazwa(nazwa_nadl), nazwa_nadl)

    # --- DZKAT_kontrola + kml ---
    warstwy_kml = [(obr_layer, 'OBR'), (wydz_layer, 'WYDZ_kontrola')]

    klucze_dzialek = dzkat_kontrola.zbuduj_klucze_dzialek(wszystkie_wpisy, dzialki_wg_arodes)
    dzkat_kontrola_layer = dzkat_kontrola.zbuduj_warstwe(dzkat_layer, klucze_dzialek)

    if dzkat_kontrola_layer is not None:
        sciezka_shp = os.path.join(katalog_docelowy, 'DZKAT_kontrola.shp')
        dzkat_kontrola.zapisz_shp(dzkat_kontrola_layer, sciezka_shp)
        raport.plik_dzkat_kontrola = sciezka_shp
        warstwy_kml.append((dzkat_kontrola_layer, 'DZKAT_kontrola'))
    else:
        raport.bledy_kml.append(
            'Brak dopasowanych działek (F_AROD_LAND_USE) do zaznaczonych '
            'wydzieleń - DZKAT_kontrola nie powstał, pominięty w '
            'eksporcie KML.')

    raport.bledy_kml.extend(
        kml_eksport.eksportuj_warstwy(iface, warstwy_kml, katalog_docelowy))

    return raport
