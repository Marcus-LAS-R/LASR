"""Silnik "Rozdziel bazy na UPUL i ISL".

Obręby ewidencyjne bazy dzielone są na dwie grupy według sumarycznej
powierzchni użytku LS (ta sama suma co kwerenda "suma użytków LS
w poszczególnych obrębach geodezyjnych", ale liczona w kodzie, z pełnym
kluczem obrębu - skrypt nie zależy od tego, czy kwerenda jest w bazie):
- ISL  - obręby z sumą LS < 10,0000 ha (tryb automatyczny) albo wskazane
         ręcznie,
- UPUL - pozostałe obręby z LS.
Obręby bez żadnego użytku LS są usuwane z OBU baz.

Baza źródłowa nie jest zmieniana - powstają dwie kopie pliku
(<nazwa>_UPUL / <nazwa>_ISL), z których usuwane są obręby drugiej grupy:
działki z tabelami zależnymi (po PARCEL_INT_NUM), wydzielenia z tabelami
zależnymi (po ARODES_INT_NUM, przypisanie do obrębu wg adresu leśnego),
osierocone wiersze adresowe (ODDZ/L-CTWO/OBRĘB), właściciele bez działek
i wiersze F_COMMUNITY.

Adres leśny UPUL: COUNTY_L[0] DISTRICT[1:3] MUNICIP[3:6] COMMUNITY[6:10]
(patrz shp_adr_les.zbuduj_adres) - litera województwa jest pomijana przy
dopasowaniu do obrębu (DISTRICT+MUNICIP+COMMUNITY).
"""

import os
import re
import shutil
from datetime import datetime

from qgis.core import (
    Qgis, QgsMessageLog, QgsProject, QgsVectorFileWriter, QgsVectorLayer,
)

PROG_ISL = 10.0  # ha - obręby z sumą LS PONIŻEJ progu idą do ISL

UPUL = 'UPUL'
ISL = 'ISL'
BEZ_LS = 'BEZ_LS'

_ROZMIAR_PORCJI = 200  # limit parametrów w zapytaniu IN (...) dla Jet/ACE
_TYPY_ADRESOWE = ('WYDZIEL', 'ODDZ', 'L-CTWO')
_ROZSZERZENIA_STYLU = ('.qml', '.qmd')

# pola z identyfikatorem TERYT obiektów EGiB/PRG (wielkie litery - patrz
# _pola) i wzorzec WWPPGG_R.OOOO
_POLA_TERYT = ('IDDZIALKI', 'IDOBREBU', 'IDUZYTKU', 'IDKONTURU', 'G5IDD',
               'G5NRO', 'G5IDR', 'IDENTYFIKA', 'JPT_KOD_JE')
_WZORZEC_TERYT = re.compile(r'(\d{2})(\d{2})(\d{2})_(\d)\.(\d{4})')


def _porcje(wartosci, rozmiar=_ROZMIAR_PORCJI):
    wartosci = sorted(wartosci)
    for i in range(0, len(wartosci), rozmiar):
        yield wartosci[i:i + rozmiar]


def _txt(w):
    return '' if w is None else str(w).strip()


def _klucz(county, district, municip, community):
    return (_txt(county), _txt(district), _txt(municip), _txt(community))


def klucz_tekst(klucz):
    """(16, 09, 085, 0001) -> '16090850001' (jak prefiks PARCELID)."""
    return ''.join(klucz)


def klucz_adresu(adr):
    """(DISTRICT, MUNICIP, COMMUNITY) z adresu leśnego UPUL albo None, gdy
    adres nie ma pełnego kodu obrębu (np. wiersz OBRĘB - sama gmina)."""
    adr = adr or ''
    if len(adr) < 10:
        return None
    k = (adr[1:3], adr[3:6], adr[6:10])
    if not all(c.isdigit() for c in ''.join(k)):
        return None
    return k


# --------------------------------------------------------------------------
# odczyt obrębów i sum LS
# --------------------------------------------------------------------------

class Obreb:
    def __init__(self, klucz, nazwa='', gmina=''):
        self.klucz = klucz
        self.nazwa = nazwa
        self.gmina = gmina
        self.pow_ls = 0.0
        self.dzialki = 0

    @property
    def ma_ls(self):
        return self.pow_ls > 0

    def grupa_auto(self):
        if not self.ma_ls:
            return BEZ_LS
        return ISL if self.pow_ls < PROG_ISL else UPUL


def pobierz_obreby(baza):
    """Zwraca listę Obreb (F_COMMUNITY + obręby występujące tylko
    w F_PARCEL), posortowaną po kluczu, z sumą LS zaokrągloną do 4 miejsc
    (sumy z Accessa bywają "brudne", np. 9.99999999 - bez zaokrąglenia
    obręb z dokładnie 10 ha mógłby trafić do ISL)."""
    obreby = {}

    gminy = {}
    w = baza.pobierz(
        'select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, MUNICIPALITY_NAME '
        'from F_MUNICIPALITY;')
    for county, district, municip, nazwa in (w or []):
        gminy[_klucz(county, district, municip, '')[:3]] = _txt(nazwa)

    w = baza.pobierz(
        'select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, '
        'COMMUNITY_NAME from F_COMMUNITY;')
    for county, district, municip, community, nazwa in (w or []):
        k = _klucz(county, district, municip, community)
        obreby[k] = Obreb(k, _txt(nazwa), gminy.get(k[:3], ''))

    w = baza.pobierz(
        'select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, '
        'count(*) from F_PARCEL group by COUNTY_CD, DISTRICT_CD, '
        'MUNICIPALITY_CD, COMMUNITY_CD;')
    for county, district, municip, community, ile in (w or []):
        k = _klucz(county, district, municip, community)
        if k not in obreby:
            obreby[k] = Obreb(k, '', gminy.get(k[:3], ''))
        obreby[k].dzialki = ile

    w = baza.pobierz(
        'select P.COUNTY_CD, P.DISTRICT_CD, P.MUNICIPALITY_CD, '
        'P.COMMUNITY_CD, U.AREA_USE_CD, sum(U.LAND_USE_AREA) '
        'from F_PARCEL P inner join F_PARCEL_LAND_USE U '
        'on P.PARCEL_INT_NUM = U.PARCEL_INT_NUM '
        'group by P.COUNTY_CD, P.DISTRICT_CD, P.MUNICIPALITY_CD, '
        'P.COMMUNITY_CD, U.AREA_USE_CD;')
    for county, district, municip, community, uzytek, suma in (w or []):
        if _txt(uzytek).upper() != 'LS' or suma is None:
            continue
        k = _klucz(county, district, municip, community)
        if k not in obreby:
            obreby[k] = Obreb(k, '', gminy.get(k[:3], ''))
        obreby[k].pow_ls = round(obreby[k].pow_ls + float(suma), 4)

    return [obreby[k] for k in sorted(obreby)]


def podziel_auto(obreby):
    return {o.klucz: o.grupa_auto() for o in obreby}


def podziel_reczny(obreby, isl_wybrane):
    """Tryb ręczny: ISL = obręby wskazane przez użytkownika (tylko z LS),
    reszta z LS = UPUL, bez LS - usuwane z obu."""
    wynik = {}
    for o in obreby:
        if not o.ma_ls:
            wynik[o.klucz] = BEZ_LS
        else:
            wynik[o.klucz] = ISL if o.klucz in isl_wybrane else UPUL
    return wynik


# --------------------------------------------------------------------------
# analiza wydzieleń
# --------------------------------------------------------------------------

def _mapa_adresowa(przydzial):
    """(DISTRICT, MUNICIP, COMMUNITY) -> grupa."""
    return {k[1:]: g for k, g in przydzial.items()}


def analizuj_wydzielenia(baza, przydzial):
    """Przypisuje wiersze F_ARODES (WYDZIEL/ODDZ/L-CTWO) do grup wg obrębu
    z adresu leśnego i - jeśli F_AROD_LAND_USE nie jest puste - wykrywa
    wydzielenia, których rozliczenie obejmuje działki z obrębu innej
    grupy (po rozdzieleniu ich rozliczenie będzie niepełne).

    Zwraca dict:
      arodes_grupa       {ARODES_INT_NUM: grupa} (WYDZIEL/ODDZ/L-CTWO),
      nieprzypisane      [ADRESS_FOREST] - adres spoza znanych obrębów
                         (zostają w obu bazach),
      rozliczenie_puste  bool,
      konflikty          [(ADRESS_FOREST, grupa_wydz, [PARCELID obcych])],
      liczba_wydz        {grupa: liczba WYDZIEL}.
    """
    mapa = _mapa_adresowa(przydzial)
    wiersze = baza.pobierz(
        'select ARODES_INT_NUM, ADRESS_FOREST, ARODES_TYP_CD from F_ARODES;'
    ) or []

    arodes_grupa = {}
    adresy = {}
    nieprzypisane = []
    liczba_wydz = {UPUL: 0, ISL: 0, BEZ_LS: 0}
    for arod, adr, typ in wiersze:
        typ = _txt(typ)
        if typ not in _TYPY_ADRESOWE:
            continue
        k = klucz_adresu(adr)
        grupa = mapa.get(k) if k else None
        if grupa is None:
            if typ == 'WYDZIEL':
                nieprzypisane.append(_txt(adr))
            continue
        arodes_grupa[arod] = grupa
        adresy[arod] = _txt(adr)
        if typ == 'WYDZIEL':
            liczba_wydz[grupa] += 1

    # wiersz OBRĘB ma adres tylko na poziomie gminy (adr[:6]), ale
    # DopiszWydzielenia tworzy go dla każdego obrębu ewidencyjnego tuż przed
    # jego L-CTWO (stworz_ops_obrebu -> stworz_ops_lctwa) - przypisanie po
    # następnym ARODES_INT_NUM; reszta (bez sąsiada) - patrz wyczysc_kopie
    obreby_adr = {}
    po_numerze = sorted((a, _txt(t)) for a, _, t in wiersze)
    for i, (arod, typ) in enumerate(po_numerze[:-1]):
        if typ in _TYPY_ADRESOWE:
            continue
        nast, typ_nast = po_numerze[i + 1]
        if typ_nast == 'L-CTWO' and nast in arodes_grupa:
            obreby_adr[arod] = arodes_grupa[nast]

    lu = baza.pobierz(
        'select A.ARODES_INT_NUM, P.COUNTY_CD, P.DISTRICT_CD, '
        'P.MUNICIPALITY_CD, P.COMMUNITY_CD, P.REG_SHEET_NR2, P.PARCEL_NR '
        'from F_AROD_LAND_USE A inner join F_PARCEL P '
        'on A.PARCEL_INT_NUM = P.PARCEL_INT_NUM;') or []

    konflikty_sl = {}
    for arod, county, district, municip, community, ark, nr in lu:
        g_wydz = arodes_grupa.get(arod)
        if g_wydz is None:
            continue
        k = _klucz(county, district, municip, community)
        g_dz = przydzial.get(k)
        if g_dz == g_wydz:
            continue
        konflikty_sl.setdefault(arod, set()).add(
            _parcelid(k, ark, nr) + ' [' + (g_dz or '?') + ']')

    konflikty = sorted(
        (adresy[a], arodes_grupa[a], sorted(obce))
        for a, obce in konflikty_sl.items())

    return {
        'arodes_grupa': arodes_grupa,
        'obreby_adr': obreby_adr,
        'nieprzypisane': sorted(nieprzypisane),
        'rozliczenie_puste': not lu,
        'konflikty': konflikty,
        'liczba_wydz': liczba_wydz,
    }


def _parcelid(klucz, ark, nr):
    ark, nr = _txt(ark), _txt(nr)
    if not ark and '.' in nr:
        ark, nr = nr.split('.', 1)
    wynik = klucz_tekst(klucz)
    if ark:
        wynik += '.' + ark
    return wynik + '.' + nr


# --------------------------------------------------------------------------
# czyszczenie kopii bazy
# --------------------------------------------------------------------------

def _tabele_z_kolumna(baza, kolumna):
    """Tabele użytkownika mające podaną kolumnę (bez względu na wielkość
    liter)."""
    # kolumny przez cursor.description, nie cursor.columns() - sterownik
    # ODBC Accessa zwraca w katalogu kolumn bajty, na których pyodbc
    # wywraca się błędem dekodowania UTF-16
    nazwy = [t.table_name for t in baza.cur.tables(tableType='TABLE')
             if not t.table_name.startswith('MSys')]
    wynik = []
    for t in nazwy:
        try:
            baza.cur.execute(f'select * from [{t}] where 1=0')
        except Exception:
            continue
        kolumny = [c[0].upper() for c in baza.cur.description]
        if kolumna.upper() in kolumny:
            wynik.append(t)
    return wynik


def _usun_po_kluczach(baza, tabele, kolumna, wartosci, ostatnia):
    """DELETE w porcjach ze wszystkich `tabele` po `kolumna`, tabela
    nadrzędna (`ostatnia`) na końcu. Zwraca liczbę usuniętych wierszy
    tabeli nadrzędnej."""
    if not wartosci:
        return 0
    kolejnosc = [t for t in tabele if t.upper() != ostatnia.upper()]
    kolejnosc.append(ostatnia)
    usuniete = 0
    for t in kolejnosc:
        for porcja in _porcje(wartosci):
            znaki = ','.join('?' for _ in porcja)
            baza.cur.execute(
                f'DELETE FROM [{t}] WHERE [{kolumna}] IN ({znaki})',
                list(porcja))
            if t == ostatnia:
                usuniete += baza.cur.rowcount if baza.cur.rowcount > 0 else 0
    return usuniete


def wyczysc_kopie(baza, przydzial, grupa_zostaje, arodes_grupa, obreby_adr):
    """Usuwa z (już skopiowanej) bazy wszystko, co nie należy do
    `grupa_zostaje`. Jedna transakcja - błąd wycofuje całość. Zwraca dict
    z licznikami albo None przy błędzie (szczegóły w logu Las-R)."""
    usun_obreby = {k for k, g in przydzial.items() if g != grupa_zostaje}
    try:
        # --- działki ---
        parcele = []
        wiersze = baza.cur.execute(
            'select PARCEL_INT_NUM, COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, '
            'COMMUNITY_CD from F_PARCEL').fetchall()
        for pid, county, district, municip, community in wiersze:
            if _klucz(county, district, municip, community) in usun_obreby:
                parcele.append(pid)

        wlasciciele = set()
        for porcja in _porcje(parcele):
            znaki = ','.join('?' for _ in porcja)
            for a, sa in baza.cur.execute(
                    'select addr_nr, second_addr_nr from '
                    'V_PARCEL_PARTICIPATION where parcel_int_num in (' +
                    znaki + ')', list(porcja)).fetchall():
                wlasciciele.add(a)
                if sa is not None:
                    wlasciciele.add(sa)

        # --- wydzielenia (WYDZIEL/ODDZ/L-CTWO z usuwanych obrębów) ---
        arodes = [a for a, g in arodes_grupa.items() if g != grupa_zostaje]
        tabele_arod = _tabele_z_kolumna(baza, 'ARODES_INT_NUM')
        n_arod = _usun_po_kluczach(
            baza, tabele_arod, 'ARODES_INT_NUM', arodes, 'F_ARODES')

        tabele_parc = _tabele_z_kolumna(baza, 'PARCEL_INT_NUM')
        n_parc = _usun_po_kluczach(
            baza, tabele_parc, 'PARCEL_INT_NUM', parcele, 'F_PARCEL')

        # --- wiersze OBRĘB (adres tylko na poziomie gminy, adr[:6]):
        # usuwane te przypisane do obrębów drugiej grupy (obreby_adr, patrz
        # analizuj_wydzielenia) i te, pod którymi nie został żaden wiersz
        # adresowy - ale gmina, która zostaje w bazie, zachowuje co
        # najmniej jeden wiersz OBRĘB ---
        wiersze = baza.cur.execute(
            'select ARODES_INT_NUM, ADRESS_FOREST, ARODES_TYP_CD '
            'from F_ARODES').fetchall()
        zyje_gmina = {(_txt(adr))[:6] for _, adr, typ in wiersze
                      if _txt(typ) in _TYPY_ADRESOWE}
        obreb_wiersze = sorted((a, _txt(adr)[:6]) for a, adr, typ in wiersze
                               if _txt(typ) not in _TYPY_ADRESOWE)
        osierocone = []
        zostaje_gmina = set()
        for a, gm in obreb_wiersze:
            if gm not in zyje_gmina:
                osierocone.append(a)
            elif obreby_adr.get(a, grupa_zostaje) != grupa_zostaje:
                osierocone.append(a)
            else:
                zostaje_gmina.add(gm)
        for a, gm in obreb_wiersze:
            if gm in zyje_gmina and gm not in zostaje_gmina:
                osierocone.remove(a)
                zostaje_gmina.add(gm)
        _usun_po_kluczach(
            baza, tabele_arod, 'ARODES_INT_NUM', osierocone, 'F_ARODES')

        # --- właściciele, którzy nie mają już żadnej działki ---
        uzywani = set()
        for a, sa in baza.cur.execute(
                'select addr_nr, second_addr_nr from V_PARCEL_PARTICIPATION'
        ).fetchall():
            uzywani.add(a)
            if sa is not None:
                uzywani.add(sa)
        osier_addr = [a for a in wlasciciele if a not in uzywani]
        for porcja in _porcje(osier_addr):
            znaki = ','.join('?' for _ in porcja)
            baza.cur.execute(
                'DELETE FROM V_ADDRESS WHERE ADDR_NR IN (' + znaki + ')',
                list(porcja))

        # --- F_COMMUNITY ---
        for k in usun_obreby:
            baza.cur.execute(
                'DELETE FROM F_COMMUNITY WHERE COUNTY_CD = ? AND '
                'DISTRICT_CD = ? AND MUNICIPALITY_CD = ? AND COMMUNITY_CD = ?',
                list(k))

        baza.con.commit()
    except Exception as e:
        baza.con.rollback()
        QgsMessageLog.logMessage(
            f'Rozdziel UPUL/ISL ({grupa_zostaje}): błąd, wycofano zmiany: {e}',
            'Las-R', Qgis.Critical)
        return None

    return {
        'dzialki_usuniete': n_parc,
        'arodes_usuniete': n_arod,
        'obreb_usuniete': len(osierocone),
        'wlasciciele_usunieci': len(osier_addr),
    }


def kompaktuj(sc):
    """Kompaktowanie kopii .mdb przez DAO (po usunięciu dużej części
    danych plik nie zmniejsza się sam). Błąd nie jest krytyczny - zwraca
    True/False."""
    if not sc.lower().endswith('.mdb'):
        return False
    try:
        import win32com.client
        silnik = win32com.client.Dispatch('DAO.DBEngine.120')
        tymcz = sc + '.kompakt.mdb'
        if os.path.exists(tymcz):
            os.remove(tymcz)
        silnik.CompactDatabase(
            sc, tymcz, ';LANGID=0x0409;CP=1252;COUNTRY=0;pwd=pw', 0,
            ';pwd=pw')
        os.replace(tymcz, sc)
        return True
    except Exception as e:
        QgsMessageLog.logMessage(
            f'Rozdziel UPUL/ISL: kompaktowanie {sc} nie powiodło się '
            f'(nie jest to błąd krytyczny): {e}', 'Las-R', Qgis.Warning)
        return False


def sciezki_wynikowe(baza_sc):
    rdzen, rozsz = os.path.splitext(baza_sc)
    return {UPUL: rdzen + '_UPUL' + rozsz, ISL: rdzen + '_ISL' + rozsz}


def skopiuj_baze(baza_sc, cel_sc):
    shutil.copyfile(baza_sc, cel_sc)


# --------------------------------------------------------------------------
# grafika
# --------------------------------------------------------------------------

def _pola(lyr):
    return {f.name().upper(): f.name() for f in lyr.fields()}


def _funkcja_klucza(lyr, mapa_adresowa):
    """Zwraca (opis_klucza, funkcja feature -> klucz obrębu 4-elementowy
    albo None) albo (None, None), gdy warstwa nie ma pól pozwalających
    ustalić obręb. Kolejność: COUNTY/DISTRICT/MUNICIP/COMMUNITY,
    PARCELID, ADR_LES/ADR_BDL."""
    pola = _pola(lyr)

    if all(p in pola for p in ('COUNTY', 'DISTRICT', 'MUNICIP', 'COMMUNITY')):
        n = [pola[p] for p in ('COUNTY', 'DISTRICT', 'MUNICIP', 'COMMUNITY')]

        def f_pola(feat):
            k = _klucz(*[_txt_null(feat[x]) for x in n])
            return k if all(k) else None
        if 'PARCELID' in pola:
            f_pid = _f_parcelid(pola['PARCELID'])
            return 'COUNTY..COMMUNITY/PARCELID', (
                lambda feat: f_pola(feat) or f_pid(feat))
        return 'COUNTY..COMMUNITY', f_pola

    if 'PARCELID' in pola:
        return 'PARCELID', _f_parcelid(pola['PARCELID'])

    for nazwa in ('ADR_LES', 'ADR_BDL'):
        if nazwa in pola:
            pole = pola[nazwa]
            # adres leśny nie ma kodu województwa - klucz odtwarzany przez
            # mapę (DISTRICT, MUNICIP, COMMUNITY) -> pełny klucz
            def f_adr(feat, pole=pole):
                k = klucz_adresu(_txt_null(feat[pole]))
                return mapa_adresowa.get(k) if k else None
            return nazwa, f_adr

    # warstwy EGiB/GML (EWID, OBR, KLU, UZYTKI...) - identyfikator TERYT
    # "WWPPGG_R.OOOO..." (np. idDzialki = 160908_5.0127.AR_1.217/17)
    for nazwa in _POLA_TERYT:
        if nazwa in pola:
            pole = pola[nazwa]

            def f_teryt(feat, pole=pole):
                m = _WZORZEC_TERYT.search(_txt_null(feat[pole]))
                if not m:
                    return None
                return (m.group(1), m.group(2), m.group(3) + m.group(4),
                        m.group(5))
            return pola[nazwa], f_teryt

    return None, None


def _txt_null(w):
    try:
        from qgis.PyQt.QtCore import QVariant
        if isinstance(w, QVariant) and w.isNull():
            return ''
    except Exception:
        pass
    return _txt(w)


def _f_parcelid(pole):
    def f(feat):
        pid = _txt_null(feat[pole]).split('.')[0]
        if len(pid) != 11 or not pid.isdigit():
            return None
        return (pid[0:2], pid[2:4], pid[4:7], pid[7:11])
    return f


def _zapisz(lyr, ids, sciezka):
    lyr.selectByIds(list(ids))
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    opcje.onlySelectedFeatures = True
    wynik = QgsVectorFileWriter.writeAsVectorFormatV3(
        lyr, sciezka, QgsProject.instance().transformContext(), opcje)
    lyr.removeSelection()
    blad = wynik[0] if isinstance(wynik, tuple) else wynik
    if blad != QgsVectorFileWriter.NoError:
        komunikat = wynik[1] if isinstance(wynik, tuple) and len(wynik) > 1 else ''
        raise RuntimeError(f'zapis {sciezka}: {komunikat}')
    zrodlo = os.path.splitext(lyr.source().split('|')[0])[0]
    cel = os.path.splitext(sciezka)[0]
    for r in _ROZSZERZENIA_STYLU:
        if os.path.isfile(zrodlo + r):
            shutil.copyfile(zrodlo + r, cel + r)


def _kopiuj_warstwe(sc, katalog):
    rdzen = os.path.splitext(sc)[0]
    nazwa = os.path.basename(rdzen)
    for plik in os.listdir(os.path.dirname(sc)):
        if os.path.splitext(plik)[0] == nazwa:
            shutil.copyfile(os.path.join(os.path.dirname(sc), plik),
                            os.path.join(katalog, plik))


def podziel_grafike(folder_shp, katalogi, przydzial):
    """Dzieli wszystkie warstwy .shp z folder_shp na katalogi[UPUL]
    i katalogi[ISL] (dla grup bez katalogu - pomijane). Obiekty obrębów
    bez LS nie trafiają nigdzie. Obiekty, dla których nie da się ustalić
    obrębu (puste/niepoprawne pole klucza), oraz obiekty z obrębów spoza
    bazy (np. sąsiednie obręby w warstwach EGiB) trafiają do OBU
    katalogów. Warstwy bez pól klucza są kopiowane w całości do obu.

    Zwraca listę wierszy raportu: (warstwa, sposób, {grupa: liczba},
    (bez_klucza, spoza_bazy), błąd)."""
    mapa_adresowa = {k[1:]: k for k in przydzial}
    for kat in katalogi.values():
        os.makedirs(kat, exist_ok=True)

    raport = []
    for plik in sorted(os.listdir(folder_shp)):
        if not plik.lower().endswith('.shp'):
            continue
        sc = os.path.join(folder_shp, plik)
        nazwa = os.path.splitext(plik)[0]
        lyr = QgsVectorLayer(sc, nazwa, 'ogr')
        if not lyr.isValid():
            raport.append((nazwa, '-', {}, 0, 'nie udało się wczytać'))
            continue

        sposob, f_klucz = _funkcja_klucza(lyr, mapa_adresowa)
        try:
            if f_klucz is None:
                for kat in katalogi.values():
                    _kopiuj_warstwe(sc, kat)
                raport.append((nazwa, 'skopiowana w całości (brak pól '
                               'obrębu)', {}, 0, ''))
                continue

            ids = {g: [] for g in katalogi}
            bez_klucza = []
            spoza_bazy = []
            for feat in lyr.getFeatures():
                k = f_klucz(feat)
                if k is None:
                    bez_klucza.append(feat.id())
                    continue
                if k not in przydzial:
                    spoza_bazy.append(feat.id())
                    continue
                g = przydzial[k]
                if g in ids:
                    ids[g].append(feat.id())

            liczby = {}
            for g, kat in katalogi.items():
                do_zapisu = ids[g] + bez_klucza + spoza_bazy
                liczby[g] = len(ids[g])
                if do_zapisu:
                    _zapisz(lyr, do_zapisu, os.path.join(kat, plik))
            raport.append((nazwa, sposob, liczby,
                           (len(bez_klucza), len(spoza_bazy)), ''))
        except Exception as e:
            QgsMessageLog.logMessage(
                f'Rozdziel UPUL/ISL - warstwa {nazwa}: {e}', 'Las-R',
                Qgis.Critical)
            raport.append((nazwa, sposob or '-', {}, 0, str(e)))

    return raport


# --------------------------------------------------------------------------
# raporty
# --------------------------------------------------------------------------

def _pow(x):
    return f'{x:.4f}'.replace('.', ',')


def _sekcja_obrebow(linie, obreby, przydzial, grupa, tytul):
    wybrane = [o for o in obreby if przydzial[o.klucz] == grupa]
    linie.append(f'{tytul} - {len(wybrane)} obrębów, LS razem '
                 f'{_pow(sum(o.pow_ls for o in wybrane))} ha')
    linie.append('-' * 70)
    for o in wybrane:
        linie.append(f'  {klucz_tekst(o.klucz)}  {o.gmina[:25]:<25} '
                     f'{o.nazwa[:25]:<25} LS {_pow(o.pow_ls):>12} ha  '
                     f'działek: {o.dzialki}')
    linie.append('')


def zapisz_raport_konfliktow(katalog, konflikty):
    os.makedirs(katalog, exist_ok=True)
    czas = datetime.now().strftime('%Y%m%dT%H%M%S')
    sc = os.path.join(katalog, f'rozdziel_UPUL_ISL_konflikty_{czas}.txt')
    linie = [
        'ROZDZIEL BAZY NA UPUL I ISL - wydzielenia na granicy grup',
        '',
        'Rozliczenie powierzchni (F_AROD_LAND_USE) tych wydzieleń obejmuje '
        'działki z obrębów, które trafią do innej bazy (albo zostaną '
        'usunięte jako obręby bez LS). Grupa wydzielenia wynika z obrębu '
        'w adresie leśnym; w nawiasie grupa działki.',
        '',
    ]
    for adr, grupa, obce in konflikty:
        linie.append(f'{adr}  [{grupa}]')
        for p in obce:
            linie.append(f'    {p}')
    with open(sc, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linie) + '\n')
    return sc


def zapisz_raport(katalog, baza_sc, tryb, obreby, przydzial, analiza,
                  wyniki_baz, raport_grafiki):
    os.makedirs(katalog, exist_ok=True)
    czas = datetime.now().strftime('%Y%m%dT%H%M%S')
    sc = os.path.join(katalog, f'rozdziel_UPUL_ISL_{czas}.txt')
    linie = [
        'ROZDZIEL BAZY NA UPUL I ISL',
        f'Baza źródłowa: {baza_sc}',
        f'Data: {datetime.now():%Y-%m-%d %H:%M}',
        f'Tryb: {tryb}' + (f' (próg {_pow(PROG_ISL)} ha)'
                           if tryb == 'automatyczny' else ''),
        '',
    ]
    _sekcja_obrebow(linie, obreby, przydzial, UPUL, 'UPUL')
    _sekcja_obrebow(linie, obreby, przydzial, ISL, 'ISL')
    _sekcja_obrebow(linie, obreby, przydzial, BEZ_LS,
                    'Obręby bez LS - usunięte z OBU baz')

    linie.append('BAZY WYNIKOWE')
    linie.append('-' * 70)
    for grupa, (sc_bazy, licz) in wyniki_baz.items():
        if licz is None:
            linie.append(f'  {grupa}: BŁĄD - {sc_bazy}')
            continue
        linie.append(
            f'  {grupa}: {sc_bazy}\n'
            f'      wydzieleń: {analiza["liczba_wydz"][grupa]}, usunięto '
            f'działek: {licz["dzialki_usuniete"]}, wierszy F_ARODES: '
            f'{licz["arodes_usuniete"]} (+{licz["obreb_usuniete"]} OBRĘB), '
            f'właścicieli: {licz["wlasciciele_usunieci"]}')
    linie.append('')

    if analiza['nieprzypisane']:
        linie.append(
            'Wydzielenia z adresem spoza obrębów bazy - pozostawione w OBU '
            f'bazach ({len(analiza["nieprzypisane"])}):')
        linie += ['  ' + a for a in analiza['nieprzypisane']]
        linie.append('')

    if analiza['rozliczenie_puste']:
        linie.append('UWAGA: rozliczenie powierzchni (F_AROD_LAND_USE) było '
                     'puste - rozlicz powierzchnię wydzieleń w obu bazach.')
        linie.append('')
    elif analiza['konflikty']:
        linie.append(
            'UWAGA: wydzielenia z rozliczeniem na działkach innej grupy - '
            'po rozdzieleniu ich rozliczenie jest niepełne, rozlicz '
            f'powierzchnię ponownie ({len(analiza["konflikty"])}):')
        for adr, grupa, obce in analiza['konflikty']:
            linie.append(f'  {adr}  [{grupa}]: ' + ', '.join(obce))
        linie.append('')

    if raport_grafiki:
        linie.append('GRAFIKA')
        linie.append('-' * 70)
        for nazwa, sposob, liczby, nieustalone, blad in raport_grafiki:
            if blad:
                linie.append(f'  {nazwa}: BŁĄD - {blad}')
                continue
            if not liczby:
                linie.append(f'  {nazwa}: {sposob}')
                continue
            bez_klucza, spoza_bazy = nieustalone
            tekst = ', '.join(f'{g}={n}' for g, n in liczby.items())
            if bez_klucza:
                tekst += f', bez ustalonego obrębu (do obu): {bez_klucza}'
            if spoza_bazy:
                tekst += f', z obrębów spoza bazy (do obu): {spoza_bazy}'
            linie.append(f'  {nazwa} (wg {sposob}): {tekst}')
        linie.append('')

    with open(sc, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linie) + '\n')
    return sc
