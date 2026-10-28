# -*- coding: utf-8 -*-
"""Formy ochrony przyrody przy łączeniu/kopiowaniu baz TPU.

F_SET (wydzielenie -> forma) wskazuje formę przez MY_INT_NUM =
F_LAND_PROTECT.INT_NUM (tak zapisuje "Dopisz FOP", baza_dopisz_fochr.py).
Wcześniej łączenie kopiowało F_SET z MY_INT_NUM bez zmian, a F_LAND_PROTECT
wcale - wydzielenia z kolejnych baz wskazywały cudze formy (o tym samym
numerze w bazie docelowej) albo nieistniejące.

polacz_formy_ochrony() dopisuje do bazy docelowej formy użyte przez
kopiowane wiersze F_SET (ta sama forma = ten sam PROTEC_AREA_CD + nazwa ->
istniejący INT_NUM, nowa -> kolejny wolny) i zwraca słownik
{stary MY_INT_NUM: nowy INT_NUM} do przemapowania F_SET. Przy okazji
F_ENV_PROTECT (zestawienie form w obrębach) - dopisywane wiersze, których w
docelowej nie ma (obręb + kod formy). TEMP_ARODES_SET - tabela robocza TPU,
pomijana.

Źródło może mieć układ PUL (F_LAND_PROTECT.PROTECT_INT_NUM, bez
LAND_PROTECT_AREA) - kolumny rozpoznawane z odczytu.
"""

SL_FORM = 'sl_land_protect'      # nazwa słownika remapu (FK w rejestrze)
KLUCZE_ZRODLA = ('INT_NUM', 'PROTECT_INT_NUM')
ENV_KOLUMNY = [
    'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD', 'COMMUNITY_CD',
    'PROTEC_AREA_CD', 'ENV_COUNT', 'TOTAL_AREA', 'PUL_AREA', 'FOREST_AREA',
    'NFOREST_AREA', 'FOREST_AREA_P', 'NFOREST_AREA_P',
]


def _tekst(v):
    return '' if v is None else str(v).strip()


def _klucz_formy(kod, nazwa):
    return (_tekst(kod).upper(), _tekst(nazwa).upper())


def _kolumny(baza, tabela):
    """Nazwy kolumn tabeli z odczytu (cursor.columns() psuje pyodbc) albo
    None, gdy tabeli nie ma."""
    try:
        baza.cur.execute('select top 1 * from ' + tabela + ';')
        return [d[0] for d in baza.cur.description]
    except Exception:
        return None


def _formy(baza, l_bledy_odczytu, opis):
    """{INT_NUM: (kod, nazwa, powierzchnia)} z F_LAND_PROTECT."""
    kol = _kolumny(baza, 'F_LAND_PROTECT')
    if kol is None:
        l_bledy_odczytu.append((baza.baza, 'F_LAND_PROTECT',
                                'Nie udało się odczytać tabeli (%s)' % opis))
        return None
    duze = {k.upper(): k for k in kol}
    klucz = next((duze[k] for k in KLUCZE_ZRODLA if k in duze), None)
    if klucz is None or 'PROTEC_AREA_CD' not in duze:
        l_bledy_odczytu.append((baza.baza, 'F_LAND_PROTECT',
                                'Nieznany układ tabeli (%s): %s'
                                % (opis, ', '.join(kol))))
        return None
    pow_k = duze.get('LAND_PROTECT_AREA')
    sql = 'select %s, %s, %s, %s from F_LAND_PROTECT;' % (
        klucz, duze['PROTEC_AREA_CD'], duze.get('LAND_PROTECT_NAME', "''"),
        pow_k or 'null')
    wiersze = baza.pobierz(sql)
    if wiersze is False:
        l_bledy_odczytu.append((baza.baza, 'F_LAND_PROTECT',
                                'Nie udało się odczytać tabeli (%s)' % opis))
        return None
    return {w[0]: (w[1], w[2], w[3]) for w in wiersze}


def _wpisz(baza0, sql, params, tabela, opis, l_bledy_wpisu):
    try:
        baza0.cur.execute(sql, params)
        baza0.con.commit()
        return True
    except Exception as e:
        l_bledy_wpisu.append((tabela, opis, str(e)))
        return False


def polacz_formy_ochrony(baza0, baza, uzyte, l_bledy_odczytu, l_bledy_wpisu,
                         dozwolone_obreby=None, env_protect=True):
    """Dopisuje do baza0 formy ochrony z `baza` o numerach z `uzyte`
    (MY_INT_NUM kopiowanych wierszy F_SET). Zwraca {stary: nowy} - forma
    nieodczytana/nieistniejąca w źródle nie ma wpisu (wiersz F_SET trzeba
    wtedy pominąć)."""
    remap = {}
    uzyte = {u for u in uzyte if u is not None}
    zrodlo = _formy(baza, l_bledy_odczytu, 'baza źródłowa') if uzyte else {}
    if zrodlo:
        cel = _formy(baza0, l_bledy_odczytu, 'baza docelowa')
        if cel is not None:
            istniejace = {_klucz_formy(k, n): nr
                          for nr, (k, n, _p) in cel.items()}
            nastepny = max([nr for nr in cel if nr is not None] + [-1]) + 1
            for stary in sorted(uzyte):
                if stary not in zrodlo:
                    continue
                kod, nazwa, pole = zrodlo[stary]
                k = _klucz_formy(kod, nazwa)
                if k in istniejace:
                    remap[stary] = istniejace[k]
                    continue
                if _wpisz(baza0,
                          'insert into F_LAND_PROTECT (PROTEC_AREA_CD, '
                          'INT_NUM, LAND_PROTECT_NAME, LAND_PROTECT_AREA) '
                          'values (?, ?, ?, ?);',
                          [kod, nastepny, nazwa, pole], 'F_LAND_PROTECT',
                          'INT_NUM=%d %s %s' % (nastepny, _tekst(kod),
                                                _tekst(nazwa)),
                          l_bledy_wpisu):
                    remap[stary] = istniejace[k] = nastepny
                    nastepny += 1
    if env_protect:
        _polacz_env_protect(baza0, baza, l_bledy_odczytu, l_bledy_wpisu,
                            dozwolone_obreby)
    return remap


def _polacz_env_protect(baza0, baza, l_bledy_odczytu, l_bledy_wpisu,
                        dozwolone_obreby):
    """F_ENV_PROTECT: wiersze źródła (obręb + kod formy), których nie ma w
    docelowej; brak tabeli w źródle (np. PUL) - bez komunikatu."""
    kol_z = _kolumny(baza, 'F_ENV_PROTECT')
    kol_c = _kolumny(baza0, 'F_ENV_PROTECT')
    if kol_z is None or kol_c is None:
        return
    duze_z = {k.upper() for k in kol_z}
    duze_c = {k.upper() for k in kol_c}
    kolumny = [k for k in ENV_KOLUMNY if k in duze_z and k in duze_c]
    if kolumny[:5] != ENV_KOLUMNY[:5]:
        return
    sql = 'select ' + ', '.join(kolumny) + ' from F_ENV_PROTECT;'
    zrd = baza.pobierz(sql)
    org = baza0.pobierz(sql)
    if zrd is False or org is False:
        l_bledy_odczytu.append((baza.baza, 'F_ENV_PROTECT',
                                'Nie udało się odczytać tabeli'))
        return

    def klucz(w):
        return tuple(_tekst(x) for x in w[:5])

    istniejace = {klucz(w) for w in org}
    dozwolone = None if dozwolone_obreby is None else {
        tuple(_tekst(y) for y in o) for o in dozwolone_obreby}
    for w in zrd:
        if dozwolone is not None and \
                tuple(_tekst(x) for x in w[:4]) not in dozwolone:
            continue
        if klucz(w) in istniejace:
            continue
        istniejace.add(klucz(w))
        _wpisz(baza0, 'insert into F_ENV_PROTECT (' + ', '.join(kolumny) +
               ') values (' + ', '.join(['?'] * len(kolumny)) + ');',
               list(w), 'F_ENV_PROTECT', 'klucz=' + str(klucz(w)),
               l_bledy_wpisu)
