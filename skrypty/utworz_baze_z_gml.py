# -*- coding: utf-8 -*-
"""Utwórz bazę z GML - nowa baza UPUL (kopia wskazanego wzoru pustej bazy)
zasilona działkami, klasoużytkami i właścicielami z plików GML EGiB.

Tryby:
  1) baza w każdym folderze - każdy folder w drzewie pod folderem startowym,
     który BEZPOŚREDNIO zawiera >=1 plik .gml, dostaje własną bazę
     <folder>/<nazwa_folderu>.mdb zasiloną wszystkimi GML z tego folderu;
  2) jedna wspólna baza - wszystkie GML z drzewa do jednej bazy
     <folder_startowy>/<nazwa>_CALOSC.mdb (nazwa do wyboru w dialogu).

Baza docelowa, która już istnieje, przerywa całość przed jakimkolwiek
zapisem (komunikat z listą). Wzór pustej bazy jest tylko kopiowany.

Dane z GML (parsowane wprost przez ElementTree, bez OGR - OGR spłaszcza
zagnieżdżone klasoużytki w listy):
  - EGB_DzialkaEwidencyjna: idDzialki (WWPPGG_R.OOOO[.ARKUSZ].NR),
    poleEwidencyjne, klasoużytki (OFU/OZU/OZK/powierzchnia), odnośnik JRG;
  - EGB_ObrebEwidencyjny (jeśli jest): nazwa obrębu do F_COMMUNITY, a gdy
    go nie ma (EWMAPA) - nazwa ze słownika TERYT wtyczki (teryt_obreby);
  - właściciele (jeśli są - tylko pełny eksport ze starostwa):
    EGB_JednostkaRejestrowaGruntow (numer grupy -> LAND_REGISTER_NR),
    EGB_UdzialWeWlasnosci (licznik/mianownik), EGB_OsobaFizyczna,
    EGB_Instytucja, EGB_PodmiotGrupowy, EGB_Malzenstwo, adresy podmiotów.
    Wg schematu EGiB 1.11; odnośniki rozpoznawane po nazwach elementów
    (przedmiot*/podmiot*/adres*/osobaFizyczna*), bez sztywnej ścieżki.
Działka bez właścicieli w GML dostaje właściciela o nazwie folderu
(podkreślenia -> spacje), udział 1/1 i LAND_REGISTER_NR = 'G1'.

Kody użytków: OFU, a gdy OZU jest inne niż OFU - "OFU-OZU" (np. Lzr-Ps),
dopasowanie do F_AREA_USE_DIC bez względu na wielkość liter. Kody spoza
słownika - użytkownik wybiera, które dopisać (nazwa "nowy", AREA_USE_NR od
najniższego numeru >900 w dół, jak w bazach BDO); niewybrane klasoużytki są
pomijane i trafiają do raportu. Gminy spoza F_MUNICIPALITY - wyraźny
monit z wyborem: konwertuj na kod ze słownika (błędny rodzaj gminy w GML,
np. Chabówka 121112_2 -> 125, gdy TERYT zna te obręby pod kodem ze
słownika; konwersja przed deduplikacją), dopisz gminę do słownika
(gminy się zmieniają, słownik jest stały) albo pomiń działki.

Duplikaty działek (ta sama działka w kilku GML jednej bazy) - zapisywana
raz (pierwsze wystąpienie), właściciele sumowani; różnice powierzchni/
klasoużytków między kopiami - do raportu.
"""
import os
import re
import shutil
import datetime
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)
from qgis.core import Qgis, QgsMessageLog

from . import teryt_obreby
from .baza_wrapper import Baza
from .pw import PasekPostepu
from .waypointy import katalog_raportow

_LOG = 'Las-R'
_TYTUL = 'Utwórz bazę z GML'
_USTAWIENIA = 'Las-R/utworz_baze_z_gml/'

TRYB_FOLDERY = 1
TRYB_CALOSC = 2

GRUPA_DOMYSLNA = 'G1'
NAZWA_NOWEGO_KODU = 'nowy'

# idDzialki: WOJ(2)POW(2)GMI(2)_RODZ(1).OBREB(4).<reszta>, <reszta> to NR
# albo ARKUSZ.NR (numery działek nie zawierają kropek)
_WZORZEC_ID = re.compile(r'^(\d{2})(\d{2})(\d{2})_(\d)\.(\d{4})\.(.+)$')

_RODZAJ_GMINY = {
    '1': 'gm. miejska', '2': 'gm. wiejska', '3': 'gm. miejsko-wiejska',
    '4': 'miasto', '5': 'obszar wiejski',
}

_XLINK_HREF = '{http://www.w3.org/1999/xlink}href'


# ---------------------------------------------------------------------
# parsowanie GML
# ---------------------------------------------------------------------

def _lokalna(tag):
    return tag.rsplit('}', 1)[-1]


def _gml_id(el):
    for klucz, wartosc in el.attrib.items():
        if _lokalna(klucz) == 'id':
            return wartosc
    return None


def _href(el):
    h = el.get(_XLINK_HREF)
    if not h:
        return None
    return h.lstrip('#').strip() or None


def _tekst(el):
    return (el.text or '').strip() if el is not None else ''


def _dziecko(el, nazwa):
    for d in el:
        if _lokalna(d.tag) == nazwa:
            return d
    return None


def _tekst_dziecka(el, nazwa):
    return _tekst(_dziecko(el, nazwa))


def _liczba(tekst):
    try:
        return float(tekst.replace(',', '.'))
    except (AttributeError, ValueError):
        return None


def _calkowita(tekst):
    try:
        return int(float(tekst.replace(',', '.')))
    except (AttributeError, ValueError):
        return None


def _hrefy(el, warunek):
    """Odnośniki xlink z poddrzewa el, z elementów, których nazwa lokalna
    spełnia warunek."""
    return [h for d in el.iter() if warunek(_lokalna(d.tag))
            for h in [_href(d)] if h]


def rozbierz_id_dzialki(id_dz):
    """'121108_2.0003.1488/1' -> dict kodów albo None."""
    m = _WZORZEC_ID.match((id_dz or '').strip())
    if not m:
        return None
    woj, pow_, gmi, rodz, obreb, reszta = m.groups()
    arkusz = None
    if '.' in reszta:
        arkusz, reszta = reszta.split('.', 1)
        arkusz = arkusz.strip() or None
    return {
        'county': woj, 'district': pow_, 'municipality': gmi + rodz,
        'community': obreb, 'arkusz': arkusz, 'nr': reszta.strip(),
    }


def _parsuj_dzialke(el):
    dz = {
        'gml_id': _gml_id(el),
        'id': _tekst_dziecka(el, 'idDzialki'),
        'pole': _liczba(_tekst_dziecka(el, 'poleEwidencyjne')),
        'klasouzytki': [],
        'jrg': [],
    }
    for d in el:
        nazwa = _lokalna(d.tag)
        if nazwa == 'klasouzytek':
            for k in d.iter():
                if _lokalna(k.tag) != 'EGB_Klasouzytek':
                    continue
                dz['klasouzytki'].append((
                    _tekst_dziecka(k, 'OFU'), _tekst_dziecka(k, 'OZU'),
                    _tekst_dziecka(k, 'OZK'),
                    _liczba(_tekst_dziecka(k, 'powierzchnia'))))
        elif nazwa.startswith('JRG'):
            h = _href(d)
            if h:
                dz['jrg'].append(h)
    return dz


def _nazwa_osoby(el):
    czesci = [_tekst_dziecka(el, n) for n in (
        'pierwszyCzlonNazwiska', 'drugiCzlonNazwiska', 'pierwszeImie',
        'drugieImie')]
    return ' '.join(c for c in czesci if c)


def _adres(el):
    czesci = OrderedDict()
    for n in ('miejscowosc', 'ulica', 'numerPorzadkowy', 'numerLokalu',
              'kodPocztowy'):
        czesci[n] = _tekst_dziecka(el, n)
    ulica = czesci['ulica']
    if czesci['numerPorzadkowy']:
        ulica = (ulica + ' ' + czesci['numerPorzadkowy']).strip()
    if czesci['numerLokalu']:
        ulica += '/' + czesci['numerLokalu']
    return {'PLACE': czesci['miejscowosc'], 'STREET': ulica,
            'post_cd': czesci['kodPocztowy'][:8]}


def parsuj_gml(sciezka):
    """Zwraca dict:
      dzialki   [dict z _parsuj_dzialke]
      obreby    {'WWPPGG_R.OOOO': nazwa}
      jrg       {gml_id: numer grupy, np. 'G12'}
      udzialy   [{'jrg': [href], 'podmioty': [href], 'licznik', 'mianownik'}]
      osoby     {gml_id: {'nazwa', 'adresy': [href]}}  (osoby fiz.,
                instytucje, podmioty grupowe)
      malzenstwa {gml_id: [href osoby]}
      adresy    {gml_id: dict adresu}
    """
    wynik = {'dzialki': [], 'obreby': {}, 'jrg': {}, 'udzialy': [],
             'osoby': {}, 'malzenstwa': {}, 'adresy': {}}
    for _zdarzenie, el in ET.iterparse(sciezka, events=('end',)):
        if _lokalna(el.tag) != 'featureMember':
            continue
        for obj in el:
            nazwa = _lokalna(obj.tag)
            gid = _gml_id(obj)
            if nazwa == 'EGB_DzialkaEwidencyjna':
                wynik['dzialki'].append(_parsuj_dzialke(obj))
            elif nazwa == 'EGB_ObrebEwidencyjny':
                ido = _tekst_dziecka(obj, 'idObrebu')
                if ido:
                    wynik['obreby'][ido] = _tekst_dziecka(obj, 'nazwaWlasna')
            elif nazwa == 'EGB_JednostkaRejestrowaGruntow':
                idj = _tekst_dziecka(obj, 'idJednostkiRejestrowej')
                if gid and idj:
                    wynik['jrg'][gid] = idj.rsplit('.', 1)[-1].strip()
            elif nazwa == 'EGB_UdzialWeWlasnosci':
                wynik['udzialy'].append({
                    'jrg': _hrefy(obj, lambda n: n.startswith('JRG')),
                    'podmioty': [
                        h for d in obj
                        if _lokalna(d.tag).startswith('podmiot')
                        for h in _hrefy(d, lambda n: not n.startswith(
                            'podmiot'))],
                    'licznik': _calkowita(_tekst_dziecka(
                        obj, 'licznikUlamkaOkreslajacegoWartoscUdzialu')),
                    'mianownik': _calkowita(_tekst_dziecka(
                        obj, 'mianownikUlamkaOkreslajacegoWartoscUdzialu')),
                })
            elif nazwa in ('EGB_OsobaFizyczna', 'EGB_Instytucja',
                           'EGB_PodmiotGrupowy'):
                if nazwa == 'EGB_OsobaFizyczna':
                    nazwa_podm = _nazwa_osoby(obj)
                else:
                    nazwa_podm = (_tekst_dziecka(obj, 'nazwaPelna') or
                                  _tekst_dziecka(obj, 'nazwaSkrocona'))
                if gid:
                    wynik['osoby'][gid] = {
                        'nazwa': nazwa_podm,
                        'adresy': _hrefy(obj, lambda n: n.startswith(
                            'adres')),
                    }
            elif nazwa == 'EGB_Malzenstwo':
                if gid:
                    wynik['malzenstwa'][gid] = _hrefy(
                        obj, lambda n: n.startswith('osobaFizyczna'))
            elif nazwa.startswith('EGB_Adres'):
                if gid:
                    wynik['adresy'][gid] = _adres(obj)
        el.clear()
    return wynik


def wlasciciele_z_gml(dane):
    """{gml_id JRG: [(klucz, nazwa, adres, licznik, mianownik)]} z udziałów
    we własności jednego pliku GML. Klucz właściciela: ('gml', gml_id
    podmiotu) - ten sam podmiot w kilku plikach to jeden V_ADDRESS."""
    def opis_podmiotu(href):
        if href in dane['malzenstwa']:
            osoby = [dane['osoby'][h] for h in dane['malzenstwa'][href]
                     if h in dane['osoby']]
            if not osoby:
                return None
            nazwa = ' i '.join(o['nazwa'] for o in osoby if o['nazwa'])
            adresy = osoby[0]['adresy']
        elif href in dane['osoby']:
            nazwa = dane['osoby'][href]['nazwa']
            adresy = dane['osoby'][href]['adresy']
        else:
            return None
        adres = next((dane['adresy'][a] for a in adresy
                      if a in dane['adresy']), {})
        return nazwa or '(brak nazwy)', adres

    wynik = {}
    for u in dane['udzialy']:
        for href in u['podmioty']:
            opis = opis_podmiotu(href)
            if opis is None:
                continue
            for jrg in u['jrg']:
                wynik.setdefault(jrg, []).append((
                    ('gml', href), opis[0], opis[1],
                    u['licznik'] or 1, u['mianownik'] or 1))
    return wynik


# ---------------------------------------------------------------------
# słowniki / kody
# ---------------------------------------------------------------------

def kod_uzytku(ofu, ozu):
    ofu = (ofu or '').strip()
    ozu = (ozu or '').strip()
    if not ofu:
        return ozu
    if ozu and ozu.lower() != ofu.lower():
        return ofu + '-' + ozu
    return ofu


def nazwa_wlasciciela_z_folderu(folder):
    nazwa = os.path.basename(os.path.normpath(folder))
    return re.sub(r'\s+', ' ', nazwa.replace('_', ' ')).strip() or nazwa


def podpowiedz_nazwy_calosc(folder_startowy):
    """Pierwsza nazwa w górę drzewa, która nie zaczyna się od '_' (np.
    ...\\Nowy_Targ\\__Geodezja_przerobiona -> Nowy_Targ_CALOSC.mdb)."""
    sc = os.path.normpath(folder_startowy)
    while True:
        nazwa = os.path.basename(sc)
        if nazwa and not nazwa.startswith('_'):
            return nazwa + '_CALOSC.mdb'
        rodzic = os.path.dirname(sc)
        if not nazwa or rodzic == sc:
            break
        sc = rodzic
    return 'CALOSC.mdb'


def znajdz_foldery_z_gml(katalog_startowy):
    wyniki = []
    for root, dirs, files in os.walk(katalog_startowy):
        dirs[:] = sorted(d for d in dirs if d != 'Kopie_manipulacyjne')
        gmle = sorted(os.path.join(root, f) for f in files
                      if f.lower().endswith('.gml'))
        if gmle:
            wyniki.append((root, gmle))
    return wyniki


def zaplanuj_bazy(foldery, tryb, folder_startowy, nazwa_calosc):
    """[(sciezka_bazy, [(folder, [gml])])]"""
    if tryb == TRYB_FOLDERY:
        return [(os.path.join(f, os.path.basename(os.path.normpath(f)) +
                              '.mdb'), [(f, g)]) for f, g in foldery]
    return [(os.path.join(folder_startowy, nazwa_calosc), list(foldery))]


class Slowniki(object):
    """Słowniki odczytane ze wzoru pustej bazy."""

    def __init__(self, baza):
        self.uzytki = {}  # lower -> kod kanoniczny
        self.nr_uzytkow = set()
        for kod, nr in baza.cur.execute(
                'SELECT AREA_USE_CD, AREA_USE_NR FROM F_AREA_USE_DIC'
        ).fetchall():
            if kod:
                self.uzytki[kod.strip().lower()] = kod.strip()
            if nr is not None:
                self.nr_uzytkow.add(int(nr))
        self.klasy = {
            k.strip().upper(): k.strip() for (k,) in baza.cur.execute(
                'SELECT SOIL_QUALITY_CD FROM F_SOIL_QUALITY_DIC').fetchall()
            if k}
        self.gminy = {}
        for row in baza.cur.execute(
                'SELECT COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, '
                'MUNICIPALITY_NAME, TAX_REG FROM F_MUNICIPALITY').fetchall():
            if row[0] and row[1] and row[2]:
                self.gminy[(row[0], row[1], row[2])] = (row[3], row[4])
        self.powiaty = {
            (r[0], r[1]) for r in baza.cur.execute(
                'SELECT COUNTY_CD, DISTRICT_CD FROM F_DISTRICT').fetchall()}

    def numery_nowych_kodow(self, ile):
        """Kolejne wolne AREA_USE_NR od najniższego numeru >900 w dół."""
        powyzej = [n for n in self.nr_uzytkow if n > 900]
        nr = (min(powyzej) if powyzej else 1000) - 1
        wynik = []
        while len(wynik) < ile and nr > 0:
            if nr not in self.nr_uzytkow:
                wynik.append(nr)
            nr -= 1
        return wynik

    def podpowiedz_nazwy_gminy(self, klucz):
        """Nazwa gminy z tym samym kodem (bez rodzaju) w słowniku + rodzaj
        z kodu, np. 'Rabka-Zdrój (gm. wiejska)'."""
        county, district, municip = klucz
        jedn = teryt_obreby.jednostka(
            '%s%s%s_%s' % (county, district, municip[:2], municip[2:]))
        if jedn and jedn[0]:
            # gmina znana w TERYT - nazwa w stylu słownika F_MUNICIPALITY
            przyrostek = {'4': ' Miasto', '5': ' Ob. wiej.'}.get(
                municip[-1:], '')
            return (jedn[0] + przyrostek)[:30]
        rodzaj = _RODZAJ_GMINY.get(municip[-1:], '')
        for (c, d, m), (nazwa, _tax) in sorted(self.gminy.items()):
            if c == county and d == district and m[:2] == municip[:2] and \
                    nazwa and not nazwa.startswith('--'):
                nazwa = re.sub(r'\s+(Miasto|Ob\. wiej\.)$', '', nazwa)
                return (nazwa + ' (' + rodzaj + ')')[:30] if rodzaj else \
                    nazwa[:30]
        return ''

    def tax_reg_powiatu(self, county, district):
        wartosci = [t for (c, d, _m), (_n, t) in self.gminy.items()
                    if c == county and d == district and t]
        return Counter(wartosci).most_common(1)[0][0] if wartosci else None


# ---------------------------------------------------------------------
# przygotowanie danych jednej bazy (bez zapisu)
# ---------------------------------------------------------------------

def klucz_dzialki(kody):
    """Identyfikator działki po ewentualnej konwersji kodu gminy - w
    formacie idDzialki (WWPPGG_R.OOOO[.ARKUSZ].NR)."""
    return '%s.%s%s' % (
        teryt_obreby.id_obrebu(kody['county'], kody['district'],
                               kody['municipality'], kody['community']),
        kody['arkusz'] + '.' if kody['arkusz'] else '', kody['nr'])


def zbierz_dane_bazy(foldery_bazy, sparsowane, konwersje=None):
    """Łączy działki z GML jednej bazy. sparsowane: {sciezka_gml: dane
    z parsuj_gml albo None (błąd)}. konwersje: {(county, district,
    municipality) z GML: municipality docelowe} - zamiana błędnego kodu
    gminy na kod ze słownika PRZED deduplikacją. Zwraca dict:
      dzialki    OrderedDict id -> {'kody', 'pole', 'klasouzytki',
                 'grupa', 'wlasciciele': OrderedDict klucz -> (nazwa,
                 adres, licznik, mianownik), 'zrodlo'}
      obreby     {(county, district, municip, community): nazwa}
      bledne_id  [(gml, id)]
      bez_klasouzytkow [id]
      rozbieznosci [(id, gml_pierwszy, gml_kolejny, opis)]
      duplikaty  int
      z_wlascicielami_gml int
      skonwertowane [(id z GML, id po konwersji)]
    """
    konwersje = konwersje or {}
    dzialki = OrderedDict()
    skonwertowane = []
    obreby = {}
    bledne_id = []
    rozbieznosci = []
    duplikaty = 0
    z_wl_gml = 0

    for folder, gmle in foldery_bazy:
        klucz_folderu = ('folder', os.path.normcase(folder))
        nazwa_folderu = nazwa_wlasciciela_z_folderu(folder)
        for gml in gmle:
            dane = sparsowane.get(gml)
            if dane is None:
                continue
            wl_jrg = wlasciciele_z_gml(dane)
            for dz in dane['dzialki']:
                kody = rozbierz_id_dzialki(dz['id'])
                if kody is None or not kody['nr']:
                    bledne_id.append((gml, dz['id'] or '(brak idDzialki)'))
                    continue
                nowa_gmina = konwersje.get(
                    (kody['county'], kody['district'], kody['municipality']))
                if nowa_gmina:
                    kody['municipality'] = nowa_gmina
                id_dz = klucz_dzialki(kody)
                if nowa_gmina:
                    skonwertowane.append((dz['id'], id_dz))

                wlasciciele = []
                grupa = None
                for jrg in dz['jrg']:
                    if jrg in wl_jrg:
                        wlasciciele.extend(wl_jrg[jrg])
                        grupa = grupa or dane['jrg'].get(jrg)
                if wlasciciele:
                    z_wl_gml += 1
                else:
                    wlasciciele = [(klucz_folderu, nazwa_folderu, {}, 1, 1)]

                klucz_obr = (kody['county'], kody['district'],
                             kody['municipality'], kody['community'])
                if not obreby.get(klucz_obr):
                    # nazwa z GML (EGB_ObrebEwidencyjny), a gdy jej nie ma
                    # (EWMAPA) - ze słownika TERYT wtyczki
                    id_obr = teryt_obreby.id_obrebu(*klucz_obr)
                    obreby[klucz_obr] = (
                        dane['obreby'].get(id_obr) or
                        teryt_obreby.nazwa_obrebu(id_obr) or '')

                klasouzytki = [k for k in dz['klasouzytki']
                               if any(k[:3]) or k[3]]
                istniejaca = dzialki.get(id_dz)
                if istniejaca is not None:
                    duplikaty += 1
                    roznice = []
                    if istniejaca['pole'] != dz['pole']:
                        roznice.append('pow. %s / %s' % (
                            istniejaca['pole'], dz['pole']))
                    if sorted(istniejaca['klasouzytki']) != \
                            sorted(klasouzytki):
                        roznice.append('klasoużytki')
                    if roznice:
                        rozbieznosci.append((
                            id_dz, istniejaca['zrodlo'], gml,
                            ', '.join(roznice)))
                    for k, nazwa, adres, licz, mian in wlasciciele:
                        istniejaca['wlasciciele'].setdefault(
                            k, (nazwa, adres, licz, mian))
                    continue

                wl = OrderedDict()
                for k, nazwa, adres, licz, mian in wlasciciele:
                    wl.setdefault(k, (nazwa, adres, licz, mian))
                dzialki[id_dz] = {
                    'kody': kody, 'pole': dz['pole'],
                    'klasouzytki': klasouzytki,
                    'grupa': (grupa or GRUPA_DOMYSLNA)[:8],
                    'wlasciciele': wl, 'zrodlo': gml,
                }

    return {
        'dzialki': dzialki, 'obreby': obreby, 'bledne_id': bledne_id,
        'bez_klasouzytkow': [i for i, d in dzialki.items()
                             if not d['klasouzytki']],
        'rozbieznosci': rozbieznosci, 'duplikaty': duplikaty,
        'z_wlascicielami_gml': z_wl_gml,
        'skonwertowane': skonwertowane,
        'obreby_bez_nazwy': sorted(
            teryt_obreby.id_obrebu(*k) for k, n in obreby.items() if not n),
    }


def brakujace_w_slownikach(dane_baz, slowniki):
    """Zwraca (kody, gminy, obreby_gmin): Counter brakujących kodów użytków
    (liczba klasoużytków), Counter brakujących gmin (liczba działek) i
    {gmina: {id_obr}} obrębów tych gmin - po wszystkich bazach."""
    kody = Counter()
    gminy = Counter()
    obreby_gmin = {}
    for dane in dane_baz:
        for d in dane['dzialki'].values():
            k = d['kody']
            klucz = (k['county'], k['district'], k['municipality'])
            if klucz not in slowniki.gminy:
                gminy[klucz] += 1
                obreby_gmin.setdefault(klucz, set()).add(
                    teryt_obreby.id_obrebu(*(klucz + (k['community'],))))
            for ofu, ozu, _ozk, _pow in d['klasouzytki']:
                kod = kod_uzytku(ofu, ozu)
                if kod and kod.lower() not in slowniki.uzytki:
                    kody[kod] += 1
    return kody, gminy, obreby_gmin


def uwagi_teryt_gminy(klucz, ids_obrebow):
    """Opis gminy spoza F_MUNICIPALITY wg słownika TERYT: czy taka
    jednostka w ogóle istnieje, a jeśli nie - pod jakim kodem TERYT zna
    obręby o tych numerach (możliwy błąd rodzaju gminy w GML)."""
    county, district, municip = klucz
    jedn = teryt_obreby.jednostka(
        '%s%s%s_%s' % (county, district, municip[:2], municip[2:]))
    if jedn:
        return 'w TERYT istnieje: ' + jedn[1]
    podpowiedzi = []
    for id_obr in sorted(ids_obrebow):
        inne = teryt_obreby.inne_rodzaje(id_obr)
        if inne:
            podpowiedzi.append('obręb %s w TERYT jako: %s' % (
                id_obr[-4:], ', '.join('%s %s' % (i, n) for i, n, _j in inne)))
    if podpowiedzi:
        return ('BRAK w TERYT - możliwy błąd kodu gminy w GML; ' +
                '; '.join(podpowiedzi))
    return 'BRAK w TERYT'


def kandydaci_konwersji(klucz, ids_obrebow, slowniki):
    """Kody gminy (ten sam numer gminy, inny rodzaj), na które można
    skonwertować gminę spoza słownika: gmina jest w F_MUNICIPALITY wzoru,
    a WSZYSTKIE obręby z GML istnieją pod nią w TERYT. Zwraca
    [(MUNICIPALITY_CD, opis)], najpierw rodzaj odpowiadający kodowi z GML
    (gm. wiejska 2 -> obszar wiejski 5, gm. miejska 1 -> miasto 4)."""
    county, district, municip = klucz
    preferowany = {'2': '5', '1': '4'}.get(municip[2:], '')
    wynik = []
    for rodzaj in '12345':
        cel = municip[:2] + rodzaj
        if cel == municip or (county, district, cel) not in slowniki.gminy:
            continue
        nazwy = []
        for id_obr in sorted(ids_obrebow):
            nazwa = teryt_obreby.nazwa_obrebu(id_obr[:7] + rodzaj + id_obr[8:])
            if not nazwa:
                break
            nazwy.append(nazwa)
        else:
            nazwa_gminy = slowniki.gminy[(county, district, cel)][0] or ''
            wynik.append((cel, '%s - %s (%s)' % (
                cel, nazwa_gminy, ', '.join(nazwy))))
    wynik.sort(key=lambda k: k[0][2:] != preferowany)
    return wynik


# ---------------------------------------------------------------------
# zapis jednej bazy
# ---------------------------------------------------------------------

def zapisz_baze(baza, dane, slowniki, nowe_kody, nowe_gminy, postep=None):
    """Zapis w jednej transakcji (commit/rollback robi wywołujący).
    nowe_kody: {kod: AREA_USE_NR}, nowe_gminy: {klucz: nazwa}. Zwraca dict
    statystyk."""
    cur = baza.cur
    stat = Counter()
    pominiete_uzytki = Counter()
    nieznane_klasy = Counter()
    pominiete_gmina = []

    for kod, nr in nowe_kody.items():
        cur.execute(
            'INSERT INTO F_AREA_USE_DIC (AREA_USE_CD, AREA_USE_NAME, '
            'AREA_USE_NR) VALUES (?,?,?)', (kod, NAZWA_NOWEGO_KODU, nr))
    uzytki = dict(slowniki.uzytki)
    uzytki.update({k.lower(): k for k in nowe_kody})

    gminy = set(slowniki.gminy)
    potrzebne_gminy = {
        (d['kody']['county'], d['kody']['district'],
         d['kody']['municipality']) for d in dane['dzialki'].values()}
    for klucz, nazwa in nowe_gminy.items():
        if klucz not in potrzebne_gminy:
            continue
        county, district, municip = klucz
        cur.execute(
            'INSERT INTO F_MUNICIPALITY (COUNTY_CD, DISTRICT_CD, '
            'MUNICIPALITY_CD, MUNICIPALITY_NAME, MUNICIPALITY_NR, '
            'DISTRICT_NR, COUNTY_NR, TAX_REG) VALUES (?,?,?,?,?,?,?,?)',
            (county, district, municip, nazwa[:30], int(municip),
             int(district), int(county),
             slowniki.tax_reg_powiatu(county, district)))
        gminy.add(klucz)
        stat['gminy'] += 1

    for (county, district, municip, community), nazwa in sorted(
            dane['obreby'].items()):
        if (county, district, municip) not in gminy:
            continue
        cur.execute(
            'INSERT INTO F_COMMUNITY (COUNTY_CD, DISTRICT_CD, '
            'MUNICIPALITY_CD, COMMUNITY_CD, COMMUNITY_NAME) '
            'VALUES (?,?,?,?,?)',
            # pusty string odrzucany przez bazę (Allow Zero Length = Nie);
            # GML z EWMAPY nie ma EGB_ObrebEwidencyjny -> NULL
            (county, district, municip, community, (nazwa or '')[:30] or
             None))
        stat['obreby'] += 1

    adresy_nr = {}
    ile = len(dane['dzialki'])
    for i, (id_dz, d) in enumerate(dane['dzialki'].items()):
        if postep is not None and i % 200 == 0:
            postep(i, ile)
        k = d['kody']
        if (k['county'], k['district'], k['municipality']) not in gminy:
            pominiete_gmina.append(id_dz)
            continue

        kolumny = ['PARCEL_NR', 'COUNTY_CD', 'DISTRICT_CD',
                   'MUNICIPALITY_CD', 'COMMUNITY_CD', 'PARCEL_AREA',
                   'LAND_REGISTER_NR']
        wartosci = [k['nr'][:20], k['county'], k['district'],
                    k['municipality'], k['community'], d['pole'],
                    d['grupa']]
        if k['arkusz']:
            kolumny += ['REG_SHEET_NR1', 'REG_SHEET_NR2']
            wartosci += [k['arkusz'][:11], k['arkusz'][:11]]
        cur.execute(
            'INSERT INTO F_PARCEL (' + ', '.join(kolumny) + ') VALUES (' +
            ','.join('?' * len(kolumny)) + ')', tuple(wartosci))
        parcel_int_num = int(cur.execute('SELECT @@IDENTITY').fetchval())
        stat['dzialki'] += 1

        shape_nr = 0
        for ofu, ozu, ozk, pow_ in d['klasouzytki']:
            kod = kod_uzytku(ofu, ozu)
            kod_kan = uzytki.get(kod.lower()) if kod else None
            if kod_kan is None:
                pominiete_uzytki[kod or '(pusty)'] += 1
                continue
            klasa = None
            if ozk:
                klasa = slowniki.klasy.get(ozk.strip().upper())
                if klasa is None:
                    nieznane_klasy[ozk] += 1
            shape_nr += 1
            cur.execute(
                'INSERT INTO F_PARCEL_LAND_USE (PARCEL_INT_NUM, SHAPE_NR, '
                'SOIL_QUALITY_CD, AREA_USE_CD, LAND_USE_AREA, AFFORESTATION) '
                'VALUES (?,?,?,?,?,?)',
                (parcel_int_num, shape_nr, klasa, kod_kan, pow_, False))
            stat['klasouzytki'] += 1

        for klucz_wl, (nazwa, adres, licz, mian) in d['wlasciciele'].items():
            addr_nr = adresy_nr.get(klucz_wl)
            if addr_nr is None:
                cur.execute(
                    'INSERT INTO V_ADDRESS (NAME_1, PLACE, STREET, post_cd, '
                    'VIEW_ADDRESS_FL, LP_PRICE) VALUES (?,?,?,?,?,?)',
                    (nazwa[:255], adres.get('PLACE') or None,
                     adres.get('STREET') or None,
                     adres.get('post_cd') or None, False, False))
                addr_nr = int(cur.execute('SELECT @@IDENTITY').fetchval())
                adresy_nr[klucz_wl] = addr_nr
                stat['wlasciciele'] += 1
            cur.execute(
                'INSERT INTO V_PARCEL_PARTICIPATION (addr_nr, '
                'parcel_int_num, part_numerator, part_denominator) '
                'VALUES (?,?,?,?)', (addr_nr, parcel_int_num, licz, mian))

    stat['pominiete_uzytki'] = pominiete_uzytki
    stat['nieznane_klasy'] = nieznane_klasy
    stat['pominiete_gmina'] = pominiete_gmina
    return stat


# ---------------------------------------------------------------------
# dialogi
# ---------------------------------------------------------------------

class _DialogGlowny(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(_TYTUL)
        self.setMinimumWidth(640)
        ust = QSettings()

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()

        self.pole_folder = QLineEdit(ust.value(_USTAWIENIA + 'folder', ''))
        przycisk_folder = QPushButton('Przeglądaj...')
        przycisk_folder.clicked.connect(self._wybierz_folder)
        siatka.addWidget(QLabel('Folder startowy (z GML):'), 0, 0)
        siatka.addWidget(self.pole_folder, 0, 1)
        siatka.addWidget(przycisk_folder, 0, 2)

        self.pole_wzor = QLineEdit(ust.value(_USTAWIENIA + 'wzor', ''))
        przycisk_wzor = QPushButton('Przeglądaj...')
        przycisk_wzor.clicked.connect(self._wybierz_wzor)
        siatka.addWidget(QLabel('Wzór pustej bazy:'), 1, 0)
        siatka.addWidget(self.pole_wzor, 1, 1)
        siatka.addWidget(przycisk_wzor, 1, 2)
        uklad.addLayout(siatka)

        self.radio_foldery = QRadioButton(
            'Baza w każdym folderze z GML  (<folder>\\<nazwa_folderu>.mdb)')
        self.radio_calosc = QRadioButton(
            'Jedna wspólna baza dla wszystkich GML  (w folderze startowym)')
        grupa = QButtonGroup(self)
        grupa.addButton(self.radio_foldery)
        grupa.addButton(self.radio_calosc)
        if int(ust.value(_USTAWIENIA + 'tryb', TRYB_FOLDERY)) == TRYB_CALOSC:
            self.radio_calosc.setChecked(True)
        else:
            self.radio_foldery.setChecked(True)
        uklad.addWidget(self.radio_foldery)
        uklad.addWidget(self.radio_calosc)

        wiersz = QHBoxLayout()
        wiersz.addSpacing(20)
        wiersz.addWidget(QLabel('Nazwa wspólnej bazy:'))
        self.pole_nazwa = QLineEdit()
        wiersz.addWidget(self.pole_nazwa)
        uklad.addLayout(wiersz)

        self.etykieta_info = QLabel('')
        self.etykieta_info.setWordWrap(True)
        uklad.addWidget(self.etykieta_info)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.button(QDialogButtonBox.Ok).setText('Utwórz')
        przyciski.accepted.connect(self._akceptuj)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

        self.pole_folder.editingFinished.connect(self._na_zmiane_folderu)
        self.radio_calosc.toggled.connect(self._aktualizuj)
        self._na_zmiane_folderu()

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder startowy z plikami GML',
            self.pole_folder.text().strip())
        if sc:
            self.pole_folder.setText(os.path.normpath(sc))
            self._na_zmiane_folderu()

    def _wybierz_wzor(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż wzór pustej bazy',
            os.path.dirname(self.pole_wzor.text().strip()),
            'Access MDB (*.mdb)')[0]
        if sc:
            self.pole_wzor.setText(os.path.normpath(sc))

    def _na_zmiane_folderu(self):
        folder = self.pole_folder.text().strip()
        if folder and os.path.isdir(folder):
            self.pole_nazwa.setText(podpowiedz_nazwy_calosc(folder))
            foldery = znajdz_foldery_z_gml(folder)
            self.etykieta_info.setText(
                'Znaleziono folderów z GML: %d, plików GML: %d.' % (
                    len(foldery), sum(len(g) for _f, g in foldery)))
        else:
            self.etykieta_info.setText('')
        self._aktualizuj()

    def _aktualizuj(self, *_):
        self.pole_nazwa.setEnabled(self.radio_calosc.isChecked())

    def _akceptuj(self):
        folder = self.folder()
        wzor = self.wzor()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, _TYTUL, 'Wskaż istniejący folder.')
            return
        if not wzor or not os.path.isfile(wzor):
            QMessageBox.warning(self, _TYTUL, 'Wskaż plik wzoru pustej bazy.')
            return
        if self.tryb() == TRYB_CALOSC:
            nazwa = self.nazwa_calosc()
            if not nazwa or re.search(r'[\\/:*?"<>|]', nazwa):
                QMessageBox.warning(
                    self, _TYTUL, 'Podaj poprawną nazwę wspólnej bazy.')
                return
        ust = QSettings()
        ust.setValue(_USTAWIENIA + 'folder', folder)
        ust.setValue(_USTAWIENIA + 'wzor', wzor)
        ust.setValue(_USTAWIENIA + 'tryb', self.tryb())
        self.accept()

    def folder(self):
        return os.path.normpath(self.pole_folder.text().strip()) \
            if self.pole_folder.text().strip() else ''

    def wzor(self):
        return os.path.normpath(self.pole_wzor.text().strip()) \
            if self.pole_wzor.text().strip() else ''

    def tryb(self):
        return TRYB_CALOSC if self.radio_calosc.isChecked() else TRYB_FOLDERY

    def nazwa_calosc(self):
        nazwa = self.pole_nazwa.text().strip()
        if nazwa and not nazwa.lower().endswith('.mdb'):
            nazwa += '.mdb'
        elif nazwa:
            nazwa = nazwa[:-4] + '.mdb'
        return nazwa


class _DialogKodow(QDialog):
    """Wybór kodów użytków spoza słownika do dopisania z nazwą 'nowy'."""

    def __init__(self, parent, kody):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL + ' - kody użytków spoza słownika')
        self.setMinimumWidth(520)
        uklad = QVBoxLayout(self)
        opis = QLabel(
            'W GML są kody użytków, których nie ma w słowniku '
            'F_AREA_USE_DIC wzoru bazy.\nZaznaczone zostaną dopisane do '
            'słownika nowej bazy z nazwą "nowy".\nKlasoużytki z kodami '
            'NIEzaznaczonymi zostaną pominięte (wypisane w raporcie).')
        uklad.addWidget(opis)

        self.tabela = QTableWidget(len(kody), 2)
        self.tabela.setHorizontalHeaderLabels(['Kod użytku', 'Klasoużytków'])
        self.tabela.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.tabela.verticalHeader().setVisible(False)
        for w, (kod, ile) in enumerate(kody.most_common()):
            item = QTableWidgetItem(kod)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.tabela.setItem(w, 0, item)
            item = QTableWidgetItem(str(ile))
            item.setFlags(Qt.ItemIsEnabled)
            self.tabela.setItem(w, 1, item)
        uklad.addWidget(self.tabela)

        wiersz = QHBoxLayout()
        for tekst, stan in (('Zaznacz wszystkie', Qt.Checked),
                            ('Odznacz wszystkie', Qt.Unchecked)):
            p = QPushButton(tekst)
            p.clicked.connect(lambda _c, s=stan: self._ustaw(s))
            wiersz.addWidget(p)
        wiersz.addStretch()
        uklad.addLayout(wiersz)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.accepted.connect(self.accept)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

    def _ustaw(self, stan):
        for w in range(self.tabela.rowCount()):
            self.tabela.item(w, 0).setCheckState(stan)

    def wybrane(self):
        return [self.tabela.item(w, 0).text()
                for w in range(self.tabela.rowCount())
                if self.tabela.item(w, 0).checkState() == Qt.Checked]


AKCJA_KONWERTUJ = 'Konwertuj na kod ze słownika'
AKCJA_DOPISZ = 'Dopisz gminę do słownika'
AKCJA_POMIN = 'Pomiń działki'


class _DialogGmin(QDialog):
    """Monit o gminach spoza F_MUNICIPALITY: konwertuj kod na gminę ze
    słownika, dopisz gminę do słownika albo pomiń działki."""

    def __init__(self, parent, gminy, slowniki, uwagi, kandydaci):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL + ' - WYKRYTO NOWĄ GMINĘ')
        self.setMinimumWidth(1000)
        self._klucze = []
        self._kandydaci = kandydaci
        self._akcje = []
        self._cele = []
        self._nazwy = []
        uklad = QVBoxLayout(self)

        ostrzezenie = QLabel(
            'UWAGA: w GML wykryto gminy, których NIE MA w słowniku '
            'F_MUNICIPALITY wzoru bazy.\n\n'
            '- Konwertuj: błędny kod gminy w GML - działki dostają kod gminy '
            'ze słownika\n  (obręby bez zmian), proponowany, gdy TERYT zna '
            'te obręby pod innym kodem.\n'
            '- Dopisz: prawdziwie nowa gmina (gminy się zmieniają, słownik '
            'jest stały).\n'
            '- Pomiń: działki z tej gminy NIE trafią do bazy.')
        ostrzezenie.setStyleSheet('color: #b00000; font-weight: bold;')
        uklad.addWidget(ostrzezenie)

        self.tabela = QTableWidget(len(gminy), 6)
        self.tabela.setHorizontalHeaderLabels(
            ['Kod z GML', 'Działek', 'Słownik TERYT', 'Akcja',
             'Kod docelowy (konwersja)', 'Nazwa gminy (dopisanie)'])
        self.tabela.verticalHeader().setVisible(False)
        for w, (klucz, ile) in enumerate(sorted(gminy.items())):
            self._klucze.append(klucz)
            item = QTableWidgetItem(' '.join(klucz))
            item.setFlags(Qt.ItemIsEnabled)
            self.tabela.setItem(w, 0, item)
            item = QTableWidgetItem(str(ile))
            item.setFlags(Qt.ItemIsEnabled)
            self.tabela.setItem(w, 1, item)
            uwaga = uwagi.get(klucz, '')
            item = QTableWidgetItem(uwaga)
            item.setFlags(Qt.ItemIsEnabled)
            item.setToolTip(uwaga)
            if uwaga.startswith('BRAK'):
                item.setForeground(QColor('#b00000'))
            self.tabela.setItem(w, 2, item)

            cele = QComboBox()
            for municip, opis in kandydaci.get(klucz, []):
                cele.addItem(opis, municip)
            self.tabela.setCellWidget(w, 4, cele)
            self._cele.append(cele)

            nazwa = QLineEdit(slowniki.podpowiedz_nazwy_gminy(klucz))
            nazwa.setMaxLength(30)
            self.tabela.setCellWidget(w, 5, nazwa)
            self._nazwy.append(nazwa)

            akcja = QComboBox()
            if kandydaci.get(klucz):
                akcja.addItem(AKCJA_KONWERTUJ)
            if (klucz[0], klucz[1]) in slowniki.powiaty:
                akcja.addItem(AKCJA_DOPISZ)
            akcja.addItem(AKCJA_POMIN)
            # domyślnie: konwersja, gdy jednostki nie ma w TERYT, a TERYT
            # zna obręby pod kodem ze słownika; prawdziwie nowa gmina
            # (jest w TERYT) - dopisanie
            if kandydaci.get(klucz) and uwaga.startswith('BRAK'):
                akcja.setCurrentText(AKCJA_KONWERTUJ)
            elif akcja.findText(AKCJA_DOPISZ) >= 0:
                akcja.setCurrentText(AKCJA_DOPISZ)
            akcja.currentTextChanged.connect(
                lambda _t, w=w: self._odswiez_wiersz(w))
            self.tabela.setCellWidget(w, 3, akcja)
            self._akcje.append(akcja)
            self._odswiez_wiersz(w)

        self.tabela.resizeColumnsToContents()
        self.tabela.setColumnWidth(2, 320)
        self.tabela.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.Stretch)
        uklad.addWidget(self.tabela)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.accepted.connect(self._akceptuj)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

    def _odswiez_wiersz(self, w):
        akcja = self._akcje[w].currentText() if w < len(self._akcje) else ''
        self._cele[w].setEnabled(akcja == AKCJA_KONWERTUJ)
        self._nazwy[w].setEnabled(akcja == AKCJA_DOPISZ)

    def _akceptuj(self):
        for w, akcja in enumerate(self._akcje):
            if akcja.currentText() == AKCJA_DOPISZ and \
                    not self._nazwy[w].text().strip():
                QMessageBox.warning(
                    self, _TYTUL, 'Podaj nazwę dla każdej dopisywanej gminy.')
                return
        pominiete = [' '.join(self._klucze[w])
                     for w, a in enumerate(self._akcje)
                     if a.currentText() == AKCJA_POMIN]
        if pominiete and QMessageBox.question(
                self, _TYTUL,
                'Gminy pominięte: ' + ', '.join(pominiete) + '\n\n'
                'Działki z tych gmin NIE trafią do bazy. Kontynuować?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        self.accept()

    def nowe_gminy(self):
        """{gmina: nazwa} do dopisania do F_MUNICIPALITY."""
        return {self._klucze[w]: self._nazwy[w].text().strip()[:30]
                for w, a in enumerate(self._akcje)
                if a.currentText() == AKCJA_DOPISZ}

    def konwersje(self):
        """{gmina z GML: MUNICIPALITY_CD docelowe}."""
        return {self._klucze[w]: self._cele[w].currentData()
                for w, a in enumerate(self._akcje)
                if a.currentText() == AKCJA_KONWERTUJ and
                self._cele[w].currentData()}


# ---------------------------------------------------------------------
# uruchomienie
# ---------------------------------------------------------------------

def _komunikat(iface, tekst, poziom=Qgis.Critical):
    iface.messageBar().pushMessage(_TYTUL, tekst, poziom, 10)


def _wczytaj_slowniki(wzor):
    baza = Baza(wzor)
    try:
        if not baza.polacz():
            return None, 'Nie udało się połączyć ze wzorem bazy.'
        ile = baza.cur.execute('SELECT COUNT(*) FROM F_PARCEL').fetchval()
        if ile:
            return None, ('Wzór bazy nie jest pusty (F_PARCEL: %d '
                          'działek) - wskaż pustą bazę.' % ile)
        return Slowniki(baza), None
    except Exception as e:
        return None, 'Błąd odczytu słowników wzoru bazy: ' + str(e)
    finally:
        baza.zamknij()


def uruchom(iface):
    dlg = _DialogGlowny(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False
    folder_startowy = dlg.folder()
    wzor = dlg.wzor()
    tryb = dlg.tryb()

    foldery = znajdz_foldery_z_gml(folder_startowy)
    if not foldery:
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            'W folderze startowym nie ma plików GML.')
        return False

    plan = zaplanuj_bazy(foldery, tryb, folder_startowy, dlg.nazwa_calosc())
    istniejace = [sc for sc, _f in plan if os.path.exists(sc)]
    if istniejace:
        QMessageBox.critical(
            iface.mainWindow(), _TYTUL,
            'Przerwano - bazy docelowe już istnieją (%d):\n\n' %
            len(istniejace) + '\n'.join(istniejace[:30]) +
            ('\n...' if len(istniejace) > 30 else '') +
            '\n\nUsuń je albo zmień nazwę i uruchom ponownie.')
        return False
    if any(os.path.normcase(sc) == os.path.normcase(wzor)
           for sc, _f in plan):
        QMessageBox.critical(iface.mainWindow(), _TYTUL,
                             'Wzór bazy nie może być bazą docelową.')
        return False

    slowniki, blad = _wczytaj_slowniki(wzor)
    if slowniki is None:
        QMessageBox.critical(iface.mainWindow(), _TYTUL, blad)
        return False

    QgsMessageLog.logMessage('------ ' + _TYTUL.upper() + ' ------', _LOG,
                             Qgis.Info)
    pasek = PasekPostepu(iface)
    postep = pasek.stworz_pasek('Odczyt GML...')

    # 1. parsowanie
    pliki = [g for _f, gmle in foldery for g in gmle]
    postep.setMaximum(len(pliki))
    sparsowane = {}
    bledy_gml = []
    for i, gml in enumerate(pliki):
        postep.setValue(i)
        QApplication.processEvents()
        try:
            sparsowane[gml] = parsuj_gml(gml)
        except Exception as e:
            sparsowane[gml] = None
            bledy_gml.append((gml, str(e)))
            QgsMessageLog.logMessage(
                'Błąd odczytu GML %s: %s' % (gml, e), _LOG, Qgis.Warning)

    dane_baz = [zbierz_dane_bazy(foldery_bazy, sparsowane)
                for _sc, foldery_bazy in plan]
    pasek.clear()

    # 2. słowniki: kody użytków i gminy
    brak_kodow, brak_gmin, obreby_gmin = brakujace_w_slownikach(
        dane_baz, slowniki)
    uwagi_gmin = {k: uwagi_teryt_gminy(k, obreby_gmin[k]) for k in brak_gmin}
    nowe_kody = {}
    if brak_kodow:
        dk = _DialogKodow(iface.mainWindow(), brak_kodow)
        if dk.exec_() != QDialog.Accepted:
            _komunikat(iface, 'Anulowano - nie utworzono żadnej bazy.',
                       Qgis.Warning)
            return False
        wybrane = dk.wybrane()
        nowe_kody = dict(zip(wybrane,
                             slowniki.numery_nowych_kodow(len(wybrane))))
    nowe_gminy = {}
    konwersje = {}
    if brak_gmin:
        kandydaci = {k: kandydaci_konwersji(k, obreby_gmin[k], slowniki)
                     for k in brak_gmin}
        dg = _DialogGmin(iface.mainWindow(), brak_gmin, slowniki, uwagi_gmin,
                         kandydaci)
        if dg.exec_() != QDialog.Accepted:
            _komunikat(iface, 'Anulowano - nie utworzono żadnej bazy.',
                       Qgis.Warning)
            return False
        nowe_gminy = dg.nowe_gminy()
        konwersje = dg.konwersje()
        if konwersje:
            # ponowne zebranie z kodami po konwersji - deduplikacja i nazwy
            # obrębów (TERYT) liczone już dla kodu ze słownika
            dane_baz = [zbierz_dane_bazy(foldery_bazy, sparsowane, konwersje)
                        for _sc, foldery_bazy in plan]

    # 3. tworzenie baz
    wyniki = []
    postep = pasek.stworz_pasek('Tworzenie baz z GML...')
    for nr, ((sc_bazy, foldery_bazy), dane) in enumerate(zip(plan, dane_baz)):
        wynik = {'baza': sc_bazy, 'foldery': foldery_bazy, 'dane': dane,
                 'stat': None, 'blad': None}
        wyniki.append(wynik)
        if not dane['dzialki']:
            wynik['blad'] = 'brak działek w GML - bazy nie utworzono'
            continue

        def _postep(i, ile, nr=nr):
            postep.setMaximum(max(ile, 1))
            postep.setValue(i)
            pasek.progressMessageBarItem.setText(
                'Tworzenie baz z GML... (%d/%d) %s' % (
                    nr + 1, len(plan), os.path.basename(sc_bazy)))
            QApplication.processEvents()

        shutil.copyfile(wzor, sc_bazy)
        baza = Baza(sc_bazy)
        try:
            if not baza.polacz():
                raise RuntimeError('nie udało się połączyć z nową bazą')
            wynik['stat'] = zapisz_baze(baza, dane, slowniki, nowe_kody,
                                        nowe_gminy, _postep)
            baza.con.commit()
        except Exception as e:
            try:
                baza.con.rollback()
            except Exception:
                pass
            wynik['blad'] = 'zapis nie powiódł się: ' + str(e)
            wynik['stat'] = None
            QgsMessageLog.logMessage(
                'Błąd zapisu %s: %s' % (sc_bazy, e), _LOG, Qgis.Critical)
        finally:
            baza.zamknij()
        if wynik['blad']:
            # kopia wzoru utworzona przed chwilą przez ten skrypt - usuwana,
            # żeby ponowne uruchomienie nie zatrzymało się na "baza istnieje"
            try:
                os.remove(sc_bazy)
            except OSError:
                pass
    pasek.clear()

    # 4. raport
    sc_raportu = _zapisz_raport(folder_startowy, wzor, tryb, wyniki,
                                bledy_gml, nowe_kody, nowe_gminy,
                                brak_kodow, brak_gmin, uwagi_gmin, konwersje)
    utworzone = sum(1 for w in wyniki if w['stat'] is not None)
    bledne = [w for w in wyniki if w['blad'] and w['dane']['dzialki']]

    message = QMessageBox(iface.mainWindow())
    message.setIcon(QMessageBox.Warning if bledne else
                    QMessageBox.Information)
    message.setWindowTitle(_TYTUL)
    message.setText('Utworzono baz: %d z %d.%s\n\nCzy pokazać raport?' % (
        utworzone, len(plan),
        '\nBłędy zapisu: %d (szczegóły w raporcie).' % len(bledne)
        if bledne else ''))
    message.addButton('Zamknij', QMessageBox.ActionRole)
    message.addButton('Zamknij i pokaż raport', QMessageBox.ActionRole)
    if message.exec_() == 1:
        os.startfile(sc_raportu)

    QgsMessageLog.logMessage('------ KONIEC ------\n', _LOG, Qgis.Info)
    return utworzone > 0


def _zapisz_raport(folder_startowy, wzor, tryb, wyniki, bledy_gml,
                   nowe_kody, nowe_gminy, brak_kodow, brak_gmin,
                   uwagi_gmin=None, konwersje=None):
    czas = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    w = []
    w.append('---- ' + _TYTUL.upper() + ' ----\n')
    w.append('Folder startowy: ' + folder_startowy)
    w.append('Wzór bazy: ' + wzor)
    w.append('Tryb: ' + ('baza w każdym folderze' if tryb == TRYB_FOLDERY
                         else 'jedna wspólna baza'))
    w.append('')

    if bledy_gml:
        w.append('!!! PLIKI GML, KTÓRYCH NIE UDAŁO SIĘ ODCZYTAĆ (%d):' %
                 len(bledy_gml))
        w.extend('  %s: %s' % b for b in bledy_gml)
        w.append('')

    if brak_kodow:
        w.append('Kody użytków spoza słownika F_AREA_USE_DIC:')
        for kod, ile in brak_kodow.most_common():
            w.append('  %-10s %5d klasoużytków  -> %s' % (
                kod, ile, 'DOPISANY ("%s", AREA_USE_NR=%d)' % (
                    NAZWA_NOWEGO_KODU, nowe_kody[kod])
                if kod in nowe_kody else 'POMINIĘTY'))
        w.append('')
    if brak_gmin:
        w.append('Gminy spoza słownika F_MUNICIPALITY:')
        for klucz, ile in sorted(brak_gmin.items()):
            w.append('  %s  %5d działek  -> %s' % (
                ' '.join(klucz), ile,
                'DOPISANA jako "%s"' % nowe_gminy[klucz]
                if klucz in nowe_gminy else
                'SKONWERTOWANA na %s' % konwersje[klucz]
                if konwersje and klucz in konwersje else
                'POMINIĘTA - działki nie trafiły do bazy'))
            if uwagi_gmin and uwagi_gmin.get(klucz):
                w.append('      TERYT: ' + uwagi_gmin[klucz])
        w.append('')

    for wynik in wyniki:
        dane = wynik['dane']
        stat = wynik['stat']
        w.append('=' * 70)
        w.append('Baza: ' + wynik['baza'])
        for folder, gmle in wynik['foldery']:
            w.append('  folder: %s  (%d GML)' % (folder, len(gmle)))
        if wynik['blad']:
            w.append('  !!! ' + wynik['blad'])
        if stat is not None:
            w.append('  Działek zapisanych: %d' % stat['dzialki'])
            w.append('  Klasoużytków zapisanych: %d' % stat['klasouzytki'])
            w.append('  Obrębów (F_COMMUNITY): %d' % stat['obreby'])
            w.append('  Właścicieli (V_ADDRESS): %d' % stat['wlasciciele'])
            if stat['gminy']:
                w.append('  Dopisanych gmin (F_MUNICIPALITY): %d' %
                         stat['gminy'])
        w.append('  Działek z właścicielami z GML: %d (pozostałe: '
                 'właściciel z nazwy folderu, grupa %s)' % (
                     dane['z_wlascicielami_gml'], GRUPA_DOMYSLNA))
        w.append('  Duplikatów działek między GML (zapisane raz): %d' %
                 dane['duplikaty'])
        if dane['rozbieznosci']:
            w.append('  Duplikaty z rozbieżnościami (zapisano pierwszą '
                     'kopię) - %d:' % len(dane['rozbieznosci']))
            for id_dz, g1, g2, opis in dane['rozbieznosci']:
                w.append('    %s: %s  [%s | %s]' % (
                    id_dz, opis, os.path.basename(g1), os.path.basename(g2)))
        if dane['skonwertowane']:
            w.append('  Działki ze skonwertowanym kodem gminy (GML -> baza) '
                     '- %d:' % len(dane['skonwertowane']))
            w.extend('    %s -> %s' % x for x in dane['skonwertowane'])
        if dane['obreby_bez_nazwy']:
            w.append('  Obręby bez nazwy (brak w GML i w słowniku TERYT, '
                     'COMMUNITY_NAME = NULL) - %d: %s' % (
                         len(dane['obreby_bez_nazwy']),
                         ', '.join(dane['obreby_bez_nazwy'])))
        if dane['bez_klasouzytkow']:
            w.append('  Działki bez klasoużytków w GML - %d:' %
                     len(dane['bez_klasouzytkow']))
            w.extend('    ' + i for i in dane['bez_klasouzytkow'])
        if dane['bledne_id']:
            w.append('  !!! Działki z niepoprawnym idDzialki (pominięte) - '
                     '%d:' % len(dane['bledne_id']))
            w.extend('    %s  [%s]' % (i, os.path.basename(g))
                     for g, i in dane['bledne_id'])
        if stat is not None:
            if stat['pominiete_gmina']:
                w.append('  !!! Działki pominięte - gmina spoza słownika - '
                         '%d:' % len(stat['pominiete_gmina']))
                w.extend('    ' + i for i in stat['pominiete_gmina'])
            if stat['pominiete_uzytki']:
                w.append('  Klasoużytki pominięte (kod spoza słownika):')
                w.extend('    %-10s %d' % x
                         for x in stat['pominiete_uzytki'].most_common())
            if stat['nieznane_klasy']:
                w.append('  Klasy gleby spoza F_SOIL_QUALITY_DIC (zapisane '
                         'bez klasy):')
                w.extend('    %-10s %d' % x
                         for x in stat['nieznane_klasy'].most_common())
        w.append('')

    sc = os.path.join(katalog_raportow(folder_startowy),
                      'raport_utworz_baze_z_gml_' + czas + '.txt')
    with open(sc, 'w', encoding='utf-8') as plik:
        plik.write('\n'.join(w) + '\n')
    return sc
