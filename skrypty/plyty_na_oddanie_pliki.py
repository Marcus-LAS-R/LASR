# -*- coding: utf-8 -*-
"""Utwórz płyty na oddanie - część bez QGIS-a (testowalna:
testy/test_plyty_na_oddanie.py): części (gmina folderu), plan płyt, nazwy,
wyszukiwanie plików, kopiowanie i opis.

Wynik w <oddanie>/_Plyty_na_oddanie/ (bez pakowania):
    Calosciowa/  [SULMN] + <część>/{Bazy_danych, SHP, Operaty, Operaty_BDO,
                 Mapy, Atlasy, Raporty}
    Gm.<Nazwa>/  to samo dla jednej gminy (TERYT - miasto i obszar wiejski
                 razem)
    PGLLP/       [SULMN] + <część>/{Operaty_BDO, Mapy, Atlasy}
Co trafia na płytę - osobna lista dla każdego rodzaju płyty (ZAWARTOSC,
domyślne DOMYSLNE_PLYT); podfoldery części tylko z zaznaczonych pozycji.
Część = jedna gmina (MUNICIP) folderu gminy, nazwa <TERYT6>_<typ>_<Nazwa>
[_M/_MW/_OW] - tak też nazywane są bazy (<część>.mdb, <część>_anonim.mdb).

Bazy (kopie bez kwerend, zwykła i zanonimizowana) i połączone warstwy SHP
przygotowuje raz (dla sumy zaznaczeń wszystkich płyt) część QGIS-owa
(plyty_na_oddanie.py) w folderze przygotowania - każda płyta bierze z niego
tylko to, co ma zaznaczone.
"""
import os
import re
import shutil

try:
    from . import przygotuj_na_wylozenia_pliki as pw
    from . import spakuj_do_opiniowania_pliki as sp
    from . import podziel_obiekt_pliki as po
    from . import tpu_raporty_pliki as tp
except ImportError:  # testy - moduł ładowany bez pakietu
    import przygotuj_na_wylozenia_pliki as pw
    import spakuj_do_opiniowania_pliki as sp
    import podziel_obiekt_pliki as po
    import tpu_raporty_pliki as tp

FOLDER_WYNIKOWY = '_Plyty_na_oddanie'
FOLDER_PRZYGOTOWANIA = '.przygotowanie' + pw.TMP
TMP = pw.TMP
LIMIT_DVD = 4700 * 1000 * 1000  # 4,7 GB (pojemność płyty DVD)

CALOSC = 'calosc'
GMINY = 'gminy'
PGLLP = 'pgllp'
PLYTY = (CALOSC, GMINY, PGLLP)
ETYKIETY_PLYT = {CALOSC: 'Całościowa', GMINY: 'Dla gmin',
                 PGLLP: 'Dla PGLLP'}
NAZWA_CALOSC = 'Calosciowa'
NAZWA_PGLLP = 'PGLLP'
PRZEDROSTEK_GMINY = 'Gm.'

BAZY = 'Bazy_danych'
SHP = 'SHP'
OPERATY = 'Operaty'
OPERATY_BDO = 'Operaty_BDO'
MAPY = 'Mapy'
ATLASY = 'Atlasy'
RAPORTY = 'Raporty'
OGOLNE = 'OGOLNE'
PODFOLDERY = (BAZY, SHP, OPERATY, OPERATY_BDO, MAPY, ATLASY, RAPORTY)
PRZYROSTEK_ANONIM = '_anonim'
# warstwy robocze, których nie dajemy na płyty (nazwa bez rozszerzenia)
POMIJANE_WARSTWY = frozenset({'MAPRAM'})

# lista "co wgrać na płytę": (klucz, etykieta)
ZAWARTOSC = (
    ('sulmn', 'Plik SULMN'),
    ('bazy', 'Bazy danych - zwykłe (bez kwerend)'),
    ('anonim', 'Bazy danych - zanonimizowane (bez kwerend)'),
    ('shp', 'Warstwy SHP połączone z obrębów (_MAPY)'),
    ('ogolne', 'Pliki ogólne SHP (_MAPY/<gmina>/OGOLNE)'),
    ('operaty', 'Operaty (PDF)'),
    ('operaty_bdo', 'Operaty BDO (PDF)'),
    ('docx', 'Operaty w wersji edytowalnej (docx)'),
    ('mapy', 'Mapy'),
    ('atlasy', 'Atlasy z legendami'),
    ('raporty', 'Raporty TPU (bez danych osobowych)'),
)
KLUCZE = tuple(k for k, _ in ZAWARTOSC)
_PELNE = {k: k not in ('sulmn', 'raporty', 'docx', 'ogolne')
          for k in KLUCZE}
DOMYSLNE_PLYT = {
    CALOSC: dict(_PELNE),
    GMINY: dict(_PELNE),
    PGLLP: {k: k in ('operaty_bdo', 'mapy', 'atlasy') for k in KLUCZE},
}
# podfolder części -> opcje, z których powstaje
_OPCJE_PODFOLDERU = {
    BAZY: ('bazy', 'anonim'), SHP: ('shp', 'ogolne'),
    OPERATY: ('operaty',), OPERATY_BDO: ('operaty_bdo',),
    MAPY: ('mapy',), ATLASY: ('atlasy',), RAPORTY: ('raporty',),
}
# rodzaje plików części -> (podfolder, opcje wymagane razem)
_PLIKI = (
    ('operaty', OPERATY, ('operaty',)),
    ('operaty_docx', OPERATY, ('operaty', 'docx')),
    ('operaty_bdo', OPERATY_BDO, ('operaty_bdo',)),
    ('operaty_bdo_docx', OPERATY_BDO, ('operaty_bdo', 'docx')),
    ('mapy', MAPY, ('mapy',)),
    ('atlasy', ATLASY, ('atlasy',)),
)


class Przerwano(Exception):
    """Użytkownik przerwał."""


def suma_opcji(*opcje):
    """Opcja zaznaczona choć na jednej liście (do wyszukiwania plików
    i przygotowania baz/SHP)."""
    return {k: any(o.get(k) for o in opcje) for k in KLUCZE}


# ------------------------------------------------------------------ nazwy

def nazwa_czesci(teryt6, municip, nazwa_gminy, zapasowa=''):
    """'301703', '035', 'Odolanow' -> '301703_5_Odolanow_OW'; bez TERYT -
    nazwa zapasowa (folder gminy) bez znaków spoza [A-Za-z0-9_-]."""
    if teryt6 and len(teryt6) == 6 and municip and len(municip) == 3:
        return po.folder_jednostki(teryt6 + municip[2], nazwa_gminy)
    tekst = sp.bez_polskich(zapasowa or nazwa_gminy or 'GMINA')
    return re.sub(r'[^A-Za-z0-9-]+', '_', tekst).strip('_') or 'GMINA'


def nazwy_plyt_gmin(gminy):
    """{klucz: 'Gm.<Nazwa>'}; powtórzona nazwa dostaje _<klucz>."""
    wyn = {}
    nazwy = [g or 'GMINA' for g in gminy.values()]
    for k, n in gminy.items():
        n = n or 'GMINA'
        wyn[k] = PRZEDROSTEK_GMINY + (
            n if nazwy.count(n) == 1 else f'{n}_{sp.nazwa_pliku(str(k))}')
    return wyn


# ------------------------------------------------------------ wyszukiwanie

def bazy_folderu(folder):
    """Bazy .mdb wprost w folderze gminy (bez podfolderów i bez *_BDO.mdb),
    od najnowszej."""
    try:
        nazwy = os.listdir(folder)
    except OSError:
        return []
    wyn = [os.path.join(folder, n) for n in nazwy
           if n.lower().endswith('.mdb') and
           not n.lower().endswith('_bdo.mdb') and
           os.path.isfile(os.path.join(folder, n))]
    return sorted(wyn, key=sp._mtime, reverse=True)


def _pliki_wzoru(katalog, wzor):
    try:
        return sorted(os.path.join(katalog, p) for p in os.listdir(katalog)
                      if wzor.match(p) and
                      os.path.isfile(os.path.join(katalog, p)))
    except OSError:
        return []


def docx_obrebu(folder, municip, community):
    """(zwykłe, BDO) - edytowalne operaty obrębu: Operaty/<woj>-<MUNICIP>-
    <COMMUNITY>-*.docx oraz *_BDO.docx z obu lokalizacji BDO (nowszy przy
    tej samej nazwie). Pliki tymczasowe Worda (~$...) nie pasują do wzoru."""
    rdzen = r'^\d+-%s-%s(-.*)?' % (re.escape(municip), re.escape(community))
    zwykle = [p for p in _pliki_wzoru(
        os.path.join(folder, sp.FOLDER_OPERATOW_ZWYKLYCH),
        re.compile(rdzen + r'\.docx$', re.IGNORECASE))
        if not p.lower().endswith('_bdo.docx')]
    bdo = {}
    for podf in sp.FOLDERY_BDO:
        for p in _pliki_wzoru(os.path.join(folder, podf), re.compile(
                rdzen + r'_BDO\.docx$', re.IGNORECASE)):
            bdo.setdefault(os.path.basename(p), []).append(p)
    return zwykle, [max(lst, key=sp._mtime) for _, lst in sorted(bdo.items())]


def foldery_shp_czesci(folder, municip, obreby):
    """{community: folder SHP} - pierwszy projekt mapy obrębu
    (_MAPY/<MUNICIP>_*/<COMMUNITY>_*/SHP, rezerwowo _ROBOCZE)."""
    wyn = {}
    for ob in obreby:
        kat = sp._foldery_shp_obrebu(folder, municip, ob['community'])
        if kat:
            wyn[ob['community']] = kat[0]
    return wyn


def zrodla_shp(foldery_shp):
    """{NAZWA warstwy: [(community, ścieżka .shp)]} - wejście do Połącz
    warstwy (kolejność obrębów)."""
    wyn = {}
    for com, kat in sorted(foldery_shp.items()):
        try:
            pliki = sorted(os.listdir(kat))
        except OSError:
            continue
        for p in pliki:
            nazwa, rozsz = os.path.splitext(p)
            if (rozsz.lower() == '.shp'
                    and nazwa.upper() not in POMIJANE_WARSTWY):
                wyn.setdefault(nazwa.upper(), []).append(
                    (com, os.path.join(kat, p)))
    return wyn


def _warstwa(plik):
    """Nazwa warstwy z nazwy pliku (MapRam.shp.xml -> MAPRAM)."""
    return plik.split('.', 1)[0].upper()


def pliki_ogolne(folder, municip):
    """Pliki z _MAPY/<MUNICIP>_*/OGOLNE (warstwy wspólne gminy), a gdy
    tam nic nie ma - z _MAPY/_ROBOCZE/<MUNICIP>_*/OGOLNE."""
    mapy = os.path.join(folder, sp.FOLDER_MAP)
    for baza in (mapy, os.path.join(mapy, sp.FOLDER_ROBOCZY)):
        wyn = []
        for gm in sp._podfoldery(baza, f'{municip}_'):
            kat = os.path.join(gm, OGOLNE)
            try:
                wyn += [os.path.join(kat, p) for p in sorted(os.listdir(kat))
                        if os.path.isfile(os.path.join(kat, p))
                        and _warstwa(p) not in POMIJANE_WARSTWY]
            except OSError:
                pass
        if wyn:
            return wyn
    return []


def _katalogi_mapy_plotowania(folder, municip=None):
    """_MAPY/PLOTOWANIE i jego foldery gmin (<MUNICIP>_*, bez _x2)."""
    plot = os.path.join(folder, sp.FOLDER_MAP, sp.FOLDER_PLOTOWANIA)
    if not os.path.isdir(plot):
        return []
    return [plot] + [d for d in sp._podfoldery(
        plot, f'{municip}_' if municip else None)
        if not d.lower().endswith('_x2')]


def _pdfy_mapy_plotowania(folder, municip=None):
    """[(ścieżka, nazwa, rodzaj)] PDF-ów z _MAPY/PLOTOWANIE: luzem i w
    folderach gmin, także w ich podfolderach Mapy/Atlasy (bez _x2)."""
    wyn = []
    for baza in _katalogi_mapy_plotowania(folder, municip):
        for podf, rodzaj in ((None, None), ('Mapy', sp.MAPY),
                             ('Atlasy', sp.ATLASY)):
            kat = baza if podf is None else os.path.join(baza, podf)
            for p in sp._pdfy(kat):
                wyn.append((os.path.join(kat, p), p,
                            rodzaj or sp.rodzaj_z_nazwy(p)))
    return wyn


def mapy_z_mapy_plotowania(folder, municip, communities):
    """Mapy/atlasy z _MAPY/PLOTOWANIE (luzem albo w folderze gminy):
    ({community: {MAPY: [...], ATLASY: [...]}} - pliki obrębów
    (<COMMUNITY>_*.pdf), {MAPY: [...], ATLASY: [...]} - pliki całej gminy
    (<MUNICIP>_*.pdf, np. 042_JAROSLAW_ATLAS.pdf, 042_JAROSLAW_LEG.pdf))."""
    obreby = {c: {sp.MAPY: [], sp.ATLASY: []} for c in communities}
    gmina = {sp.MAPY: [], sp.ATLASY: []}
    for sc, p, rodzaj in _pdfy_mapy_plotowania(folder, municip):
        przedrostek = p.split('_', 1)[0]
        if przedrostek in obreby:
            obreby[przedrostek][rodzaj].append(sc)
        elif przedrostek == municip:
            gmina[rodzaj].append(sc)
    return obreby, gmina


def dostepne_mapy(foldery):
    """Czy są mapy/atlasy (pw.MAPY/pw.ATLASY) - PLOTOWANIE folderu gminy
    i _MAPY/PLOTOWANIE."""
    wyn = {r for r in pw.dostepne_rodzaje(foldery)
           if r in (pw.MAPY, pw.ATLASY)}
    for folder in foldery:
        wyn.update(r for _, _, r in _pdfy_mapy_plotowania(folder))
    return wyn


# ------------------------------------------------------------------ części

def czesci_z_gmin(gminy):
    """gminy z przygotuj_na_wylozenia.obreby_folderu ({klucz: {nazwa,
    obreby}}) -> lista części [{klucz_gminy, nazwa_gminy, folder, municip,
    teryt, nazwa, obreby}] - jedna na (folder gminy, MUNICIP)."""
    czesci = {}
    for klucz, g in gminy.items():
        teryt = klucz if isinstance(klucz, str) else ''
        for ob in g['obreby']:
            k = (ob['folder'], ob['municip'])
            if k not in czesci:
                czesci[k] = {
                    'klucz_gminy': klucz, 'nazwa_gminy': g['nazwa'],
                    'folder': ob['folder'], 'municip': ob['municip'],
                    'teryt': teryt,
                    'nazwa': nazwa_czesci(teryt, ob['municip'], g['nazwa'],
                                          ob['nazwa_folderu']),
                    'obreby': []}
            czesci[k]['obreby'].append(ob)
    wyn = sorted(czesci.values(), key=lambda c: c['nazwa'].lower())
    uzyte = {}
    for c in wyn:  # dwie części o tej samej nazwie (np. dwa foldery)
        n = uzyte.get(c['nazwa'], 0)
        uzyte[c['nazwa']] = n + 1
        if n:
            c['nazwa'] = f"{c['nazwa']}_{n + 1}"
    for c in wyn:
        c['obreby'].sort(key=lambda o: o['community'])
    return wyn


def _bez_dubli(lista):
    widziane, wyn = set(), []
    for p in lista:
        if os.path.normcase(p) not in widziane:
            widziane.add(os.path.normcase(p))
            wyn.append(p)
    return wyn


def _bez_dubli_nazw(lista):
    widziane, wyn = set(), []
    for p in lista:
        n = os.path.basename(p).lower()
        if n not in widziane:
            widziane.add(n)
            wyn.append(p)
    return wyn


def uzupelnij_czesc(cz, opcje):
    """Pliki części dla opcji (suma list wszystkich płyt): baza, pliki
    {rodzaj z _PLIKI: [źródła]}, źródła SHP, pliki OGOLNE, braki."""
    bazy = bazy_folderu(cz['folder'])
    cz['baza'] = bazy[0] if bazy else None
    cz['bazy_inne'] = bazy[1:]
    pliki = {r: [] for r, _, _ in _PLIKI}
    braki = []
    dod_obreby, dod_gmina = mapy_z_mapy_plotowania(
        cz['folder'], cz['municip'], [o['community'] for o in cz['obreby']])
    # atlas/legenda całej gminy (<MUNICIP>_*_ATLAS/LEG.pdf) - raz na część
    for klucz, rodzaj in (('mapy', sp.MAPY), ('atlasy', sp.ATLASY)):
        if opcje.get(klucz):
            pliki[klucz] += dod_gmina[rodzaj]
    for ob in cz['obreby']:
        p = pw.pliki_obrebu(ob['folder'], ob['municip'], ob['community'])
        p[pw.MAPY] = p[pw.MAPY] + dod_obreby[ob['community']][sp.MAPY]
        p[pw.ATLASY] = p[pw.ATLASY] + dod_obreby[ob['community']][sp.ATLASY]
        for klucz, rodzaj in (('operaty', pw.OPERATY),
                              ('operaty_bdo', pw.OPERATY_BDO),
                              ('mapy', pw.MAPY), ('atlasy', pw.ATLASY)):
            if opcje.get(klucz):
                pliki[klucz] += p[rodzaj]
        if opcje.get('docx'):
            zw, bdo = docx_obrebu(ob['folder'], ob['municip'],
                                  ob['community'])
            pliki['operaty_docx'] += zw
            pliki['operaty_bdo_docx'] += bdo
        atl = [os.path.basename(s).upper()
               for s in p[pw.ATLASY] + dod_gmina[sp.ATLASY]]
        brak = [n for n, klucz, jest in (
            ('operat', 'operaty', p[pw.OPERATY]),
            ('operat BDO', 'operaty_bdo', p[pw.OPERATY_BDO]),
            ('mapa', 'mapy', p[pw.MAPY] + dod_gmina[sp.MAPY]),
            ('atlas', 'atlasy', any('ATLAS' in n for n in atl)),
            ('legenda', 'atlasy', any('_LEG' in n for n in atl)))
            if opcje.get(klucz) and not jest]
        if brak:
            braki.append(f"{ob['municip']}.{ob['community']} "
                         f"{ob.get('nazwa_obrebu') or ''}".rstrip() +
                         ': ' + ', '.join(brak))
    cz['pliki'] = {k: _bez_dubli(v) for k, v in pliki.items()}
    for k in ('mapy', 'atlasy'):
        # ten sam plik w PLOTOWANIE i _MAPY/PLOTOWANIE - raz (pierwszy)
        cz['pliki'][k] = _bez_dubli_nazw(cz['pliki'][k])
    cz['foldery_shp'] = (foldery_shp_czesci(cz['folder'], cz['municip'],
                                            cz['obreby'])
                         if opcje.get('shp') else {})
    cz['shp'] = zrodla_shp(cz['foldery_shp'])
    bez_shp = [ob['community'] for ob in cz['obreby']
               if ob['community'] not in cz['foldery_shp']]
    if opcje.get('shp') and bez_shp:
        braki.append('brak SHP mapy obrębu (_MAPY): ' + ', '.join(bez_shp))
    cz['ogolne'] = (pliki_ogolne(cz['folder'], cz['municip'])
                    if opcje.get('ogolne') else [])
    # raporty TPU z <folder gminy>/Raporty_TPU - bez danych osobowych
    cz['raporty'] = (tp.raporty_na_plyte(
        cz['folder'], cz['municip'], [o['community'] for o in cz['obreby']])
        if opcje.get('raporty') else [])
    if opcje.get('raporty') and not cz['raporty']:
        braki.append(f'brak raportów TPU ({tp.FOLDER_RAPORTOW} obok bazy - '
                     'Generuj › Zestawienia raportów TPU)')
    if cz['baza'] is None and (opcje.get('bazy') or opcje.get('anonim')):
        braki.insert(0, 'BRAK BAZY .mdb w folderze gminy')
    cz['braki'] = braki
    return cz


# ------------------------------------------------------------------- plan

def podfoldery_plyty(opcje):
    """Podfoldery części na płycie - tylko z zaznaczonych pozycji."""
    return tuple(p for p in PODFOLDERY
                 if any(opcje.get(k) for k in _OPCJE_PODFOLDERU[p]))


def zaplanuj(czesci, plyty, sulmn=None, opcje_plyt=None):
    """Płyty [{rodzaj, nazwa, czesci, opcje, sulmn}] w kolejności PLYTY
    (płyty gmin wg nazwy). opcje_plyt: {rodzaj: {klucz: bool}} - lista
    płyty (brak - DOMYSLNE_PLYT); sulmn - ścieżka, na płytę trafia, gdy ma
    zaznaczony SULMN."""
    opcje_plyt = opcje_plyt or {}

    def _plyta(rodzaj, nazwa, cz):
        o = opcje_plyt.get(rodzaj) or DOMYSLNE_PLYT[rodzaj]
        return {'rodzaj': rodzaj, 'nazwa': nazwa, 'czesci': cz, 'opcje': o,
                'sulmn': sulmn if o.get('sulmn') else None}

    wyn = []
    if CALOSC in plyty:
        wyn.append(_plyta(CALOSC, NAZWA_CALOSC, list(czesci)))
    if GMINY in plyty:
        gminy = {}
        for c in czesci:
            gminy.setdefault(c['klucz_gminy'], []).append(c)
        nazwy = nazwy_plyt_gmin({k: cz[0]['nazwa_gminy']
                                 for k, cz in gminy.items()})
        for k in sorted(gminy, key=lambda k: nazwy[k].lower()):
            wyn.append(_plyta(GMINY, nazwy[k], gminy[k]))
    if PGLLP in plyty:
        wyn.append(_plyta(PGLLP, NAZWA_PGLLP, list(czesci)))
    return wyn


def potrzebne_przygotowanie(plan):
    """Czy któraś płyta ma bazy/SHP (przygotowywane raz)."""
    return any(p['opcje'].get(k) for p in plan
               for k in ('bazy', 'anonim', 'shp', 'ogolne'))


def pliki_czesci(plyta, c):
    """[(źródło, ścieżka względna w części)] - pliki z folderów obiektu."""
    o = plyta['opcje']
    wyn = []
    for rodzaj, podf, wymagane in _PLIKI:
        if all(o.get(k) for k in wymagane):
            wyn += [(s, os.path.join(podf, os.path.basename(s)))
                    for s in c['pliki'].get(rodzaj, [])]
    return wyn


def raporty_czesci(plyta, c):
    """[(źródło, ścieżka względna w części, arkusze do wycięcia)] -
    raporty TPU (Raporty/<folder raportu>/...), gdy płyta je ma."""
    if not plyta['opcje'].get('raporty'):
        return []
    return [(s, os.path.join(RAPORTY, wzgl), ark)
            for s, wzgl, ark in c.get('raporty', [])]


def przygotowane_czesci(plyta, c, przygotowanie):
    """[(źródło, ścieżka względna w części)] z folderu przygotowania:
    bazy wybranych wersji, połączone SHP, OGOLNE."""
    o = plyta['opcje']
    wyn = []
    kat = os.path.join(przygotowanie or '', c['nazwa'], BAZY)
    for p in _lista(kat):
        anonim = os.path.splitext(p)[0].endswith(PRZYROSTEK_ANONIM)
        if o.get('anonim' if anonim else 'bazy'):
            wyn.append((os.path.join(kat, p), os.path.join(BAZY, p)))
    kat = os.path.join(przygotowanie or '', c['nazwa'], SHP)
    if o.get('shp'):
        wyn += [(os.path.join(kat, p), os.path.join(SHP, p))
                for p in _lista(kat)]
    if o.get('ogolne'):
        wyn += [(os.path.join(kat, OGOLNE, p), os.path.join(SHP, OGOLNE, p))
                for p in _lista(os.path.join(kat, OGOLNE))]
    return wyn


def _lista(kat):
    try:
        return sorted(p for p in os.listdir(kat)
                      if os.path.isfile(os.path.join(kat, p)))
    except OSError:
        return []


def _rozmiar_katalogu(kat):
    razem = 0
    for kor, _, pliki in os.walk(kat):
        razem += sum(sp._rozmiar(os.path.join(kor, p)) for p in pliki)
    return razem


def szacuj_rozmiar(plyta):
    """Szacunek przed przygotowaniem: bazy x liczba wersji, SHP - suma
    warstw źródłowych (po połączeniu mniej), pliki, SULMN."""
    o = plyta['opcje']
    razem = sp._rozmiar(plyta['sulmn']) if plyta['sulmn'] else 0
    wersje = int(bool(o.get('bazy'))) + int(bool(o.get('anonim')))
    for c in plyta['czesci']:
        if c.get('baza'):
            razem += wersje * sp._rozmiar(c['baza'])
        if o.get('shp'):
            for zrodla in c['shp'].values():
                for _, sc in zrodla:
                    razem += sum(sp._rozmiar(os.path.splitext(sc)[0] + r)
                                 for r in ('.shp', '.dbf', '.shx'))
        if o.get('ogolne'):
            razem += sum(sp._rozmiar(p) for p in c['ogolne'])
        razem += sum(sp._rozmiar(s) for s, _ in pliki_czesci(plyta, c))
        razem += sum(sp._rozmiar(s) for s, _, _ in raporty_czesci(plyta, c))
    return razem


def rozmiar_czesci(plyta, c, przygotowanie=None):
    """Rozmiar części na płycie: przygotowane bazy/SHP (faktyczny) +
    pliki."""
    return (sum(sp._rozmiar(s) for s, _ in
                przygotowane_czesci(plyta, c, przygotowanie) +
                pliki_czesci(plyta, c)) +
            sum(sp._rozmiar(s) for s, _, _ in raporty_czesci(plyta, c)))


def rozmiar_plyty(plyta, przygotowanie=None):
    return ((sp._rozmiar(plyta['sulmn']) if plyta['sulmn'] else 0) +
            sum(rozmiar_czesci(plyta, c, przygotowanie)
                for c in plyta['czesci']))


def za_duze(plan, przygotowanie=None, limit=LIMIT_DVD):
    """{nazwa płyty: rozmiar} płyt większych niż limit."""
    wyn = {}
    for p in plan:
        r = rozmiar_plyty(p, przygotowanie)
        if r > limit:
            wyn[p['nazwa']] = r
    return wyn


def podziel_plyty(plan, przygotowanie=None, limit=LIMIT_DVD):
    """Płyty większe niż limit dzielone po gminach (częściach) na
    <nazwa>_1, _2... (SULMN na każdej). Gmina większa niż limit - sama na
    płycie (gminy się nie dzieli)."""
    wyn = []
    for p in plan:
        if rozmiar_plyty(p, przygotowanie) <= limit:
            wyn.append(p)
            continue
        sulmn = sp._rozmiar(p['sulmn']) if p['sulmn'] else 0
        grupy = sp.podziel_na_czesci(
            [(c, rozmiar_czesci(p, c, przygotowanie)) for c in p['czesci']],
            limit - sulmn)
        for i, g in enumerate(grupy, 1):
            wyn.append(dict(p, nazwa=f"{p['nazwa']}_{i}", czesci=g))
    return wyn


def istniejace_wyniki(docelowy, plan):
    """Płyty, które ten przebieg zastąpi: <nazwa> i <nazwa>_<n> (także
    części podzielonej płyty z poprzedniego przebiegu)."""
    try:
        nazwy = os.listdir(docelowy)
    except OSError:
        return []
    wzory = [re.compile(r'^%s(_\d+)?$' % re.escape(p['nazwa']),
                        re.IGNORECASE) for p in plan]
    return sorted(n for n in nazwy
                  if os.path.isdir(os.path.join(docelowy, n)) and
                  any(w.match(n) for w in wzory))


# ------------------------------------------------------------- kopiowanie

def _kopiuj(zrodlo, cel, bledy, postep):
    os.makedirs(os.path.dirname(cel), exist_ok=True)
    try:
        shutil.copy2(zrodlo, cel)
    except OSError as e:
        bledy.append(f'{zrodlo}: {e}')
    if postep and postep(sp._rozmiar(zrodlo)) is False:
        raise Przerwano()


def kopiuj_plyte(docelowy, plyta, przygotowanie=None, postep=None):
    """Kopiuje płytę do <docelowy>/<nazwa>.tmp. przygotowanie: folder
    z <część>/{Bazy_danych, SHP} (przygotowane raz dla wszystkich płyt).
    postep(bajty) -> False przerywa (Przerwano, .tmp usunięty). Zwraca listę
    błędów."""
    tmp = os.path.join(docelowy, plyta['nazwa'] + TMP)
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    bledy = []
    try:
        if plyta['sulmn']:
            _kopiuj(plyta['sulmn'], os.path.join(
                tmp, os.path.basename(plyta['sulmn'])), bledy, postep)
        for c in plyta['czesci']:
            kat = os.path.join(tmp, c['nazwa'])
            os.makedirs(kat, exist_ok=True)
            for s, wzgl in (przygotowane_czesci(plyta, c, przygotowanie) +
                            pliki_czesci(plyta, c)):
                _kopiuj(s, os.path.join(kat, wzgl), bledy, postep)
            for s, wzgl, arkusze in raporty_czesci(plyta, c):
                # zestawienie bez arkuszy z danymi osobowymi
                try:
                    tp.kopiuj_bez_arkuszy(s, os.path.join(kat, wzgl),
                                          arkusze)
                except Exception as e:
                    bledy.append(f'{s}: {e}')
                if postep and postep(sp._rozmiar(s)) is False:
                    raise Przerwano()
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return bledy


def podmien(docelowy, plan, istniejace):
    """Usuwa stare płyty (istniejace) i zmienia <nazwa>.tmp -> <nazwa>."""
    bledy = []
    for nazwa in istniejace:
        try:
            shutil.rmtree(os.path.join(docelowy, nazwa))
        except OSError as e:
            bledy.append(f'Nie usunięto starej płyty {nazwa}: {e}')
    for p in plan:
        tmp = os.path.join(docelowy, p['nazwa'] + TMP)
        try:
            os.replace(tmp, os.path.join(docelowy, p['nazwa']))
        except OSError as e:
            bledy.append(f"{p['nazwa']}: {e} - pliki zostały w "
                         f"{p['nazwa']}{TMP}")
    return bledy


def usun_tymczasowe(docelowy, plan):
    for p in plan:
        shutil.rmtree(os.path.join(docelowy, p['nazwa'] + TMP),
                      ignore_errors=True)
    shutil.rmtree(os.path.join(docelowy, FOLDER_PRZYGOTOWANIA),
                  ignore_errors=True)


def rozmiary_plyt(docelowy, plan):
    return {p['nazwa']: _rozmiar_katalogu(os.path.join(docelowy, p['nazwa']))
            for p in plan}


# ----------------------------------------------------------------- opisy

def gb(bajty):
    return f'{bajty / 1e9:.2f} GB'.replace('.', ',')


def opis_planu(plan, czesci, uwagi=(), rozmiary=None, limit=LIMIT_DVD):
    """rozmiary: {płyta: bajty} faktyczne (po utworzeniu); bez - szacunek.
    limit None - brak limitu (bez ostrzeżeń)."""
    L = [f'Wielkość nośnika: mniej niż {gb(limit)} (DVD)' if limit
         else 'Wielkość nośnika: brak limitu', '']
    for p in plan:
        rozm = (rozmiary or {}).get(p['nazwa'])
        szac = rozm is None
        if szac:
            rozm = szacuj_rozmiar(p)
        L.append(f"{p['nazwa']} ({ETYKIETY_PLYT[p['rodzaj']]}) - "
                 f"{len(p['czesci'])} gmin, {'ok. ' if szac else ''}"
                 f"{gb(rozm)}")
        if limit and rozm > limit:
            L.append(f'  UWAGA: płyta większa niż {gb(limit)} - nie '
                     'zmieści się na DVD' + (
                         ' (szacunek - dokładny rozmiar po przygotowaniu '
                         'baz i SHP)' if szac else ''))
        L.append('  wgrywane: ' + (', '.join(
            e for k, e in ZAWARTOSC if p['opcje'].get(k)) or '-'))
        if p['sulmn']:
            L.append(f"  SULMN: {os.path.basename(p['sulmn'])}")
        for c in p['czesci']:
            L.append(f"  {c['nazwa']} - {len(c['obreby'])} obr.")
        L.append('')
    L.append('GMINY')
    for c in czesci:
        L.append(f"  {c['nazwa']} ({os.path.basename(c['folder'])}, "
                 f"MUNICIP {c['municip']}):")
        L.append('    baza: ' + (os.path.basename(c['baza']) if c['baza']
                                 else 'BRAK'))
        if c['bazy_inne']:
            L.append('    UWAGA: w folderze są też starsze bazy: ' +
                     ', '.join(os.path.basename(b) for b in c['bazy_inne']))
        L.append(f"    SHP: {len(c['shp'])} warstw z "
                 f"{len(c['foldery_shp'])} obrębów" +
                 (f", OGOLNE: {len(c['ogolne'])} plików" if c['ogolne']
                  else ''))
        L.append('    pliki: ' + ', '.join(
            f'{k} {len(v)}' for k, v in c['pliki'].items() if v))
        if c.get('raporty'):
            L.append(f"    raporty TPU: {len(c['raporty'])} plików (bez "
                     'raportów z danymi osobowymi; Zestawienie raportów '
                     'bez arkuszy ' + ', '.join(tp.ARKUSZE_OSOBOWE) + ')')
        for b in c['braki']:
            L.append(f'    BRAK: {b}')
    if uwagi:
        L += ['', 'UWAGI']
        L += [f'  {u}' for u in uwagi]
    return '\n'.join(L) + '\n'
