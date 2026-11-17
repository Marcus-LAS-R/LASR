# -*- coding: utf-8 -*-
"""Przygotuj na wyłożenia - część bez QGIS-a (testowalna:
testy/test_przygotuj_na_wylozenia.py): pliki obrębu, nazwy folderów gmin,
podział na części, kopiowanie, raport.

Wynik (bez pakowania), jeden folder na gminę (TERYT - miasto i obszar
wiejski gminy miejsko-wiejskiej razem):
    <docelowy>/pUPUL_<Nazwa_gminy>/Mapy/      mapy obrębów
                                  /Atlasy/    atlasy z legendami
                                  /Operaty/   operaty (zwykłe .pdf)
                                  /Operaty_BDO/ operaty *_BDO.pdf
Folder gminy ma mniej niż LIMIT (490 MB); większa gmina dostaje
pUPUL_<Nazwa>_1, _2... - obręb nigdy nie jest rozdzielany.

Źródła plików w folderze gminy/obrębu - jak w Spakuj do opiniowania
(spakuj_do_opiniowania_pliki.py), do tego zwykły operat z
Operaty/<woj>-<MUNICIP>-<COMMUNITY>-<nazwa>.pdf.
"""
import os
import re
import shutil

try:
    from . import spakuj_do_opiniowania_pliki as sp
except ImportError:  # testy - moduł ładowany bez pakietu
    import spakuj_do_opiniowania_pliki as sp

FOLDER_WYNIKOWY = '_Na_wylozenia'
PRZEDROSTEK = 'pUPUL_'
LIMIT = 490 * 1024 * 1024
TMP = '.tmp'

MAPY = sp.MAPY
ATLASY = sp.ATLASY
OPERATY = 'Operaty'
OPERATY_BDO = sp.OPERATY
RODZAJE = (MAPY, ATLASY, OPERATY, OPERATY_BDO)
PODFOLDERY = {MAPY: 'Mapy', ATLASY: 'Atlasy', OPERATY: 'Operaty',
              OPERATY_BDO: 'Operaty_BDO'}
ETYKIETY = {MAPY: 'Mapy', ATLASY: 'Atlasy z legendami',
            OPERATY: 'Operaty', OPERATY_BDO: 'Operaty BDO'}

_PRZEDROSTKI_GMIN = re.compile(
    r'^(miasto\s+i\s+gmina|gmina\s+miejsko-wiejska|gmina\s+miejska|'
    r'gmina\s+wiejska|gmina|miasto)\s+', re.IGNORECASE)


class Przerwano(Exception):
    """Użytkownik przerwał kopiowanie."""


# ------------------------------------------------------------------ nazwy

def nazwa_gminy(tekst):
    """'Gmina Ostrów Wielkopolski' -> 'Ostrow_Wielkopolski',
    'Miasto Odolanów' -> 'Odolanow'."""
    tekst = _PRZEDROSTKI_GMIN.sub('', str(tekst or '').strip())
    tekst = sp.bez_polskich(tekst)
    return re.sub(r'[^A-Za-z0-9-]+', '_', tekst).strip('_')


def nazwa_z_folderu(nazwa_folderu):
    """Gdy GMIN.shp nie ma nazwy: '301703_5_Odolanow_OW' -> 'Odolanow'."""
    n = re.sub(r'^\d{6}_\d_', '', nazwa_folderu)
    n = re.sub(r'_(M|OW|W|G|MW)$', '', n, flags=re.IGNORECASE)
    return nazwa_gminy(n)


def teryt_z_folderu(nazwa_folderu, municip):
    """'301703_5_Odolanow_OW', '035' -> '301703'; None, gdy nazwa folderu
    nie zaczyna się od TERYT tej gminy."""
    m = re.match(r'^(\d{4})(\d{2})_(\d)', nazwa_folderu)
    if m and m.group(2) + m.group(3) == municip:
        return m.group(1) + m.group(2)
    return None


def nazwy_folderow(gminy):
    """{klucz: 'pUPUL_<Nazwa>'} dla {klucz: nazwa}; powtórzona nazwa
    dostaje _<klucz> (np. dwie gminy o tej samej nazwie w obiekcie)."""
    wyn = {}
    nazwy = [n or 'GMINA' for n in gminy.values()]
    for k, n in gminy.items():
        n = n or 'GMINA'
        wyn[k] = PRZEDROSTEK + (n if nazwy.count(n) == 1
                                else f'{n}_{sp.nazwa_pliku(str(k))}')
    return wyn


# ---------------------------------------------------------- pliki obrębu

def operaty_zwykle(folder, municip, community):
    """Operaty/<woj>-<MUNICIP>-<COMMUNITY>-<nazwa>.pdf (bez _BDO)."""
    kat = os.path.join(folder, sp.FOLDER_OPERATOW_ZWYKLYCH)
    wzor = re.compile(r'^\d+-%s-%s(-.*)?\.pdf$' % (
        re.escape(municip), re.escape(community)), re.IGNORECASE)
    return [os.path.join(kat, p) for p in sp._pdfy(kat)
            if wzor.match(p) and not p.lower().endswith('_bdo.pdf')]


def pliki_obrebu(folder, municip, community):
    """{rodzaj: [ścieżki]} dla RODZAJE."""
    p = sp.pliki_obrebu(folder, municip, community)
    return {MAPY: p[sp.MAPY], ATLASY: p[sp.ATLASY],
            OPERATY: operaty_zwykle(folder, municip, community),
            OPERATY_BDO: p[sp.OPERATY]}


def dostepne_rodzaje(foldery):
    wyn = set()
    dost = sp.dostepne_rodzaje(foldery)
    for r in (MAPY, ATLASY, OPERATY_BDO):
        if r in dost:
            wyn.add(r)
    for folder in foldery:
        kat = os.path.join(folder, sp.FOLDER_OPERATOW_ZWYKLYCH)
        if any(not p.lower().endswith('_bdo.pdf') for p in sp._pdfy(kat)):
            wyn.add(OPERATY)
    return wyn


def braki_obrebu(pliki, rodzaje):
    wyn = sp.braki_obrebu({sp.MAPY: pliki[MAPY], sp.ATLASY: pliki[ATLASY],
                           sp.OPERATY: pliki[OPERATY_BDO], sp.SHP: []},
                          [r for r in rodzaje if r != OPERATY])
    if OPERATY in rodzaje and not pliki[OPERATY]:
        wyn.insert(len(wyn) - (1 if 'operat BDO' in wyn else 0), 'operat')
    return wyn


def podwojne_bdo(obreb):
    """Opis, gdy operat BDO jest w obu lokalizacjach (wzięty nowszy)."""
    wyn = []
    for nazwa, lista in sp.wersje_bdo(obreb['folder'], obreb['municip'],
                                      obreb['community']).items():
        if len(lista) > 1:
            wyn.append(f"{nazwa}: wzięty z "
                       f"{os.path.relpath(os.path.dirname(lista[0]), obreb['folder'])}"
                       ' (nowszy)')
    return wyn


# ------------------------------------------------------------------- plan

def _klucz_obrebu(ob):
    return (ob['municip'], ob['community'], ob['nazwa_folderu'].lower())


def zaplanuj(gminy, rodzaje, limit=LIMIT):
    """gminy: {klucz: {'nazwa': Nazwa_gminy, 'obreby': [obręb]}} - obręby
    uzupełniane o 'pliki', 'braki' i 'podwojne'. Zwraca listę po nazwie:
    {klucz, nazwa, stem, obreby, czesci: [{folder, obreby, pliki:
    [(źródło, ścieżka względna)], rozmiar, za_duza}]}."""
    stemy = nazwy_folderow({k: g['nazwa'] for k, g in gminy.items()})
    plan = []
    for klucz in sorted(gminy, key=lambda k: stemy[k].lower()):
        obreby = sorted(gminy[klucz]['obreby'], key=_klucz_obrebu)
        pozycje = []
        for ob in obreby:
            ob['pliki'] = pliki_obrebu(ob['folder'], ob['municip'],
                                       ob['community'])
            ob['braki'] = braki_obrebu(ob['pliki'], rodzaje)
            ob['podwojne'] = (podwojne_bdo(ob) if OPERATY_BDO in rodzaje
                              else [])
            pary = [(p, os.path.join(PODFOLDERY[r], os.path.basename(p)))
                    for r in RODZAJE if r in rodzaje
                    for p in ob['pliki'][r]]
            if pary:
                pozycje.append(((ob, pary),
                                sum(sp._rozmiar(p) for p, _ in pary)))
        podzial = sp.podziel_na_czesci(pozycje, limit)
        czesci = []
        for i, czesc in enumerate(podzial, 1):
            pary = [para for _, lista in czesc for para in lista]
            rozmiar = sum(sp._rozmiar(p) for p, _ in pary)
            czesci.append({
                'folder': stemy[klucz] if len(podzial) == 1
                else f'{stemy[klucz]}_{i}',
                'obreby': [ob for ob, _ in czesc], 'pliki': pary,
                'rozmiar': rozmiar, 'za_duza': rozmiar >= limit})
        plan.append({'klucz': klucz, 'nazwa': gminy[klucz]['nazwa'],
                     'stem': stemy[klucz], 'obreby': obreby,
                     'czesci': czesci})
    return plan


def istniejace_wyniki(docelowy, plan):
    """Foldery, które ten przebieg zastąpi: <stem>, <stem>_<n> (także
    części z poprzedniego przebiegu, których teraz nie będzie)."""
    try:
        nazwy = os.listdir(docelowy)
    except OSError:
        return []
    wzory = [re.compile(r'^%s(_\d+)?$' % re.escape(p['stem']),
                        re.IGNORECASE) for p in plan]
    return sorted(n for n in nazwy
                  if os.path.isdir(os.path.join(docelowy, n)) and
                  any(w.match(n) for w in wzory))


# ------------------------------------------------------------- kopiowanie

def kopiuj_czesc(docelowy, czesc, postep=None):
    """Kopiuje część do <folder>.tmp (podfoldery tylko te, które mają
    pliki). postep(bajty) zwraca False = przerwij (Przerwano, .tmp
    usunięty). Zwraca listę błędów odczytu plików."""
    tymczasowy = os.path.join(docelowy, czesc['folder'] + TMP)
    if os.path.exists(tymczasowy):
        shutil.rmtree(tymczasowy)
    bledy = []
    try:
        for zrodlo, sciezka in czesc['pliki']:
            cel = os.path.join(tymczasowy, sciezka)
            os.makedirs(os.path.dirname(cel), exist_ok=True)
            try:
                shutil.copy2(zrodlo, cel)
            except OSError as e:
                bledy.append(f'{zrodlo}: {e}')
            if postep and postep(sp._rozmiar(zrodlo)) is False:
                raise Przerwano()
    except BaseException:
        shutil.rmtree(tymczasowy, ignore_errors=True)
        raise
    return bledy


def podmien(docelowy, plan, istniejace):
    """Po skopiowaniu wszystkich części: usuwa foldery z poprzedniego
    przebiegu (istniejace) i zmienia nazwy <folder>.tmp -> <folder>.
    Zwraca listę błędów."""
    bledy = []
    for nazwa in istniejace:
        try:
            shutil.rmtree(os.path.join(docelowy, nazwa))
        except OSError as e:
            bledy.append(f'Nie usunięto starego folderu {nazwa}: {e}')
    for poz in plan:
        for cz in poz['czesci']:
            tmp = os.path.join(docelowy, cz['folder'] + TMP)
            try:
                os.replace(tmp, os.path.join(docelowy, cz['folder']))
            except OSError as e:
                bledy.append(f"{cz['folder']}: {e} - pliki zostały w "
                             f"{cz['folder']}{TMP}")
    return bledy


def usun_tymczasowe(docelowy, plan):
    for poz in plan:
        for cz in poz['czesci']:
            shutil.rmtree(os.path.join(docelowy, cz['folder'] + TMP),
                          ignore_errors=True)


# ----------------------------------------------------------------- opisy

def _opis_obrebu(ob):
    return (f"{ob['nazwa_folderu']} / {ob['municip']}.{ob['community']} "
            f"{ob.get('nazwa_obrebu') or ''}").rstrip()


def opis_planu(plan, uwagi, rodzaje):
    linie = ['Zawartość: ' + ', '.join(ETYKIETY[r] for r in RODZAJE
                                       if r in rodzaje),
             f'Limit folderu: {sp.megabajty(LIMIT)}', '']
    for poz in plan:
        linie.append(f"{poz['nazwa']}: {len(poz['obreby'])} obr.")
        if not poz['czesci']:
            linie.append('  brak plików - folder nie powstanie')
        for cz in poz['czesci']:
            linie.append(f"  {cz['folder']} - {len(cz['obreby'])} obr., "
                         f"{len(cz['pliki'])} plików, "
                         f"{sp.megabajty(cz['rozmiar'])}")
            if cz['za_duza']:
                linie.append('    UWAGA: jeden obręb przekracza limit '
                             f'{sp.megabajty(LIMIT)} - obrębu się nie dzieli')
            for ob in cz['obreby']:
                linie.append(f'    {_opis_obrebu(ob)}')
        w_czesciach = [ob for cz in poz['czesci'] for ob in cz['obreby']]
        for ob in poz['obreby']:
            if ob not in w_czesciach:
                linie.append(f'    {_opis_obrebu(ob)} - brak plików')
        linie.append('')

    braki = [(_opis_obrebu(ob), ob['braki']) for poz in plan
             for ob in poz['obreby'] if ob['braki']]
    if braki:
        linie.append('BRAKI PLIKÓW:')
        linie += [f"  {k}: {', '.join(v)}" for k, v in braki]
        linie.append('')
    podwojne = [(_opis_obrebu(ob), o) for poz in plan
                for ob in poz['obreby'] for o in ob['podwojne']]
    if podwojne:
        linie.append('OPERATY BDO W OBU LOKALIZACJACH (Operaty_BDO i '
                     'Operaty/Operaty_BDO):')
        linie += [f'  {k}: {o}' for k, o in podwojne]
        linie.append('')
    if uwagi:
        linie.append('UWAGI:')
        linie += [f'  {u}' for u in uwagi]
        linie.append('')
    return '\n'.join(linie)
