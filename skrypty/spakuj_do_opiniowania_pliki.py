# -*- coding: utf-8 -*-
"""Spakuj do opiniowania przez Nadleśnictwo - część bez QGIS-a (testowalna:
testy/test_spakuj_do_opiniowania.py): wyszukiwanie plików obrębu, nazwy,
podział na ZIP-y, pakowanie, zestawienie XLSX, raport.

Układ danych w folderze gminy/obrębu:
    Operaty_BDO/<woj>-<MUNICIP>-<COMMUNITY>-<nazwa>_BDO.pdf
    PLOTOWANIE/<MUNICIP>_<nazwa>/Mapy/<COMMUNITY>_<nazwa>_*.pdf
    PLOTOWANIE/<MUNICIP>_<nazwa>/Atlasy/<COMMUNITY>_<nazwa>_*.pdf
                                     (atlas + legenda, np. *_ATLAS, *_LEG)

Obręb to (folder, MUNICIP, COMMUNITY) - słownik z kluczami:
folder, nazwa_folderu, municip, community, nazwa_gminy, nazwa_obrebu.

Do ZIP-a trafiają wyłącznie operaty *_BDO.pdf - zwykły operat zawiera dane
osobowe i nie jest brany nawet wtedy, gdy wersji BDO brakuje.
"""
import os
import re
import unicodedata
import zipfile

FOLDER_WYNIKOWY = 'N-ctwa_do_opiniowania'
PLIK_XLSX = 'Nadlesnictwa_obreby.xlsx'
FOLDER_PLOTOWANIA = 'PLOTOWANIE'
FOLDER_OPERATOW = 'Operaty_BDO'
LIMIT_ZIP = 500 * 1024 * 1024

MAPY = 'Mapy'
ATLASY = 'Atlasy'
OPERATY = 'Operaty BDO'
RODZAJE = (MAPY, ATLASY, OPERATY)

_POLSKIE = str.maketrans('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ', 'acelnoszzACELNOSZZ')
_NAGLOWKI_XLSX = ('Nr gminy', 'Nazwa gminy', 'Nr obrębu', 'Nazwa obrębu')


class Przerwano(Exception):
    """Użytkownik przerwał pakowanie."""


# ------------------------------------------------------------------ nazwy

def bez_polskich(tekst):
    tekst = str(tekst).translate(_POLSKIE)
    return ''.join(z for z in unicodedata.normalize('NFKD', tekst)
                   if not unicodedata.combining(z))


def nazwa_pliku(tekst):
    """DĘBICA -> DEBICA, CZARNA BIAŁOSTOCKA -> CZARNA_BIALOSTOCKA."""
    tekst = bez_polskich(tekst).upper()
    return re.sub(r'[^A-Z0-9-]+', '_', tekst).strip('_')


def nazwy_zipow(nadlesnictwa):
    """{klucz: nazwa pliku bez rozszerzenia} dla {klucz: {nazwa, rdlp}}.
    Ta sama nazwa nadleśnictwa w dwóch RDLP (jest np. GŁOGÓW w Krośnie
    i Wrocławiu) dostaje przyrostek z RDLP."""
    podstawa = {k: nazwa_pliku(v['nazwa']) or 'NADLESNICTWO'
                for k, v in nadlesnictwa.items()}
    wyn = {}
    uzyte = set()
    for k in sorted(podstawa, key=lambda x: (podstawa[x], str(x))):
        nazwa = podstawa[k]
        if list(podstawa.values()).count(nazwa) > 1:
            rdlp = nazwa_pliku(nadlesnictwa[k].get('rdlp') or '')
            if rdlp:
                nazwa = f'{nazwa}_{rdlp}'
        kandydat, nr = nazwa, 2
        while kandydat in uzyte:
            kandydat = f'{nazwa}_{nr}'
            nr += 1
        uzyte.add(kandydat)
        wyn[k] = kandydat
    return wyn


def etykieta_obrebu(obreb):
    """Folder obrębu w ZIP-ie: 0013_STOBIERNA."""
    nazwa = nazwa_pliku(obreb.get('nazwa_obrebu') or '')
    return f"{obreb['community']}_{nazwa}" if nazwa else obreb['community']


# ---------------------------------------------------------- pliki obrębu

def _pdfy(katalog):
    try:
        return sorted(p for p in os.listdir(katalog)
                      if p.lower().endswith('.pdf') and
                      os.path.isfile(os.path.join(katalog, p)))
    except OSError:
        return []


def _foldery_plotowania(folder, municip=None):
    """Podfoldery PLOTOWANIE; z municip - tylko <MUNICIP>_*."""
    plot = os.path.join(folder, FOLDER_PLOTOWANIA)
    try:
        nazwy = sorted(os.listdir(plot))
    except OSError:
        return []
    return [os.path.join(plot, n) for n in nazwy
            if os.path.isdir(os.path.join(plot, n)) and
            (municip is None or n.startswith(f'{municip}_'))]


def _operat(nazwa, municip, community):
    wzor = r'^\d+-%s-%s(-.*)?_BDO\.pdf$' % (
        re.escape(municip), re.escape(community))
    return re.match(wzor, nazwa, re.IGNORECASE) is not None


def pliki_obrebu(folder, municip, community):
    """{rodzaj: [ścieżki PDF]} dla jednego obrębu. Foldery arch, Operaty
    i pliki poza poniższymi lokalizacjami nie są w ogóle przeglądane."""
    wyn = {r: [] for r in RODZAJE}
    for podf, rodzaj in (('Mapy', MAPY), ('Atlasy', ATLASY)):
        for plot in _foldery_plotowania(folder, municip):
            kat = os.path.join(plot, podf)
            wyn[rodzaj] += [os.path.join(kat, p) for p in _pdfy(kat)
                            if p.startswith(f'{community}_')]
    kat = os.path.join(folder, FOLDER_OPERATOW)
    wyn[OPERATY] = [os.path.join(kat, p) for p in _pdfy(kat)
                    if _operat(p, municip, community)]
    return wyn


def dostepne_rodzaje(foldery):
    """Które rodzaje materiałów są w ogóle w podanych folderach."""
    wyn = set()
    for folder in foldery:
        for plot in _foldery_plotowania(folder):
            if _pdfy(os.path.join(plot, 'Mapy')):
                wyn.add(MAPY)
            if _pdfy(os.path.join(plot, 'Atlasy')):
                wyn.add(ATLASY)
        if any(p.lower().endswith('_bdo.pdf')
               for p in _pdfy(os.path.join(folder, FOLDER_OPERATOW))):
            wyn.add(OPERATY)
    return wyn


def nazwa_obrebu_z_plikow(pliki, community):
    """Nazwa obrębu, gdy nie ma jej w OBR.shp: z operatu
    (03-042-0013-Stobierna_BDO.pdf), inaczej z mapy/atlasu
    (0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf)."""
    for sc in pliki.get(OPERATY, []):
        m = re.match(r'^\d+-\d+-\d+-(.+)_BDO\.pdf$', os.path.basename(sc),
                     re.IGNORECASE)
        if m:
            return m.group(1)
    for rodzaj in (MAPY, ATLASY):
        for sc in pliki.get(rodzaj, []):
            m = re.match(
                r'^%s_(.+?)_(MAPA|ATLAS|LEG)' % re.escape(community),
                os.path.basename(sc), re.IGNORECASE)
            if m:
                return m.group(1)
    return ''


def braki_obrebu(pliki, rodzaje):
    """Opisy brakujących materiałów spośród wybranych rodzajów."""
    wyn = []
    if MAPY in rodzaje and not pliki[MAPY]:
        wyn.append('mapa')
    if ATLASY in rodzaje:
        nazwy = [os.path.basename(p).upper() for p in pliki[ATLASY]]
        if not any('_ATLAS' in n for n in nazwy):
            wyn.append('atlas')
        if not any('_LEG' in n for n in nazwy):
            wyn.append('legenda')
    if OPERATY in rodzaje and not pliki[OPERATY]:
        wyn.append('operat BDO')
    return wyn


# ------------------------------------------------------------------- plan

def podziel_na_czesci(pozycje, limit=LIMIT_ZIP):
    """[(obiekt, rozmiar)] -> [[obiekt, ...], ...] - po kolei; każda część
    ma mniej niż limit bajtów, obiekt nigdy nie jest dzielony (pojedynczy
    obiekt >= limitu dostaje własną część)."""
    czesci, biezaca, suma = [], [], 0
    for obiekt, rozmiar in pozycje:
        if biezaca and suma + rozmiar >= limit:
            czesci.append(biezaca)
            biezaca, suma = [], 0
        biezaca.append(obiekt)
        suma += rozmiar
    if biezaca:
        czesci.append(biezaca)
    return czesci


def klucz_sortowania_obrebu(obreb):
    return (obreb['nazwa_folderu'].lower(), obreb['municip'],
            obreb['community'])


def zaplanuj(przypisania, obreby, nadlesnictwa, rodzaje, limit=LIMIT_ZIP):
    """Plan pakowania - lista po nazwie pliku:
    {klucz, nazwa, stem, obreby: [obręb], czesci: [{plik, obreby, pliki:
    [(źródło, ścieżka w ZIP-ie)], rozmiar, za_duza}]}.
    przypisania: {klucz nadleśnictwa: {klucz obrębu}},
    obreby: {klucz obrębu: obręb} - uzupełniane o 'pliki' i 'braki'
    (także nazwa obrębu, gdy była pusta)."""
    for ob in obreby.values():
        ob['pliki'] = pliki_obrebu(ob['folder'], ob['municip'],
                                   ob['community'])
        ob['braki'] = braki_obrebu(ob['pliki'], rodzaje)
        if not ob.get('nazwa_obrebu'):
            ob['nazwa_obrebu'] = nazwa_obrebu_z_plikow(ob['pliki'],
                                                       ob['community'])

    stemy = nazwy_zipow({k: nadlesnictwa[k] for k in przypisania})
    plan = []
    for klucz in sorted(przypisania, key=lambda k: stemy[k]):
        lista = sorted((obreby[k] for k in przypisania[klucz]),
                       key=klucz_sortowania_obrebu)
        pozycje = []
        for ob in lista:
            pliki = [p for r in rodzaje for p in ob['pliki'][r]]
            if pliki:
                pozycje.append(((ob, pliki),
                                sum(_rozmiar(p) for p in pliki)))
        podzial = podziel_na_czesci(pozycje, limit)
        czesci = []
        for i, czesc in enumerate(podzial, 1):
            stem = stemy[klucz] if len(podzial) == 1 \
                else f'{stemy[klucz]}_{i}'
            pary = [(p, '/'.join((ob['nazwa_folderu'], etykieta_obrebu(ob),
                                  os.path.basename(p))))
                    for ob, pliki in czesc for p in pliki]
            rozmiar = sum(_rozmiar(p) for p, _ in pary)
            czesci.append({'plik': f'{stem}.zip',
                           'obreby': [ob for ob, _ in czesc],
                           'pliki': pary, 'rozmiar': rozmiar,
                           'za_duza': rozmiar >= limit})
        plan.append({'klucz': klucz, 'nazwa': nadlesnictwa[klucz]['nazwa'],
                     'stem': stemy[klucz], 'obreby': lista, 'czesci': czesci})
    return plan


def _rozmiar(sciezka):
    try:
        return os.path.getsize(sciezka)
    except OSError:
        return 0


def istniejace_wyniki(folder, plan):
    """Pliki, które ten przebieg zastąpi: <stem>.zip, <stem>_<n>.zip (także
    części z poprzedniego przebiegu, które teraz by nie powstały) i XLSX."""
    try:
        nazwy = os.listdir(folder)
    except OSError:
        return []
    wzory = [re.compile(r'^%s(_\d+)?\.zip$' % re.escape(p['stem']),
                        re.IGNORECASE) for p in plan]
    return sorted(n for n in nazwy
                  if n.lower() == PLIK_XLSX.lower() or
                  any(w.match(n) for w in wzory))


# -------------------------------------------------------------- pakowanie

def spakuj_czesc(folder, czesc, postep=None):
    """Tworzy ZIP części (przez plik tymczasowy - przerwany przebieg nie
    zostawia niepełnego ZIP-a). postep(bajty_pliku) zwraca False, gdy
    przerwać. Zwraca listę błędów odczytu plików."""
    docelowy = os.path.join(folder, czesc['plik'])
    tymczasowy = docelowy + '.tmp'
    bledy = []
    try:
        with zipfile.ZipFile(tymczasowy, 'w', zipfile.ZIP_DEFLATED,
                             allowZip64=True) as zf:
            for zrodlo, sciezka in czesc['pliki']:
                try:
                    zf.write(zrodlo, sciezka)
                except OSError as e:
                    bledy.append(f'{zrodlo}: {e}')
                if postep and postep(_rozmiar(zrodlo)) is False:
                    raise Przerwano()
        os.replace(tymczasowy, docelowy)
    except BaseException:
        if os.path.exists(tymczasowy):
            os.remove(tymczasowy)
        raise
    return bledy


def _nazwa_arkusza(stem, uzyte):
    baza = stem[:31]
    nazwa, nr = baza, 2
    while nazwa in uzyte:
        dopisek = f'_{nr}'
        nazwa = baza[:31 - len(dopisek)] + dopisek
        nr += 1
    uzyte.add(nazwa)
    return nazwa


def zapisz_xlsx(sciezka, plan):
    """Jeden skoroszyt, arkusz na nadleśnictwo (numery jako tekst - zera
    wiodące zostają)."""
    import openpyxl
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    uzyte = set()
    for poz in plan:
        ws = wb.create_sheet(_nazwa_arkusza(poz['stem'], uzyte))
        ws.append(list(_NAGLOWKI_XLSX))
        for kom in ws[1]:
            kom.font = Font(bold=True)
        for ob in poz['obreby']:
            ws.append([ob['municip'], ob.get('nazwa_gminy') or '',
                       ob['community'], ob.get('nazwa_obrebu') or ''])
            ws.cell(row=ws.max_row, column=1).number_format = '@'
            ws.cell(row=ws.max_row, column=3).number_format = '@'
        for kol, szer in zip('ABCD', (10, 28, 10, 28)):
            ws.column_dimensions[kol].width = szer
        ws.freeze_panes = 'A2'
    wb.save(sciezka)


# ----------------------------------------------------------------- opisy

def megabajty(bajty):
    return f'{bajty / 1048576:.1f} MB'


def _opis_obrebu(ob):
    return (f"{ob['nazwa_folderu']} / {ob['community']} "
            f"{ob.get('nazwa_obrebu') or ''}").rstrip()


def opis_planu(plan, poza, uwagi, rodzaje):
    """Tekst podglądu przed pakowaniem i początek raportu."""
    linie = ['Zawartość: ' + ', '.join(
        'Atlasy z legendami' if r == ATLASY else r for r in rodzaje), '']
    for poz in plan:
        linie.append(f"{poz['nazwa']}: {len(poz['obreby'])} obr.")
        if not poz['czesci']:
            linie.append('  brak plików - ZIP nie powstanie')
        for cz in poz['czesci']:
            linie.append(f"  {cz['plik']} - {len(cz['obreby'])} obr., "
                         f"{len(cz['pliki'])} plików, "
                         f"{megabajty(cz['rozmiar'])}")
            if cz['za_duza']:
                linie.append('    UWAGA: jeden obręb przekracza limit '
                             f'{megabajty(LIMIT_ZIP)} - obrębu się nie dzieli')
            for ob in cz['obreby']:
                linie.append(f'    {_opis_obrebu(ob)}')
        bez_plikow = [ob for ob in poz['obreby']
                      if not any(ob in cz['obreby'] for cz in poz['czesci'])]
        for ob in bez_plikow:
            linie.append(f'    {_opis_obrebu(ob)} - brak plików')
        linie.append('')

    braki = {}
    for poz in plan:
        for ob in poz['obreby']:
            if ob['braki']:
                braki[_opis_obrebu(ob)] = ob['braki']
    if braki:
        linie.append('BRAKI PLIKÓW:')
        linie += [f"  {k}: {', '.join(v)}" for k, v in sorted(braki.items())]
        linie.append('')
    if poza:
        linie.append('OBRĘBY BEZ NADLEŚNICTWA (żadne wydzielenie nie ma '
                     'ponad 20% w nadleśnictwie):')
        linie += [f'  {_opis_obrebu(ob)}'
                  for ob in sorted(poza, key=klucz_sortowania_obrebu)]
        linie.append('')
    if uwagi:
        linie.append('UWAGI:')
        linie += [f'  {u}' for u in uwagi]
        linie.append('')
    return '\n'.join(linie)
