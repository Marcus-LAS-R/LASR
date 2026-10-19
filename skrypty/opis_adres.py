"""Adres leśny w Edytorze opisu - składanie z okien paska adresu karty,
wolna litera wydzielenia, kontrola i plan zapisu w F_ARODES (nowe
wydzielenie, przeadresowanie). Bez interfejsu; używane przez
opis_taksacyjny.py.

Adres UPUL (25 znaków): COUNTY_L[0] DISTRICT[1:3] MUNICIP[3:6]
COMMUNITY[6:10] - GRP[11:13] ODDZ[13:17] - WYDZ[18:22] - SUFIKS[23:25].
Prefiks [0:6] (gmina) jest stały - w karcie edytowalne są obręb, grupa,
oddział i wydzielenie. Hierarchia F_ARODES na wydzielenie: OBRĘB [:6],
L-CTWO [:10], ODDZ [:17], WYDZIEL (ORDER_KEY i kolejność wpisu jak w
baza_dopisz_wydz.DopiszWydzielenia).
"""
import re

GRUPA_NOWEGO = '10'  # grupa nowego wydzielenia (prywatni)
CZESCI = ('obreb', 'grp', 'oddz', 'wydz')


def skladowe(adr):
    """{'obreb', 'grp', 'oddz', 'wydz'} z adresu (bez spacji) albo None."""
    if not adr or len(adr) < 22:
        return None
    return {'obreb': adr[6:10].strip(), 'grp': adr[11:13].strip(),
            'oddz': adr[13:17].strip(), 'wydz': adr[18:22].strip()}


def zloz(prefiks, obreb, grp, oddz, wydz):
    """Adres z części (jak shp_adr_les.zbuduj_adres): grupa pusta -> dwie
    spacje, oddział i wydzielenie wyrównane spacjami do 4 znaków."""
    grp = grp if len(grp) == 2 else '  '
    return f'{prefiks}{obreb}-{grp}{oddz.ljust(4)}-{wydz.ljust(4)}-00'


def normalizuj(czesc, tekst):
    """Postać zapisywana w adresie: obręb 4 cyfry, grupa 2 cyfry (z
    zerami), oddział bez zer wiodących, wydzielenie małymi literami."""
    tekst = (tekst or '').strip()
    if czesc == 'obreb' and tekst.isdigit():
        return tekst.zfill(4)
    if czesc == 'grp' and tekst.isdigit():
        return tekst.zfill(2)
    if czesc == 'oddz' and tekst.isdigit() and int(tekst):
        return str(int(tekst))
    if czesc == 'wydz':
        return tekst.lower()
    return tekst


def wolna_litera(litery, adresy_wydz, prefiks, obreb, oddz, pomin=None):
    """Pierwsza litera z listy niezajęta w oddziale obrębu (we wszystkich
    grupach - bez dwóch "1-b" w różnych grupach); pomin - własny adres
    przeadresowywanego wydzielenia. None, gdy lista się skończyła."""
    poczatek = prefiks + obreb
    zajete = {a[18:22].strip() for a in adresy_wydz
              if a != pomin and a[:10] == poczatek
              and a[13:17].strip() == oddz}
    return next((x for x in litery if x not in zajete), None)


def docelowy(prefiks, czesci, litery, adresy, adres_bazy=None):
    """(adres, błąd, litera_auto) z okien paska adresu.

    czesci - {'obreb', 'grp', 'oddz', 'wydz'} (pusty 'wydz' = następna
    wolna litera), adresy - {ADRESS_FOREST: ARODES_TYP_CD} z F_ARODES,
    adres_bazy - obecny adres wydzielenia (None - nowe). Błąd = tekst dla
    użytkownika (adres wtedy None)."""
    c = {k: normalizuj(k, czesci.get(k, '')) for k in CZESCI}
    if not re.fullmatch(r'\d{4}', c['obreb']):
        return None, 'obręb: 4 cyfry', None
    if c['grp'] and not re.fullmatch(r'\d{2}', c['grp']):
        return None, 'grupa: 2 cyfry albo pusta', None
    if not re.fullmatch(r'\d{1,4}', c['oddz']) or not int(c['oddz']):
        return None, 'oddział: liczba 1-9999', None
    if c['wydz'] and not re.fullmatch(r'[a-z]{1,2}', c['wydz']):
        return None, 'wydzielenie: 1-2 małe litery', None
    if not any(a[:10] == prefiks + c['obreb'] for a in adresy):
        return None, f'obręb {c["obreb"]} nie istnieje w bazie', None
    auto = None
    if not c['wydz']:
        wydz_bazy = [a for a, t in adresy.items() if t == 'WYDZIEL']
        auto = wolna_litera(litery, wydz_bazy, prefiks, c['obreb'],
                            c['oddz'], pomin=adres_bazy)
        if auto is None:
            return None, 'brak wolnej litery w oddziale', None
    adr = zloz(prefiks, c['obreb'], c['grp'], c['oddz'], c['wydz'] or auto)
    if adr != adres_bazy and adr in adresy:
        return None, f'adres zajęty w bazie: {adr}', auto
    return adr, '', auto


def brakujace_poziomy(adr, adresy, dopisz):
    """Operacje [ADRESS_FOREST, ARODES_TYP_CD, ORDER_KEY, ADRESS_VALID]
    poziomów nad wydzieleniem (ODDZ, OBRĘB, L-CTWO - kolejność jak w
    DopiszWydzielenia), których nie ma w F_ARODES; dopisz - obiekt
    DopiszWydzielenia (stworz_ops_*)."""
    wyn = []
    for f in (dopisz.stworz_ops_oddz, dopisz.stworz_ops_obrebu,
              dopisz.stworz_ops_lctwa):
        op = f(adr)
        if op[0] not in adresy and op[0] not in [o[0] for o in wyn]:
            wyn.append(op)
    return wyn


def puste_poziomy(stary, rekordy):
    """ARODES_INT_NUM poziomów ODDZ / L-CTWO starego adresu, pod którymi
    po przeadresowaniu nie zostało żadne wydzielenie (jak w
    Baza.usun_rekordy). rekordy - [(ADRESS_FOREST, ARODES_INT_NUM,
    ARODES_TYP_CD)] stanu PO zmianie adresu."""
    wyn = []
    if not any(t == 'WYDZIEL' and a[:17] == stary[:17]
               for a, _n, t in rekordy):
        wyn += [n for a, n, t in rekordy
                if t == 'ODDZ' and a[:17] == stary[:17]]
    # leśnictwo tylko wtedy, gdy pod nim nic już nie zostało (także
    # puste oddziały spoza tej zmiany - bez osieroconych rekordów)
    if not any(t != 'L-CTWO' and n not in wyn and a[:10] == stary[:10]
               for a, n, t in rekordy):
        wyn += [n for a, n, t in rekordy
                if t == 'L-CTWO' and a[:10] == stary[:10]]
    return wyn
