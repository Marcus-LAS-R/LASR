# -*- coding: utf-8 -*-
"""NTG - przygotowanie warstw i bazy obiektu (bez Qt-owych okien).

Przebieg (gui/przygotuj_dialog.py woła kolejne kroki):
1. szukaj_folderow_shp: w folderze obiektu każdy folder z WYDZ.shp to
   źródło warstw (pomijane foldery jak w Połącz bazy TPU: '_*', arch*,
   kopi*, oraz folder eksportu);
2. polacz_warstwy: WYDZ, ODDZ, LS -> <eksport>\\SHP przez
   shp_polacz_warstwy.polacz_warstwe (EPSG:2180, duplikaty geometrii
   usuwane); GMIN i OBR najpierw do folderu roboczego;
3. polacz_bazy: jak Połącz bazy TPU (baza_polacz.Laczenie, wszystkie
   grupy tabel, bez filtra obrębów), z blokującą kontrolą duplikatów
   wydzieleń i działek; jedna baza = zwykła kopia;
4. wytnij_objete: zostają tylko gminy/obręby, w których połączona baza
   ma wydzielenia (obreby_z_bazy - kody TERYT, nie geometria),
   nadleśnictwa - tylko przecinające zasięg gmin obiektu (z zapasem
   ZAPAS_NADL, żeby na mapie były też sąsiednie);
   Połączona baza od razu anonimizowana (baza_anonimizuj.anonimizuj_baze,
   kwerendy zostają) - stąd nazwa Baza_NTG_polaczona_BDO.mdb; bazy
   źródłowe nietknięte;
5. dopisz_metadane: WYDZ_DOPISANE jak "Dopisz metadane"
   (shp_dopisz_kody.DopiszKody) z połączonej bazy.
Wynik: <eksport>\\SHP, <eksport>\\Baza_NTG_polaczona_BDO.mdb,
<eksport>\\Raporty - bez projektu QGIS (mapy robi "Generuj mapy" w bieżącym projekcie).
"""
import os
import shutil
from datetime import datetime

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature,
    QgsFeatureRequest, QgsGeometry, QgsProject, QgsRectangle,
    QgsVectorLayer, QgsWkbTypes,
)

from ... import funkcje
from ... import shp_polacz_warstwy as pw
from ...baza_polacz import (
    Laczenie, _kontrola_duplikatow_dzialek, _kontrola_duplikatow_wydzieln)
from ...baza_polacz_rejestr import rejestr_domyslny
from ...baza_polacz_wyszukaj import pomin_folder
from ...baza_wrapper import Baza

EPSG = "EPSG:2180"
FOLDER_EKSPORTU = "_NTG"          # '_' -> pomijany przy szukaniu danych
FOLDER_SHP = "SHP"
FOLDER_ROBOCZY = "_robocze"
NAZWA_BAZY = "Baza_NTG_polaczona_BDO.mdb"   # zanonimizowana, kwerendy zostają
NAZWA_BAZY_STARA = "UPUL.mdb"     # wcześniejsze wersje - bez anonimizacji
NAZWA_NADL = "NADL"

WARSTWY_LACZONE = ("WYDZ", "ODDZ", "LS")      # wprost do SHP
WARSTWY_WYCINANE = ("GMIN", "OBR")           # łączone, potem wycinane
ZAPAS_NADL = 0.25                            # część szerokości/wysokości


# ---------------------------------------------------------------- szukanie

def _wewnatrz(sciezka, katalog):
    s, k = os.path.normcase(os.path.abspath(sciezka)), \
        os.path.normcase(os.path.abspath(katalog))
    return s == k or s.startswith(k + os.sep)


def szukaj_folderow_shp(obiekt, eksport=None):
    """[(folder względny, {NAZWA: ścieżka .shp})] - foldery z WYDZ.shp."""
    wyn = []
    for folder, podfoldery, _ in os.walk(obiekt):
        podfoldery[:] = sorted(
            p for p in podfoldery if not pomin_folder(p) and
            not (eksport and _wewnatrz(os.path.join(folder, p), eksport)))
        warstwy = pw.warstwy_w_folderze(folder)
        if "WYDZ" in warstwy:
            wyn.append((os.path.relpath(folder, obiekt), warstwy))
    return wyn


def zrodla_warstw(foldery_shp):
    """{NAZWA: [(folder, ścieżka)]} - format shp_polacz_warstwy."""
    wyn = {}
    for folder, warstwy in foldery_shp:
        for nazwa, sciezka in sorted(warstwy.items()):
            wyn.setdefault(nazwa, []).append((folder, sciezka))
    return wyn


# ---------------------------------------------------------------- warstwy

def polacz_warstwy(zrodla, nazwy, folder, postep=None):
    """Łączy warstwy (bez szukania nakładań). Zwraca listę wyników
    polacz_warstwe albo None, gdy przerwano."""
    os.makedirs(folder, exist_ok=True)
    wyniki = []
    for nazwa in nazwy:
        if nazwa not in zrodla:
            continue
        r = pw.polacz_warstwe(nazwa, zrodla[nazwa], folder, True, False,
                              postep)
        if r is None:
            return None
        wyniki.append(r)
    return wyniki


def _cyfry(wartosc):
    return "".join(c for c in str(wartosc or "") if c.isdigit())


def obreby_z_bazy(baza_sc):
    """Obręby z wydzieleniami w bazie (F_AROD_LAND_USE -> F_PARCEL) jako
    11 cyfr TERYT: WWPPGG+R+OOOO (= kod obrębu bez '_' i '.', np.
    180404_2.0007 -> 18040420007). Pierwsze 7 cyfr to kod gminy."""
    baza = Baza(baza_sc)
    if not baza.polacz():
        raise RuntimeError("Nie udało się połączyć z bazą " + baza_sc)
    try:
        wiersze = baza.pobierz(
            "select distinct p.COUNTY_CD, p.DISTRICT_CD, p.MUNICIPALITY_CD, "
            "p.COMMUNITY_CD from (F_AROD_LAND_USE as l inner join F_PARCEL "
            "as p on l.PARCEL_INT_NUM = p.PARCEL_INT_NUM);")
    finally:
        baza.zamknij()
    if not wiersze:
        raise RuntimeError("W bazie nie ma wydzieleń z działkami "
                           "(F_AROD_LAND_USE/F_PARCEL) - nie da się ustalić "
                           "obrębów obiektu")
    kody = set()
    for w in wiersze:
        kod = "".join(str(x or "").strip() for x in w)
        if len(kod) == 11 and kod.isdigit():
            kody.add(kod)
    return kody


def _do_2180(lyr):
    crs = QgsCoordinateReferenceSystem(EPSG)
    if not lyr.crs().isValid() or lyr.crs() == crs:
        return None
    return QgsCoordinateTransform(lyr.crs(), crs,
                                  QgsProject.instance().transformContext())


def wytnij_objete(zrodlo_sc, cel_sc, kody=None, pole_kodu=None,
                  dlugosc=None, prostokat=None, nazwa=None):
    """Zapisuje do cel_sc (UTF-8, EPSG:2180) obiekty zrodlo_sc:
    - z kodami: te, których pierwsze `dlugosc` cyfr pola_kodu jest wśród
      kodów (kody przycięte do tej samej długości),
    - z prostokątem (EPSG:2180): te, które go przecinają.
    Zwraca (zapisane, odrzucone, bez_kodu, znalezione kody) albo zgłasza
    RuntimeError."""
    lyr = QgsVectorLayer(zrodlo_sc, nazwa or "warstwa", "ogr")
    if not lyr.isValid():
        raise RuntimeError("Nie da się otworzyć warstwy " + zrodlo_sc)
    tr = _do_2180(lyr)
    zadanie = QgsFeatureRequest()
    if prostokat is not None:
        zasieg = QgsRectangle(prostokat)
        if tr is not None:
            zasieg = tr.transformBoundingBox(
                zasieg, QgsCoordinateTransform.ReverseTransform)
        zadanie.setFilterRect(zasieg)
        geom_prost = QgsGeometry.fromRect(prostokat)
    if kody is not None:
        szukane = {k[:dlugosc] for k in kody}

    typ = QgsWkbTypes.multiType(lyr.wkbType())
    mem = QgsVectorLayer("%s?crs=%s" % (QgsWkbTypes.displayString(typ), EPSG),
                         nazwa or "warstwa", "memory")
    mem.dataProvider().addAttributes(lyr.fields().toList())
    mem.updateFields()

    zostaw, bez_kodu, znalezione = [], 0, set()
    for f in lyr.getFeatures(zadanie):
        g = QgsGeometry(f.geometry())
        if g.isNull():
            continue
        if tr is not None:
            g.transform(tr)
        if kody is not None:
            kod = _cyfry(f[pole_kodu])
            if len(kod) < dlugosc:
                bez_kodu += 1
                continue
            if kod[:dlugosc] not in szukane:
                continue
            znalezione.add(kod[:dlugosc])
        if prostokat is not None and not g.intersects(geom_prost):
            continue
        g.convertToMultiType()
        nf = QgsFeature(mem.fields())
        nf.setGeometry(g)
        nf.setAttributes(f.attributes())
        zostaw.append(nf)
    mem.dataProvider().addFeatures(zostaw)
    ok, kom = funkcje.zapisz_shp_utf8(mem, cel_sc)
    if not ok:
        raise RuntimeError("Nie zapisano %s: %s" % (cel_sc, kom))
    return (len(zostaw), lyr.featureCount() - len(zostaw), bez_kodu,
            znalezione)


def opis_kodu(kod):
    """'18040420007' -> '180404_2.0007 Pełkinie (gm. Jarosław)',
    '1804042' -> '180404_2 Jarosław' - nazwy ze słownika TERYT wtyczki."""
    from ... import teryt_obreby
    if len(kod) == 11:
        id_obr = "%s_%s.%s" % (kod[:6], kod[6], kod[7:])
        wpis = teryt_obreby.wczytaj().get(id_obr)
        return id_obr + (" %s (gm. %s)" % (wpis[0], wpis[1]) if wpis else "")
    id_j = "%s_%s" % (kod[:6], kod[6])
    wpis = teryt_obreby.jednostka(id_j)
    return id_j + (" " + wpis[0] if wpis else "")


def zasieg_z_zapasem(sciezka, zapas=ZAPAS_NADL):
    lyr = QgsVectorLayer(sciezka, "z", "ogr")
    r = QgsRectangle(lyr.extent())
    r.grow(max(r.width(), r.height()) * zapas)
    return r


# ---------------------------------------------------------------- bazy

def polacz_bazy(bazy, cel_sc, katalog_raportow):
    """Łączy bazy do cel_sc. Zwraca (ok, komunikat, bledy) - bledy to
    lista (baza, tabela, wiersz, błąd). Przy duplikatach wydzieleń/działek
    nic nie łączy (ok=False, komunikat z raportem)."""
    bazy = sorted(bazy)
    if len(bazy) == 1:
        shutil.copyfile(bazy[0], cel_sc)
        return True, "skopiowano jedyną bazę: " + bazy[0], []

    os.makedirs(katalog_raportow, exist_ok=True)
    for fn, opis in ((_kontrola_duplikatow_wydzieln, "wydzieleń"),
                     (_kontrola_duplikatow_dzialek, "działek")):
        dup, rap = fn(katalog_raportow, bazy)
        if dup:
            return (False, "%d zdublowanych %s w bazach - raport: %s"
                    % (len(dup), opis, rap), [])

    shutil.copyfile(bazy[0], cel_sc)
    baza0 = Baza(cel_sc)
    if not baza0.polacz():
        return False, "Nie udało się połączyć z bazą " + cel_sc, []
    bledy = []
    try:
        for sc in bazy[1:]:
            zrodlo = Baza(sc)
            if not zrodlo.polacz():
                bledy.append((sc, "", "", "nie udało się połączyć z bazą"))
                continue
            lacz = Laczenie(baza0, zrodlo, rejestr_domyslny())
            lacz.p_f_max()
            lacz.p_f_arodes()
            lacz.p_f_community()
            lacz.p_pozostale_nadrzedne()
            lacz.p_tabele()
            lacz.d_tabele()
            for tabela, wiersz, blad in lacz.l_bledy_wpisu:
                bledy.append((sc, tabela, wiersz, blad))
            for bsc, tabela, blad in lacz.l_bledy_odczytu:
                bledy.append((bsc, tabela, "(cała tabela - błąd odczytu)",
                              blad))
            zrodlo.zamknij()
    finally:
        baza0.zamknij()
    return True, "połączono %d baz" % len(bazy), bledy


# ---------------------------------------------------------------- WYDZ_DOPISANE

def dopisz_metadane(iface, wydz_sc, baza_sc):
    """WYDZ_DOPISANE obok WYDZ (DopiszKody bez wyboru warstwy/bazy).
    Zwraca ścieżkę albo zgłasza RuntimeError."""
    from ...shp_dopisz_kody import DopiszKody
    d = DopiszKody(iface)
    d.wydz = QgsVectorLayer(wydz_sc, "WYDZ", "ogr")
    d.wydz_path = wydz_sc
    d.kat = os.path.dirname(wydz_sc)
    d.baza = Baza(baza_sc)
    if not d.pobierzBaze():
        raise RuntimeError("Nie udało się odczytać danych z bazy " + baza_sc)
    d.dopisz_kody()
    wpol = getattr(d, "wpol", None)
    if wpol is None:
        raise RuntimeError("Nie utworzono WYDZ_DOPISANE")
    # DopiszKody dodaje warstwę do bieżącego projektu - tu niepotrzebna
    if QgsProject.instance().mapLayer(wpol.id()):
        QgsProject.instance().removeMapLayer(wpol.id())
    return os.path.join(d.kat, "WYDZ_DOPISANE.shp")


# ---------------------------------------------------------------- raport

def zapisz_raport(eksport, linie, nazwa="przygotuj", skrot="NTG"):
    kat = os.path.join(eksport, "Raporty")
    os.makedirs(kat, exist_ok=True)
    sc = os.path.join(kat, "raport_%s_%s_%s.txt"
                      % (nazwa, skrot,
                         datetime.now().strftime("%Y%m%dT%H%M%S")))
    with open(sc, "w", encoding="utf-8") as f:
        f.write("\n".join(linie))
    return sc
