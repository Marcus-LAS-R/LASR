"""Silnik "Wydziel właścicieli do nowej bazy" - wybranych właścicieli (i
wszystkich współwłaścicieli z ich grup rejestrowych, F_PARCEL.
LAND_REGISTER_NR) wraz z ich działkami ewidencyjnymi (i opcjonalnie opisem
taksacyjnym/grafiką) przenosi z bazy źródłowej do już istniejącej bazy
docelowej.

Reużywa Laczenie (baza_polacz.py) do zapisu w bazie docelowej - dokładnie
tym samym wzorcem, co konwersja_pul_upul/core/kopia_pul_upul.py: owija
instancję Laczenie i podmienia tylko p_f_arodes()/p_pozostale_nadrzedne()
na wersje filtrowane jawnym zbiorem kluczy (zamiast dedup/obrębów), nie
modyfikując samego Laczenie/baza_polacz.py.
"""

import os
from datetime import datetime

from qgis.core import (
    Qgis, QgsMessageLog, QgsProject, QgsVectorLayer, QgsVectorFileWriter,
)

from ...baza_polacz import Laczenie
from ...baza_polacz_rejestr import (
    F_PARCEL_NADRZEDNA, V_ADDRESS_NADRZEDNA, GRUPA3_DZIECI,
)
from ...funkcje import isNone

_ROZMIAR_PORCJI = 200  # limit parametrów w zapytaniu IN (...) dla Jet/ACE


def _porcje(wartosci, rozmiar=_ROZMIAR_PORCJI):
    wartosci = sorted(wartosci)
    for i in range(0, len(wartosci), rozmiar):
        yield wartosci[i:i + rozmiar]


def _pobierz_filtrowane(baza, tabela, kolumny, kolumna_filtr, wartosci):
    """SELECT kolumny FROM tabela WHERE kolumna_filtr IN (wartosci), w
    porcjach (Jet/ACE ma praktyczny limit liczby parametrów)."""
    if not wartosci:
        return []
    wynik = []
    sql = ('select ' + ', '.join(kolumny) + ' from ' + tabela +
           ' where ' + kolumna_filtr + ' in ({});')
    for porcja in _porcje(wartosci):
        znaki = ','.join('?' for _ in porcja)
        wynik.extend(
            baza.cur.execute(sql.format(znaki), list(porcja)).fetchall())
    return wynik


def pobierz_wlascicieli(baza):
    """Zwraca listę krotek (ADDR_NR, NAME_1, NAME_2, addr_grp_fl) do
    wypełnienia tabeli wyboru w dialogu, albo [] przy błędzie/pustej bazie."""
    wynik = baza.pobierz(
        'select ADDR_NR, NAME_1, NAME_2, addr_grp_fl from V_ADDRESS '
        'order by ADDR_NR;')
    return wynik if wynik is not False else []


def policz_zbior_eksportu(baza, addr_wybrani):
    """Zwraca (addr_final, parcels_final) na podstawie grup rejestrowych
    (F_PARCEL.LAND_REGISTER_NR) - stałego zestawu współwłaścicieli dla
    jednej lub więcej działek; jedna działka należy do dokładnie jednej
    grupy, jeden właściciel może występować w kilku grupach (różne
    współwłasności na różnych działkach). Zwraca WSZYSTKIE działki grup
    rejestrowych, do których należy którykolwiek z addr_wybrani, oraz
    wszystkich właścicieli/współwłaścicieli zapisanych na tych działkach
    (podejście potwierdzone z użytkownikiem 2026-09-14 jako dokładniejsze
    niż rekonstrukcja współwłasności ze skanu V_PARCEL_PARTICIPATION -
    LAND_REGISTER_NR jest tu zawsze pewny i kompletny w obrębie JEDNEGO
    obrębu ewidencyjnego - patrz policz_grupy_rejestrowe_wlasciciela)."""
    grupy = policz_grupy_rejestrowe_wlasciciela(baza, addr_wybrani)
    if not grupy:
        return set(addr_wybrani), set()

    numery = {g[4] for g in grupy}
    kandydaci = _pobierz_filtrowane(
        baza, 'F_PARCEL',
        ['PARCEL_INT_NUM', 'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD',
         'COMMUNITY_CD', 'LAND_REGISTER_NR'],
        'LAND_REGISTER_NR', numery)
    parcels = {w[0] for w in kandydaci if tuple(w[1:]) in grupy}
    if not parcels:
        return set(addr_wybrani), set()

    addr_final = set(addr_wybrani)
    for a, sa in _pobierz_filtrowane(
            baza, 'V_PARCEL_PARTICIPATION', ['addr_nr', 'second_addr_nr'],
            'parcel_int_num', parcels):
        addr_final.add(a)
        if sa is not None:
            addr_final.add(sa)

    return addr_final, parcels


def policz_arodes_wydziel(baza, parcels):
    """Zwraca zbiór starych ARODES_INT_NUM (typu WYDZIEL) wydzieleń
    mających choć jeden użytek (F_AROD_LAND_USE) na którejś z podanych
    działek - do eksportu opisu taksacyjnego (opcja 1)."""
    wiersze = _pobierz_filtrowane(
        baza, 'F_AROD_LAND_USE', ['ARODES_INT_NUM'], 'PARCEL_INT_NUM', parcels)
    return {w[0] for w in wiersze}


def policz_klucze_dzialek(baza, parcels):
    """Zwraca zbiór kluczy (kod_gminy, COMMUNITY_CD, PARCEL_NR) - do
    dopasowania obiektów DZKAT/LS (opcja 2), tym samym kształtem klucza co
    kontrola_terenowa/core/dzkat_kontrola._klucz_dzkat."""
    wiersze = _pobierz_filtrowane(
        baza, 'F_PARCEL',
        ['COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD', 'COMMUNITY_CD',
         'PARCEL_NR'],
        'PARCEL_INT_NUM', parcels)
    return {
        (isNone(w[0]) + isNone(w[1]) + isNone(w[2]), isNone(w[3]), isNone(w[4]))
        for w in wiersze
    }


def policz_adresy_wydz(baza, arodes):
    """Zwraca zbiór ADRESS_FOREST (ADR_LES) dla podanych ARODES_INT_NUM -
    do dopasowania obiektów WYDZ/PNSW (opcja 2)."""
    wiersze = _pobierz_filtrowane(
        baza, 'F_ARODES', ['ADRESS_FOREST'], 'ARODES_INT_NUM', arodes)
    return {w[0] for w in wiersze}


def policz_grupy_rejestrowe_wlasciciela(baza, addr_wybrani):
    """Zwraca zbiór grup rejestrowych - krotek (COUNTY_CD, DISTRICT_CD,
    MUNICIPALITY_CD, COMMUNITY_CD, LAND_REGISTER_NR) - działek, na których
    występuje którykolwiek z addr_wybrani (jako addr_nr LUB second_addr_nr
    w V_PARCEL_PARTICIPATION). LAND_REGISTER_NR jest unikalny TYLKO w
    obrębie jednego obrębu ewidencyjnego (np. "G118" może niezależnie
    istnieć w dwóch różnych obrębach, dla zupełnie innych właścicieli -
    stwierdzone empirycznie 2026-09-14) - dlatego samo LAND_REGISTER_NR
    nie wystarcza jako klucz, potrzebny jest pełny kod obrębu."""
    wiersze = baza.pobierz(
        'select addr_nr, parcel_int_num, second_addr_nr '
        'from V_PARCEL_PARTICIPATION;')
    if wiersze is False:
        return set()
    parcels = {p for a, p, sa in wiersze if a in addr_wybrani or sa in addr_wybrani}
    if not parcels:
        return set()
    wiersze2 = _pobierz_filtrowane(
        baza, 'F_PARCEL',
        ['COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD', 'COMMUNITY_CD',
         'LAND_REGISTER_NR'],
        'PARCEL_INT_NUM', parcels)
    return {tuple(w) for w in wiersze2 if w[4] is not None}


def _slownik_adresow_wydz(baza, arodes):
    return dict(_pobierz_filtrowane(
        baza, 'F_ARODES', ['ARODES_INT_NUM', 'ADRESS_FOREST'],
        'ARODES_INT_NUM', arodes))


def _wyr1(dane):
    """Buduje czytelny identyfikator działki (jak Wyr1 w Baza.uzytki())
    z (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD,
    REG_SHEET_NR2, PARCEL_NR)."""
    county, district, municip, community, ark, nr = dane
    wyr1 = isNone(county) + isNone(district) + isNone(municip) + isNone(community)
    if isNone(ark):
        wyr1 += '.' + isNone(ark)
    wyr1 += '.' + isNone(nr)
    return wyr1


def policz_wydzielenia_mieszane(baza, arodes, grupy_dozwolone):
    """Kontrola grup rejestrowych: wydzielenie (WYDZIEL) to jednostka
    gospodarki leśnej niezależna od granic własności - jedno wydzielenie
    może obejmować działki z RÓŻNYCH grup rejestrowych (F_PARCEL.
    LAND_REGISTER_NR, jedna działka = jedna grupa). Zwraca listę krotek
    (ADRESS_FOREST, [PARCELID obcej działki, ...]) dla wydzieleń z
    `arodes`, w których choć jedna działka (wg F_AROD_LAND_USE - musi być
    uzupełnione, inaczej kontrola nic nie wykryje) należy do grupy
    rejestrowej spoza `grupy_dozwolone` - czyli działki, które nie powinny
    się znaleźć w eksportowanym wydzieleniu (należą do kogoś, kto nie jest
    eksportowany). "Działki właściwe" NIE są tu liczone per-wydzielenie -
    to po prostu wszystkie parcels_final (patrz policz_wszystkie_parcelid),
    myślące byłoby pokazywanie ich tylko dla wydzieleń mieszanych (feedback
    użytkownika 2026-09-14)."""
    if not arodes:
        return []

    wiersze = _pobierz_filtrowane(
        baza, 'F_AROD_LAND_USE', ['ARODES_INT_NUM', 'PARCEL_INT_NUM'],
        'ARODES_INT_NUM', arodes)
    parcele_wydz = {}
    for arod, parcel in wiersze:
        parcele_wydz.setdefault(arod, set()).add(parcel)

    wszystkie_parcele = {p for parcele in parcele_wydz.values() for p in parcele}
    dane_dzialek = {}
    for w in _pobierz_filtrowane(
            baza, 'F_PARCEL',
            ['PARCEL_INT_NUM', 'LAND_REGISTER_NR', 'COUNTY_CD', 'DISTRICT_CD',
             'MUNICIPALITY_CD', 'COMMUNITY_CD', 'REG_SHEET_NR2', 'PARCEL_NR'],
            'PARCEL_INT_NUM', wszystkie_parcele):
        pid, lrn, county, district, municip, community, ark, nr = w
        grupa = (county, district, municip, community, lrn)
        dane_dzialek[pid] = (grupa, _wyr1((county, district, municip, community, ark, nr)))
    adresy = _slownik_adresow_wydz(baza, arodes)

    mieszane = []
    for arod, parcele in parcele_wydz.items():
        obce = []
        for p in parcele:
            grupa, parcelid = dane_dzialek.get(p, (None, None))
            if parcelid is None:
                continue
            if grupa not in grupy_dozwolone:
                obce.append(parcelid)
        if obce:
            mieszane.append((adresy.get(arod, str(arod)), sorted(obce)))
    return mieszane


def policz_wszystkie_parcelid(baza, parcels):
    """Zwraca posortowaną listę PARCELID (patrz _wyr1) dla podanego zbioru
    PARCEL_INT_NUM - "działki właściwe" to WSZYSTKIE działki przeznaczone
    do eksportu (parcels_final), niezależnie od podziału na wydzielenia
    mieszane/czyste."""
    wiersze = _pobierz_filtrowane(
        baza, 'F_PARCEL',
        ['PARCEL_INT_NUM', 'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD',
         'COMMUNITY_CD', 'REG_SHEET_NR2', 'PARCEL_NR'],
        'PARCEL_INT_NUM', parcels)
    return sorted({_wyr1(w[1:]) for w in wiersze})


def zapisz_raport_wydzielen_mieszanych(katalog, mieszane, wszystkie_wlasciwe):
    """Zapisuje listę wydzieleń mieszanych do pliku txt - sekcja "Działki
    obce" per adres leśny (tylko wydzielenia mieszane, patrz
    policz_wydzielenia_mieszane), potem JEDNA płaska sekcja "Działki
    właściwe" ze WSZYSTKIMI działkami przeznaczonymi do eksportu
    (wszystkie_wlasciwe, patrz policz_wszystkie_parcelid) - podział
    właściwych per-wydzielenie byłby mylący dla operatora (feedback
    użytkownika 2026-09-14)."""
    czas = datetime.now().isoformat().replace(':', '')[:-7]
    rap_sc = os.path.join(katalog, 'wydzielenia_mieszane_' + czas + '.txt')

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write('WYDZIELENIA DO ROZDZIELENIA PRZED PONOWNYM URUCHOMIENIEM\r\n')
        plik.write('=' * 72 + '\r\n\r\n')

        plik.write('DZIAŁKI OBCE (do rozdzielenia z wydzieleń mieszanych)\r\n')
        plik.write('-' * 72 + '\r\n')
        for adres, obce in sorted(mieszane):
            plik.write(adres + '\r\n')
            for parcelid in obce:
                plik.write('    ' + parcelid + '\r\n')
            plik.write('\r\n')

        plik.write('DZIAŁKI WŁAŚCIWE (wszystkie przeznaczone do eksportu)\r\n')
        plik.write('-' * 72 + '\r\n')
        for parcelid in wszystkie_wlasciwe:
            plik.write(parcelid + '\r\n')

    return rap_sc


def zapisz_warstwy_wydzielen_mieszanych(folder_shp_zrodlowy, folder_docelowy,
                                         obce_parcelid, wlasciwe_parcelid):
    """Zapisuje w folder_docelowy dwie warstwy dopasowane po PARCELID z
    warstwy DZKAT (folder_shp_zrodlowy) - Dzialki_wlasciwe.shp (WSZYSTKIE
    działki przeznaczone do eksportu, patrz policz_wszystkie_parcelid) i
    Dzialki_obce.shp (tylko te, które trzeba wydzielić z wydzieleń
    mieszanych, patrz policz_wydzielenia_mieszane) - do wizualnej kontroli
    na mapie. Zwraca {'Dzialki_wlasciwe': sciezka|None, 'Dzialki_obce':
    sciezka|None} - None gdy brak warstwy DZKAT albo brak dopasowanych
    obiektów danego rodzaju."""
    lyr = _wczytaj_shp(folder_shp_zrodlowy, 'DZKAT')
    if lyr is None:
        return {'Dzialki_wlasciwe': None, 'Dzialki_obce': None}

    os.makedirs(folder_docelowy, exist_ok=True)
    wyniki = {}
    for nazwa, parcelidy in (('Dzialki_wlasciwe', set(wlasciwe_parcelid)),
                              ('Dzialki_obce', set(obce_parcelid))):
        dopasowane = [f for f in lyr.getFeatures() if f['PARCELID'] in parcelidy]
        if _zapisz_podzbior(lyr, dopasowane, folder_docelowy, nazwa):
            wyniki[nazwa] = os.path.join(folder_docelowy, nazwa + '.shp')
        else:
            wyniki[nazwa] = None
    return wyniki


def zapisz_raport_eksportu(katalog, baza, addr_wybrani, addr_final,
                            parcels_final, arodes_raport):
    """Zapisuje końcowy raport txt (PRZED ew. uprzątnięciem źródła - to ono
    kasuje dane, które ten raport opisuje): działki każdego wyeksportowanego
    właściciela, pełną listę wyeksportowanych wydzieleń oraz wydzielenia w
    podziale na pierwotnie zaznaczonych właścicieli (addr_wybrani) - dla
    każdego z nich tylko te wydzielenia, które dotykają JEGO własnych
    działek (nie wszystkich działek doczepionych współwłaścicieli)."""
    nazwy = {
        w[0]: (w[1] or '', w[2] or '') for w in _pobierz_filtrowane(
            baza, 'V_ADDRESS', ['ADDR_NR', 'NAME_1', 'NAME_2'],
            'ADDR_NR', addr_final)
    }

    dzialki = {
        w[0]: _wyr1(w[1:]) for w in _pobierz_filtrowane(
            baza, 'F_PARCEL',
            ['PARCEL_INT_NUM', 'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD',
             'COMMUNITY_CD', 'REG_SHEET_NR2', 'PARCEL_NR'],
            'PARCEL_INT_NUM', parcels_final)
    }

    dzialki_wlasciciela = {}
    for a, p, sa in _pobierz_filtrowane(
            baza, 'V_PARCEL_PARTICIPATION',
            ['addr_nr', 'parcel_int_num', 'second_addr_nr'],
            'parcel_int_num', parcels_final):
        for wl in (a, sa):
            if wl is not None:
                dzialki_wlasciciela.setdefault(wl, set()).add(p)

    adresy_wydz = _slownik_adresow_wydz(baza, arodes_raport)
    parcel_arodes = {}
    for arod, parcel in _pobierz_filtrowane(
            baza, 'F_AROD_LAND_USE', ['ARODES_INT_NUM', 'PARCEL_INT_NUM'],
            'ARODES_INT_NUM', arodes_raport):
        parcel_arodes.setdefault(parcel, set()).add(arod)

    czas = datetime.now().isoformat().replace(':', '')[:-7]
    rap_sc = os.path.join(katalog, 'eksport_wlascicieli_' + czas + '.txt')

    def _naglowek(addr_nr):
        nazwa_1, nazwa_2 = nazwy.get(addr_nr, ('', ''))
        return f'[{addr_nr}] {nazwa_1} {nazwa_2}'.rstrip()

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write('RAPORT EKSPORTU WŁAŚCICIELI\r\n')
        plik.write('Baza źródłowa: ' + baza.baza + '\r\n')
        plik.write('=' * 72 + '\r\n\r\n')

        plik.write('DZIAŁKI WYEKSPORTOWANYCH WŁAŚCICIELI\r\n')
        plik.write('-' * 72 + '\r\n')
        for addr_nr in sorted(addr_final):
            plik.write(_naglowek(addr_nr) + '\r\n')
            for p in sorted(dzialki_wlasciciela.get(addr_nr, ()),
                             key=lambda pp: dzialki.get(pp, str(pp))):
                plik.write('    ' + dzialki.get(p, str(p)) + '\r\n')
            plik.write('\r\n')

        plik.write('WYEKSPORTOWANE WYDZIELENIA (ogółem: ' +
                    str(len(adresy_wydz)) + ')\r\n')
        plik.write('-' * 72 + '\r\n')
        for adr in sorted(adresy_wydz.values()):
            plik.write(adr + '\r\n')
        plik.write('\r\n')

        plik.write('WYDZIELENIA W PODZIALE NA WYBRANYCH WŁAŚCICIELI\r\n')
        plik.write('-' * 72 + '\r\n')
        for addr_nr in sorted(addr_wybrani):
            plik.write(_naglowek(addr_nr) + '\r\n')
            jego_arodes = set()
            for p in dzialki_wlasciciela.get(addr_nr, ()):
                jego_arodes |= parcel_arodes.get(p, set())
            for arod in sorted(jego_arodes,
                                key=lambda a: adresy_wydz.get(a, str(a))):
                if arod in adresy_wydz:
                    plik.write('    ' + adresy_wydz[arod] + '\r\n')
            plik.write('\r\n')

    return rap_sc


def podglad(baza, addr_wybrani, opcja_opisy):
    """Dry-run: liczy, bez zapisu, ile rekordów zostanie objętych
    eksportem. Zwraca dict z licznikami do wyświetlenia użytkownikowi."""
    addr_final, parcels = policz_zbior_eksportu(baza, addr_wybrani)
    arodes = policz_arodes_wydziel(baza, parcels) if opcja_opisy else set()
    return {
        'wlasciciele_zaznaczeni': len(addr_wybrani),
        'wspolwlasciciele_dodatkowi': len(addr_final) - len(addr_wybrani),
        'dzialki': len(parcels),
        'wydzielenia': len(arodes),
    }


class EksportWlascicieli:
    """Owija Laczenie (baza_polacz.py) - patrz docstring modułu. Metody o
    tych samych nazwach co Laczenie/KopiaPULdoUPUL, ale filtrowane jawnym
    zbiorem starych kluczy zamiast dedup/obrębów."""

    def __init__(self, baza0, baza_zrodlowa, opcja_opisy):
        self.baza0 = baza0
        self.baza = baza_zrodlowa

        wybrane = {
            'f_parcel': True, 'v_address': True,
            'v_parcel_participation': True, 'f_parcel_land_use': True,
            'f_arodes': opcja_opisy,
        }
        for t in GRUPA3_DZIECI:
            wybrane[t.klucz] = opcja_opisy

        self.laczenie = Laczenie(baza0, baza_zrodlowa, wybrane=wybrane)

    @property
    def sl_arodes(self):
        return self.laczenie.sl_arodes

    @property
    def l_bledy_wpisu(self):
        return self.laczenie.l_bledy_wpisu

    @property
    def l_bledy_odczytu(self):
        return self.laczenie.l_bledy_odczytu

    def p_f_max(self):
        self.laczenie.p_f_max()

    def p_f_arodes(self, arodes_dozwolone):
        """Odpowiednik Laczenie.p_f_arodes(), filtrowany jawnym zbiorem
        ARODES_INT_NUM (WYDZIEL) do eksportu zamiast obrębów - dopisuje
        też administracyjne wiersze ODDZ/L-CTWO, których prefiks adresu
        odpowiada eksportowanym wydzieleniom (odwrotność cleanupu w
        baza_wrapper.usun_rekordy, gdy te wiersze zostają puste)."""
        l = self.laczenie
        if not l.wybrane.get('f_arodes'):
            return

        sql = ('select ARODES_INT_NUM, ADRESS_FOREST, ARODES_TYP_CD, '
               'ORDER_KEY, ADRESS_VALID, PROT_INT_NUM, TEMP_RAPORT '
               'from f_arodes order by arodes_int_num asc;')
        arod_org = l.baza0.pobierz(sql)
        arod_zrd = l.baza.pobierz(sql)
        if arod_org is False:
            l.l_bledy_odczytu.append(
                (l.baza0.baza, 'f_arodes',
                 'Nie udało się odczytać tabeli (baza docelowa)'))
            arod_org = []
        if arod_zrd is False:
            l.l_bledy_odczytu.append(
                (l.baza.baza, 'f_arodes',
                 'Nie udało się odczytać tabeli (baza źródłowa)'))
            arod_zrd = []

        sl_org_baza = {x[1] for x in arod_org}

        prefiks16 = {it[1][:16] for it in arod_zrd if it[0] in arodes_dozwolone}
        prefiks10 = {it[1][:10] for it in arod_zrd if it[0] in arodes_dozwolone}

        do_wpisania = [
            it for it in arod_zrd
            if it[0] in arodes_dozwolone
            or (it[2] == 'ODDZ' and it[1][:16] in prefiks16)
            or (it[2] == 'L-CTWO' and it[1][:10] in prefiks10)
        ]

        for it in do_wpisania:
            if it[1] not in sl_org_baza:
                l.maxint += 1
                l.f_arodes.append([l.maxint] + list(it[1:]))
                l.sl_arodes[it[0]] = l.maxint
            else:
                l.l_wpisanych_innych.append(it[1])

    def p_f_community(self):
        # Grupa 1 - zawsze dedup po kluczu naturalnym, tania (mała
        # tabela), reużyta bez zmian
        self.laczenie.p_f_community()

    def p_pozostale_nadrzedne(self, parcels_final, addr_final):
        """Odpowiednik Laczenie.p_pozostale_nadrzedne(), filtrowany jawnym
        zbiorem starych PARCEL_INT_NUM/ADDR_NR zamiast obrębów - reużywa
        Laczenie._polacz_nadrzedna() wprost (ten sam mechanizm remapu PK
        i dedupu po kluczu naturalnym co "Połącz bazy TPU")."""
        l = self.laczenie
        if l.wybrane.get('f_parcel'):
            l.f_parcel_nowe, l.maxparcel = l._polacz_nadrzedna(
                F_PARCEL_NADRZEDNA, l.maxparcel,
                filtr_wiersza=lambda w: w[0] in parcels_final)
        if l.wybrane.get('v_address'):
            l.v_address_nowe, l.maxaddr = l._polacz_nadrzedna(
                V_ADDRESS_NADRZEDNA, l.maxaddr,
                filtr_wiersza=lambda w: w[0] in addr_final)

    def p_tabele(self):
        self.laczenie.p_tabele()

    def d_tabele(self):
        self.laczenie.d_tabele()


def eksportuj_grafike(folder_shp_zrodlowy, folder_docelowy, klucze_dzialek,
                       adresy_wydz):
    """Zapisuje w folder_docelowy podzbiory DZKAT/LS/WYDZ/PNSW z
    folder_shp_zrodlowy dopasowane do klucze_dzialek (DZKAT/LS, po kluczu
    z policz_klucze_dzialek) i adresy_wydz (WYDZ/PNSW, po ADR_LES/ADR_BDL).
    Zwraca {nazwa_warstwy: liczba_wyeksportowanych_obiektow}."""
    os.makedirs(folder_docelowy, exist_ok=True)
    wyniki = {}

    for nazwa in ('DZKAT', 'LS'):
        lyr = _wczytaj_shp(folder_shp_zrodlowy, nazwa)
        if lyr is None:
            continue
        dopasowane = [f for f in lyr.getFeatures() if _klucz_dzkat(f) in klucze_dzialek]
        wyniki[nazwa] = _zapisz_podzbior(lyr, dopasowane, folder_docelowy, nazwa)

    for nazwa, kolumna in (('WYDZ', 'ADR_LES'), ('PNSW', 'ADR_BDL')):
        lyr = _wczytaj_shp(folder_shp_zrodlowy, nazwa)
        if lyr is None:
            continue
        dopasowane = [f for f in lyr.getFeatures() if f[kolumna] in adresy_wydz]
        wyniki[nazwa] = _zapisz_podzbior(lyr, dopasowane, folder_docelowy, nazwa)

    return wyniki


def uprzatnij_shp(folder_shp_zrodlowy, klucze_dzialek, adresy_wydz):
    """Trwale usuwa z warstw źródłowych (DZKAT/LS/WYDZ/PNSW) obiekty
    dopasowane do wyeksportowanych właścicieli/działek/wydzieleń. Zwraca
    {nazwa_warstwy: liczba_usunietych}."""
    usuniete = {}

    for nazwa in ('DZKAT', 'LS'):
        lyr = _wczytaj_shp(folder_shp_zrodlowy, nazwa)
        if lyr is None:
            continue
        do_usun = [f.id() for f in lyr.getFeatures()
                   if _klucz_dzkat(f) in klucze_dzialek]
        usuniete[nazwa] = _usun_z_warstwy(lyr, do_usun)

    for nazwa, kolumna in (('WYDZ', 'ADR_LES'), ('PNSW', 'ADR_BDL')):
        lyr = _wczytaj_shp(folder_shp_zrodlowy, nazwa)
        if lyr is None:
            continue
        do_usun = [f.id() for f in lyr.getFeatures() if f[kolumna] in adresy_wydz]
        usuniete[nazwa] = _usun_z_warstwy(lyr, do_usun)

    return usuniete


def _klucz_dzkat(feat):
    return (
        isNone(feat['COUNTY']) + isNone(feat['DISTRICT']) + isNone(feat['MUNICIP']),
        isNone(feat['COMMUNITY']), isNone(feat['PARCELNR']),
    )


def _wczytaj_shp(folder, nazwa):
    sc = os.path.join(folder, nazwa + '.shp')
    if not os.path.isfile(sc):
        return None
    lyr = QgsVectorLayer(sc, nazwa, 'ogr')
    return lyr if lyr.isValid() else None


def _zapisz_podzbior(lyr, features, folder_docelowy, nazwa):
    if not features:
        return 0
    lyr.selectByIds([f.id() for f in features])
    sciezka = os.path.join(folder_docelowy, nazwa + '.shp')
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    opcje.onlySelectedFeatures = True
    QgsVectorFileWriter.writeAsVectorFormatV3(
        lyr, sciezka, QgsProject.instance().transformContext(), opcje)
    lyr.removeSelection()
    return len(features)


def _usun_z_warstwy(lyr, ids):
    if not ids:
        return 0
    lyr.startEditing()
    lyr.dataProvider().deleteFeatures(ids)
    lyr.commitChanges()
    return len(ids)


def uprzatnij_baze(baza, parcels, arodes, addr_final):
    """Usuwa z bazy źródłowej wyeksportowane działki (F_PARCEL i zależne)
    oraz - jeśli exportowano opisy taksacyjne (opcja 1) - wydzielenia
    (przez baza_wrapper.Baza.usun_rekordy, już przetestowane, wraz z
    cleanupem opróżnionych ODDZ/L-CTWO). Na końcu usuwa właścicieli
    (V_ADDRESS), którzy po tym nie mają już żadnej pozostałej działki w
    bazie źródłowej (analogicznie do baza_usun_op.py).

    Jeśli opcja 1 NIE była zaznaczona, wydzielenia zostają w bazie
    źródłowej (dane leśne, niezależne od właściciela), ale ich rozliczenie
    powierzchni (F_AROD_LAND_USE) na usuwanych działkach jest i tak
    czyszczone - pozostałe wydzielenia mogą wymagać ponownego
    "Rozlicz powierzchnię wydzieleń"."""
    if not parcels:
        return True

    try:
        for porcja in _porcje(parcels):
            znaki = ','.join('?' for _ in porcja)
            baza.cur.execute(
                'DELETE FROM F_AROD_LAND_USE WHERE PARCEL_INT_NUM IN (' +
                znaki + ')', list(porcja))
        baza.con.commit()
    except Exception as e:
        baza.con.rollback()
        QgsMessageLog.logMessage(
            f'uprzatnij_baze: błąd przy czyszczeniu F_AROD_LAND_USE, '
            f'wycofano zmiany: {e}', 'Las-R', Qgis.Critical)
        return False

    if arodes and not baza.usun_rekordy(sorted(arodes)):
        return False

    try:
        for porcja in _porcje(parcels):
            znaki = ','.join('?' for _ in porcja)
            baza.cur.execute(
                'DELETE FROM V_PARCEL_PARTICIPATION WHERE parcel_int_num '
                'IN (' + znaki + ')', list(porcja))
            baza.cur.execute(
                'DELETE FROM F_PARCEL_LAND_USE WHERE PARCEL_INT_NUM IN (' +
                znaki + ')', list(porcja))
            baza.cur.execute(
                'DELETE FROM F_PARCEL WHERE PARCEL_INT_NUM IN (' +
                znaki + ')', list(porcja))

        if addr_final:
            uzywani_a = baza.cur.execute(
                'select distinct addr_nr from V_PARCEL_PARTICIPATION'
            ).fetchall()
            uzywani_b = baza.cur.execute(
                'select distinct second_addr_nr from V_PARCEL_PARTICIPATION'
            ).fetchall()
            wciaz_uzywani = ({r[0] for r in uzywani_a} |
                              {r[0] for r in uzywani_b if r[0] is not None})
            osierocone = [a for a in addr_final if a not in wciaz_uzywani]
            for porcja in _porcje(osierocone):
                znaki = ','.join('?' for _ in porcja)
                baza.cur.execute(
                    'DELETE FROM V_ADDRESS WHERE ADDR_NR IN (' + znaki + ')',
                    list(porcja))

        baza.con.commit()
    except Exception as e:
        baza.con.rollback()
        QgsMessageLog.logMessage(
            f'uprzatnij_baze: błąd, wycofano zmiany: {e}', 'Las-R',
            Qgis.Critical)
        return False

    return True
