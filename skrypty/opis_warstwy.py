"""Warstwy i gatunki opisu taksacyjnego - reguły poprawności, sortowanie i
plan zapisu do bazy (bez interfejsu; używane przez opis_taksacyjny.py).

Reguły z F_ERROR_DIC Taksatora, zawężone i sprawdzone na bazach z
materialy (krok 2, 24 bazy z opisem, ~100 tys. gatunków):
- twarde (BLAD - blokują zapis): zgodne z danymi Taksatora w 98-100%,
- ostrzeżenia (OSTRZ - zapis możliwy): braki pomiarów, limity - decyzja
  użytkownika: brakujące pomiary tylko ostrzegają.

Model danych warstwy (słownik):
    {'STOREY_CD', 'MIXTURE_CD', 'DENSITY_CD', 'STANDDENSITY_INDEX',
     'gatunki': [{'SPEC_STOR_INT_NUM' (None = nowy), 'SPECIES_CD',
                  'PART_CD', 'SPECIES_AGE', 'BHD', 'HEIGHT',
                  'SITE_CLASS_CD', 'VOLUME'}, ...]}
Kody jako tekst ('' = brak), liczby jako int/float albo None.
"""
import json

from .aktualizacja_upul.core.formula import obliczona_masa

BLAD, OSTRZ = 'blad', 'ostrz'

# warstwy dostępne w "+ Warstwa" (używane w praktyce - decyzja użytkownika)
PRAKTYCZNE = ['DRZEW', 'PODR', 'NAL', 'PODSZ', 'PRZES', 'ZADRZEW', 'ZAKRZEW']

JAK_DRZEW = {'DRZEW', 'IP', 'IIP'}
JAK_PODROST = {'PODR', 'PODRII', 'PODS'}
UDZIAL_WYMAGANY = JAK_DRZEW | JAK_PODROST | {'NAL'}
UDZIAL_ZAKAZANY = {'PODSZ', 'PRZES', 'ZADRZEW', 'ZAKRZEW'}
BEZ_WIEKU = {'PODSZ', 'ZAKRZEW'}
ZADRZEWIENIE_WYMAGANE = JAK_DRZEW | JAK_PODROST | {'NAL', 'PODSZ'}
ZADRZEWIENIE_ZAKAZANE = {'PRZES'}
ZMIESZANIE_ZAKAZANE = {'PRZES'}
# IP/IIP zastępują DRZEW - na początku kolejności warstw
KOLEJNOSC_SPECJALNA = {'IP': 0.1, 'IIP': 0.2}

POLA_WARSTWY = ['MIXTURE_CD', 'DENSITY_CD', 'STANDDENSITY_INDEX']
POLA_GATUNKU = ['SPECIES_CD', 'PART_CD', 'SPECIES_AGE', 'BHD', 'HEIGHT',
                'SITE_CLASS_CD', 'VOLUME']
LIMITY = [('SPECIES_AGE', 200, 'GAT26', 'Wiek przekracza 200'),
          ('BHD', 200, 'GAT27', 'Pierśnica przekracza 200'),
          ('HEIGHT', 60, 'GAT28', 'Wysokość przekracza 60'),
          ('VOLUME', 1200, 'GAT29', 'Zasobność przekracza 1200')]


def pusty(v):
    return v is None or (isinstance(v, str) and v.strip() == '')


def udzial_liczbowy(p):
    p = '' if p is None else str(p).strip()
    return int(p) if p.isdigit() else None


# ------------------------------------------------------------------ reguły

def waliduj(warstwy, rodzaj_pow=''):
    """Zwraca {klucz: [(poziom, kod_reguly, komunikat), ...]}; klucz:
    (wi, gi, pole) - komórka gatunku, (wi, None, pole) - komórka warstwy,
    (wi, None, None) - cała warstwa, ('wydz', None, None) - wydzielenie."""
    wyn = {}

    def dodaj(klucz, poziom, kod, tekst):
        wyn.setdefault(klucz, []).append((poziom, kod, tekst))

    if rodzaj_pow == 'D-STAN' and not any(
            w['STOREY_CD'] in JAK_DRZEW for w in warstwy):
        dodaj(('wydz', None, None), BLAD, 'WAR33',
              'Brak warstwy drzewostanu (DRZEW) dla D-STAN')

    for wi, w in enumerate(warstwy):
        k = w['STOREY_CD']
        gat = w['gatunki']
        if not gat:
            dodaj((wi, None, None), BLAD, 'WAR29',
                  f'Warstwa {k} nie ma gatunków')
        liczbowe = [(gi, udzial_liczbowy(g['PART_CD']))
                    for gi, g in enumerate(gat)
                    if udzial_liczbowy(g['PART_CD']) is not None]

        # --- parametry warstwy
        if k in JAK_DRZEW and len(liczbowe) > 1 and pusty(w['MIXTURE_CD']):
            dodaj((wi, None, 'MIXTURE_CD'), BLAD, 'WAR13',
                  'Więcej niż 1 gatunek z udziałem - wymagane zmieszanie')
        if k in ZMIESZANIE_ZAKAZANE and not pusty(w['MIXTURE_CD']):
            dodaj((wi, None, 'MIXTURE_CD'), BLAD, 'WAR14',
                  f'Dla {k} nie podaje się zmieszania')
        if k in ZADRZEWIENIE_ZAKAZANE and not pusty(w['STANDDENSITY_INDEX']):
            dodaj((wi, None, 'STANDDENSITY_INDEX'), BLAD, 'WAR20',
                  f'Dla {k} nie podaje się zadrzewienia')
        if k in ZADRZEWIENIE_WYMAGANE and pusty(w['STANDDENSITY_INDEX']):
            dodaj((wi, None, 'STANDDENSITY_INDEX'), BLAD, 'WAR19',
                  f'Dla {k} wymagane jest zadrzewienie')
        if k in JAK_DRZEW and pusty(w['DENSITY_CD']):
            dodaj((wi, None, 'DENSITY_CD'), OSTRZ, '',
                  'Brak zwarcia (w danych Taksatora podawane w 99%)')

        # --- suma udziałów
        if liczbowe and sum(u for _gi, u in liczbowe) != 10:
            suma = sum(u for _gi, u in liczbowe)
            for gi, _u in liczbowe:
                dodaj((wi, gi, 'PART_CD'), BLAD, 'GAT15',
                      f'Suma udziałów w warstwie = {suma}, musi być 10')

        # --- gatunki
        widziane = {}
        for gi, g in enumerate(gat):
            u = udzial_liczbowy(g['PART_CD'])
            part = '' if g['PART_CD'] is None else str(g['PART_CD']).strip()
            if pusty(g['SPECIES_CD']):
                dodaj((wi, gi, 'SPECIES_CD'), BLAD, '',
                      'Brak kodu gatunku (usuń wiersz przyciskiem ✕ albo '
                      'wpisz kod)')
            if k in UDZIAL_WYMAGANY and not part:
                dodaj((wi, gi, 'PART_CD'), BLAD, 'GAT11',
                      f'Dla {k} udział jest wymagany')
            if k in UDZIAL_ZAKAZANY and part:
                dodaj((wi, gi, 'PART_CD'), BLAD, 'GAT22',
                      f'Dla {k} udział musi pozostać pusty')
            if k not in BEZ_WIEKU and pusty(g['SPECIES_AGE']):
                dodaj((wi, gi, 'SPECIES_AGE'), BLAD, 'GAT19',
                      f'Dla {k} wymagany jest wiek gatunku')
            if part in ('PJD', 'MJS') and not pusty(g['VOLUME']):
                dodaj((wi, gi, 'VOLUME'), BLAD, 'GAT17',
                      'Dla udziału PJD/MJS zasobność musi być pusta')
            if str(g['SITE_CLASS_CD'] or '').strip() == 'IA' and \
                    not str(g['SPECIES_CD']).startswith('SO'):
                dodaj((wi, gi, 'SITE_CLASS_CD'), BLAD, 'GAT18',
                      'Bonitacja IA tylko dla sosny (SO*)')
            para = (g['SPECIES_CD'], g['SPECIES_AGE'])
            if para in widziane:
                for x in (widziane[para], gi):
                    dodaj((wi, x, 'SPECIES_CD'), BLAD, 'GAT13',
                          'Ten sam gatunek w tym samym wieku w warstwie')
            widziane[para] = gi

            # braki pomiarów - tylko ostrzeżenia
            wymagane = []
            if k in JAK_DRZEW and u is not None:
                wymagane = ['SITE_CLASS_CD', 'HEIGHT']
                if (g['SPECIES_AGE'] or 0) >= 20:
                    wymagane += ['BHD', 'VOLUME']
            elif k in JAK_PODROST and u is not None:
                wymagane = ['SITE_CLASS_CD', 'HEIGHT']
            elif k == 'NAL' and u is not None:
                wymagane = ['SITE_CLASS_CD']
            elif k == 'PRZES':
                wymagane = ['BHD', 'HEIGHT', 'VOLUME', 'SITE_CLASS_CD']
            for pole in wymagane:
                if pusty(g[pole]):
                    dodaj((wi, gi, pole), OSTRZ, '',
                          'Brak wartości (w danych Taksatora zwykle podawana)')
            if not pusty(g['BHD']) and not pusty(g['HEIGHT']) and \
                    pusty(g['VOLUME']) and part not in ('PJD', 'MJS'):
                dodaj((wi, gi, 'VOLUME'), OSTRZ, 'GAT23',
                      'Podano pierśnicę i wysokość - brak zasobności')
            for pole, limit, kod, tekst in LIMITY:
                if not pusty(g[pole]) and float(g[pole]) > limit:
                    dodaj((wi, gi, pole), OSTRZ, kod, tekst)
    return wyn


def lista_bledow(walidacja, warstwy):
    """Błędy twarde bez powtórzeń: reguły dotyczące całej warstwy (np.
    GAT15 zaznaczony na każdym udziale) raz na warstwę, dubel GAT13 raz na
    parę gatunek+wiek."""
    wyn = []
    for (wi, gi, _pole), lst in sorted(
            walidacja.items(), key=lambda x: str(x[0])):
        for p, kod, tx in lst:
            if p != BLAD:
                continue
            if wi == 'wydz':
                gdzie = 'wydzielenie'
            else:
                gdzie = warstwy[wi]['STOREY_CD']
                if gi is not None and kod != 'GAT15':
                    g = warstwy[wi]['gatunki'][gi]
                    gdzie += f" / {g['SPECIES_CD'] or '(bez kodu)'}"
                    if kod == 'GAT13':
                        gdzie += f" {g['SPECIES_AGE']} lat"
            linia = f'{gdzie}: {kod} {tx}'.replace(':  ', ': ')
            if linia not in wyn:
                wyn.append(linia)
    return wyn


def wczytaj_tablice_bonitacji(cur):
    """(tablica, masy, grupy): tablica {(gatunek, wiek): {klasa: wysokość}}
    i masy {(gatunek, wiek): {klasa: zasobność}} z F_TABLICA_ROZSZERZONA,
    grupy {gatunek: gatunek tablicowy} z F_TREE_SPECIES.HEIGHT_GRP
    (gatunki bez własnej tablicy). Puste, gdy bazy nie mają tych tabel."""
    tablica, masy, grupy = {}, {}, {}
    try:
        for g, k, w, h, v in cur.execute(
                'select SPECIES_CD, SITE_CLASS_CD, SPECIES_AGE, HEIGHT, '
                'VOLUME from F_TABLICA_ROZSZERZONA').fetchall():
            if g is None or k is None or w is None:
                continue
            klucz, klasa = (str(g).strip(), int(w)), str(k).strip()
            if h is not None:
                tablica.setdefault(klucz, {})[klasa] = float(h)
            if v is not None:
                masy.setdefault(klucz, {})[klasa] = float(v)
        for g, grp in cur.execute(
                'select SPECIES_CD, HEIGHT_GRP from F_TREE_SPECIES').fetchall():
            if g is not None and grp is not None:
                grupy[str(g).strip()] = str(grp).strip()
    except Exception:
        return {}, {}, {}
    return tablica, masy, grupy


def sugeruj_bonitacje(tablica, grupy, gatunek, wiek, wysokosc):
    """Klasa bonitacji z tablicy: najbliższa wysokość tablicowa dla
    gatunku i wieku (remis - niższa klasa). Na bazach Taksatora zgodna z
    wpisaną bonitacją w 90,4% (reszta to ocena taksatora) - dlatego tylko
    podpowiedź do zatwierdzenia. None, gdy brak danych."""
    if not tablica or pusty(gatunek) or wiek is None or wysokosc is None:
        return None
    klasy = tablica.get((gatunek, int(wiek))) or \
        tablica.get((grupy.get(gatunek, ''), int(wiek)))
    if not klasy:
        return None
    return min(klasy, key=lambda k: (abs(klasy[k] - float(wysokosc)),
                                     klasy[k]))


# ------------------------------------------------- masa <-> zadrzewienie
# Wzór F3 z Aktualizacji UPUL (aktualizacja_upul/core/formula.py), liczony
# w dwie strony, tylko dla warstwy DRZEW:
#   masa gatunku = ROUND(Vtab * 0,1 * udział * Zd)
#   Zd           = ROUND(suma mas / suma(Vtab * udział / 10), 1)
# Vtab z F_TABLICA_ROZSZERZONA (gatunek, wiek, bonitacja), dla gatunków
# bez własnej tablicy - gatunek tablicowy (HEIGHT_GRP); IA poza SO* jak I,
# 0 w tablicy jak 1; PJD/MJS poza obliczeniami.

WARSTWA_MASY = 'DRZEW'
WSP_MASY, ZERO_MASY = 0.1, 1   # constants.json Aktualizacji UPUL


def masa_tablicowa(masy, grupy, g):
    """Vtab dla gatunku albo None (brak gatunku, wieku, bonitacji lub
    wpisu w tablicy)."""
    gat, wiek = g['SPECIES_CD'], g['SPECIES_AGE']
    klasa = (g['SITE_CLASS_CD'] or '').strip()
    if not masy or pusty(gat) or wiek is None or not klasa:
        return None
    if klasa == 'IA' and not gat.startswith('SO'):
        klasa = 'I'
    for klucz in (gat, grupy.get(gat)):
        v = masy.get((klucz, int(wiek)), {}).get(klasa)
        if v is not None:
            return v
    return None


def udzial_masy(g):
    u = udzial_liczbowy(g['PART_CD'])
    return u if u is not None and 1 <= u <= 10 else None


def masa_z_zd(masy, grupy, g, zd):
    """Masa gatunku z zadrzewienia albo None, gdy nie da się policzyć."""
    u = udzial_masy(g)
    vt = masa_tablicowa(masy, grupy, g)
    if u is None or vt is None or zd is None:
        return None
    return obliczona_masa(vt, zd, u, ZERO_MASY, WSP_MASY)


def zd_z_mas(masy, grupy, gatunki):
    """(Zd albo None, pominięte gatunki) - zadrzewienie z mas gatunków na
    udziale 1-10; gatunek bez masy albo bez wpisu w tablicy pomijany."""
    suma_v = suma_t = 0.0
    pominiete = []
    for g in gatunki:
        u = udzial_masy(g)
        if u is None:
            continue
        vt = masa_tablicowa(masy, grupy, g)
        if vt is None or g['VOLUME'] is None:
            pominiete.append(g['SPECIES_CD'] or '?')
            continue
        suma_v += g['VOLUME']
        suma_t += (vt or ZERO_MASY) * u / 10
    if suma_t <= 0:
        return None, pominiete
    return round(suma_v / suma_t, 1), pominiete


def pola_wymagane_warstwy(kod):
    """Pola parametrów warstwy odwiedzane przez Enter (kolejność kolumn)."""
    if kod in JAK_DRZEW:
        return ['MIXTURE_CD', 'DENSITY_CD', 'STANDDENSITY_INDEX']
    if kod in ZADRZEWIENIE_WYMAGANE:
        return ['STANDDENSITY_INDEX']
    return []


def pola_wymagane_gatunku(kod, g):
    """Pola gatunku odwiedzane przez Enter - wg profilu warstw z danych
    Taksatora (krok 2), liczone na bieżących wartościach wiersza."""
    part = '' if g.get('PART_CD') is None else str(g['PART_CD']).strip()
    liczbowy = part not in ('PJD', 'MJS')  # pusty udział = jeszcze nieznany
    wiek = g.get('SPECIES_AGE') or 0
    p = ['SPECIES_CD']
    if kod in JAK_DRZEW:
        p += ['PART_CD', 'SPECIES_AGE']
        if liczbowy:
            if wiek >= 20:
                p.append('BHD')
            p += ['HEIGHT', 'SITE_CLASS_CD']
            if wiek >= 20:
                p.append('VOLUME')
    elif kod in JAK_PODROST:
        p += ['PART_CD', 'SPECIES_AGE']
        if liczbowy:
            p += ['HEIGHT', 'SITE_CLASS_CD']
    elif kod == 'NAL':
        p += ['PART_CD', 'SPECIES_AGE']
        if liczbowy:
            p.append('SITE_CLASS_CD')
    elif kod == 'PRZES':
        p += ['SPECIES_AGE', 'BHD', 'HEIGHT', 'SITE_CLASS_CD', 'VOLUME']
    elif kod == 'ZADRZEW':
        p.append('SPECIES_AGE')
    return p


def policz(walidacja):
    bledy = sum(1 for lst in walidacja.values() for p, *_ in lst if p == BLAD)
    ostrz = sum(1 for lst in walidacja.values() for p, *_ in lst if p == OSTRZ)
    return bledy, ostrz


# -------------------------------------------------------------- sortowanie

def _klucz_gatunku(g):
    u = udzial_liczbowy(g['PART_CD'])
    part = '' if g['PART_CD'] is None else str(g['PART_CD']).strip()
    if u is not None:
        return (0, -u)
    return {'MJS': (1, 0), 'PJD': (2, 0)}.get(part, (3, 0))


def posortuj(warstwy, nr_warstw):
    """Kolejność jak w danych Taksatora: warstwy wg numeru słownika
    F_STOREY_DIC (IP/IIP na początku), gatunki - udziały liczbowe
    malejąco, potem MJS, potem PJD (sortowanie stabilne)."""
    def kw(w):
        k = w['STOREY_CD']
        return KOLEJNOSC_SPECJALNA.get(k, float(nr_warstw.get(k, 99)))
    wyn = sorted(warstwy, key=kw)
    for w in wyn:
        w['gatunki'] = sorted(w['gatunki'], key=_klucz_gatunku)
    return wyn


# ------------------------------------------------------------- plan zapisu

def _opis_gatunku(g):
    return '|'.join('' if g.get(p) is None else str(g.get(p))
                    for p in POLA_GATUNKU)


def plan_zapisu(aint, stare, nowe):
    """Lista (sql, parametry) do wykonania w JEDNEJ transakcji + wiersze
    dziennika (adr zostaje uzupełniony przez wywołującego).

    Zasady (klucze TPU):
    - istniejące gatunki aktualizowane w miejscu - zachowują
      SPEC_STOR_INT_NUM; nowe dostają autonumer Accessa (COUNTER),
    - unikalne indeksy F_STOREY_SPECIES (warstwa+ranga, warstwa+gatunek+
      wiek) - przed docelową aktualizacją wszystkie istniejące gatunki
      wydzielenia dostają tymczasowe, unikalne rangi i wiek (faza A),
    - `nowe` muszą być już posortowane (posortuj) - rangi = kolejność."""
    ops, dziennik = [], []
    stare_w = {w['STOREY_CD']: w for w in stare}
    nowe_w = {w['STOREY_CD']: w for w in nowe}

    # 1. usunięte warstwy (z gatunkami)
    for k, w in stare_w.items():
        if k not in nowe_w:
            ops.append(('delete from F_STOREY_SPECIES where ARODES_INT_NUM = ? '
                        'and STOREY_CD = ?', (aint, k)))
            ops.append(('delete from F_AROD_STOREY where ARODES_INT_NUM = ? '
                        'and STOREY_CD = ?', (aint, k)))
            dziennik.append(('WARSTWA_USUNIETA', k, json.dumps(
                w, ensure_ascii=False, default=str), ''))

    # 2. usunięte gatunki w zachowanych warstwach
    zachowane_id = {g['SPEC_STOR_INT_NUM'] for w in nowe for g in w['gatunki']
                    if g['SPEC_STOR_INT_NUM'] is not None}
    for k, w in stare_w.items():
        if k not in nowe_w:
            continue
        for g in w['gatunki']:
            if g['SPEC_STOR_INT_NUM'] not in zachowane_id:
                ops.append(('delete from F_STOREY_SPECIES where '
                            'SPEC_STOR_INT_NUM = ?', (g['SPEC_STOR_INT_NUM'],)))
                dziennik.append(('GATUNEK_USUNIETY', f"{k}/{g['SPECIES_CD']}",
                                 _opis_gatunku(g), ''))

    # 3. faza A - tymczasowe rangi i wiek istniejących gatunków
    istniejace = [g for w in nowe for g in w['gatunki']
                  if g['SPEC_STOR_INT_NUM'] is not None]
    for i, g in enumerate(istniejace):
        ops.append(('update F_STOREY_SPECIES set SPECIES_RANK_ORDER = ?, '
                    'SPECIES_AGE = ? where SPEC_STOR_INT_NUM = ?',
                    (1000 + i, -1000 - i, g['SPEC_STOR_INT_NUM'])))

    # 4. warstwy: nowe i zmienione (rangi = kolejność)
    for r, w in enumerate(nowe, 1):
        k = w['STOREY_CD']
        wart = [None if pusty(w[p]) else w[p] for p in POLA_WARSTWY]
        if k not in stare_w:
            ops.append(('insert into F_AROD_STOREY (ARODES_INT_NUM, STOREY_CD, '
                        'STOREY_RANK_ORDER, ' + ', '.join(POLA_WARSTWY) +
                        ') values (?, ?, ?, ?, ?, ?)', (aint, k, r, *wart)))
            dziennik.append(('WARSTWA_DODANA', k, '', ''))
        else:
            ops.append(('update F_AROD_STOREY set STOREY_RANK_ORDER = ?, ' +
                        ', '.join(f'{p} = ?' for p in POLA_WARSTWY) +
                        ' where ARODES_INT_NUM = ? and STOREY_CD = ?',
                        (r, *wart, aint, k)))
            for p in POLA_WARSTWY:
                if stare_w[k][p] != w[p]:
                    dziennik.append(('ZMIANA', f'{k}/{p}', stare_w[k][p], w[p]))

    # 5. gatunki: docelowe wartości istniejących, wstawienie nowych
    stare_g = {g['SPEC_STOR_INT_NUM']: g for w in stare for g in w['gatunki']}
    for w in nowe:
        k = w['STOREY_CD']
        for r, g in enumerate(w['gatunki'], 1):
            wart = [None if pusty(g[p]) else g[p] for p in POLA_GATUNKU]
            if g['SPEC_STOR_INT_NUM'] is None:
                ops.append(('insert into F_STOREY_SPECIES (ARODES_INT_NUM, '
                            'STOREY_CD, SPECIES_RANK_ORDER, ' +
                            ', '.join(POLA_GATUNKU) + ') values (?, ?, ?, ' +
                            ', '.join('?' * len(POLA_GATUNKU)) + ')',
                            (aint, k, r, *wart)))
                dziennik.append(('GATUNEK_DODANY', f"{k}/{g['SPECIES_CD']}",
                                 '', _opis_gatunku(g)))
            else:
                ops.append(('update F_STOREY_SPECIES set SPECIES_RANK_ORDER = ?, ' +
                            ', '.join(f'{p} = ?' for p in POLA_GATUNKU) +
                            ' where SPEC_STOR_INT_NUM = ?',
                            (r, *wart, g['SPEC_STOR_INT_NUM'])))
                przed = stare_g.get(g['SPEC_STOR_INT_NUM'])
                if przed is not None and _opis_gatunku(przed) != _opis_gatunku(g):
                    dziennik.append(('GATUNEK_ZMIANA', f"{k}/{g['SPECIES_CD']}",
                                     _opis_gatunku(przed), _opis_gatunku(g)))
    return ops, dziennik
