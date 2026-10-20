"""PNSW (powierzchnie nie tworzące wydzielenia) w Edytorze opisu - model,
kontrole i plan zapisu. Bez interfejsu; używane przez opis_taksacyjny.py.

Tabele: F_AROD_SPEC_AREA (ARODES_INT_NUM, AROD_SPAREA_ORDER = nr PNSW w
wydzieleniu, SPECIAL_AREA_CD, LOCATION_CD, SPECIAL_AREA [ha],
SPECIAL_AREA_NUM = 1 jak w "Dopisz PNSW", SPECIAL_AREA_YEAR - nieużywane)
i F_SPECIES_SPAREA (gatunki PNSW: SP_RANK_ORDER, SPECIES_CD, SP_AGE).

Numeracja: nr PNSW się nie zmienia - po usunięciu PNSW ze środka zostaje
dziura, nowy dostaje max + 1 ("Dopisz PNSW" łączy rekordy bazy z warstwą
PNSW po NR_PNSW - przenumerowanie rozjechałoby je z geometrią).
"""
import json

from .opis_warstwy import OSTRZ

POLA_PNSW = ['SPECIAL_AREA_CD', 'LOCATION_CD', 'SPECIAL_AREA']
POLA_GATUNKU_PNSW = ['SPECIES_CD', 'SP_AGE']
# rodzaje z drzewami (odnowione / kępy) - w danych zawsze z gatunkiem
Z_GATUNKIEM = {'D LUKA', 'D PRZEZ', 'KĘPA', 'OD GNIA', 'OD G CZ'}
MAX_WIEK = 300


def _txt(v):
    return '' if v is None else str(v).strip()


def model(pnsw, gatunki):
    """Lista PNSW karty z rekordów F_AROD_SPEC_AREA i F_SPECIES_SPAREA
    (słowniki kolumna: wartość); '_BAZA' - PNSW jest w bazie."""
    wyn = []
    for p in sorted(pnsw, key=lambda w: w['AROD_SPAREA_ORDER'] or 0):
        nr = p['AROD_SPAREA_ORDER']
        gat = sorted((g for g in gatunki if g['AROD_SPAREA_ORDER'] == nr),
                     key=lambda g: g['SP_RANK_ORDER'] or 0)
        pow_ = p.get('SPECIAL_AREA')
        wyn.append({
            'NR': int(nr),
            'SPECIAL_AREA_CD': _txt(p.get('SPECIAL_AREA_CD')),
            'LOCATION_CD': _txt(p.get('LOCATION_CD')),
            'SPECIAL_AREA': None if pow_ is None else round(float(pow_), 4),
            'gatunki': [{'SPECIES_CD': _txt(g.get('SPECIES_CD')),
                         'SP_AGE': None if g.get('SP_AGE') is None
                         else int(g['SP_AGE'])} for g in gat],
            '_BAZA': True,
        })
    return wyn


def nastepny_nr(nowe, stare):
    """Nr nowego PNSW: max z bieżących i z bazy + 1 (numer usuniętego,
    a jeszcze niezapisanego PNSW nie jest używany ponownie)."""
    return max([p['NR'] for p in list(nowe) + list(stare)] + [0]) + 1


def waliduj(pnsw, pow_wydz):
    """{(indeks PNSW, pole): [(OSTRZ, kod, tekst)]} - same ostrzeżenia
    (zapis możliwy); pole gatunku: ('SPECIES_CD' | 'SP_AGE', nr gatunku)."""
    wyn = {}

    def dodaj(klucz, kod, tekst):
        wyn.setdefault(klucz, []).append((OSTRZ, kod, tekst))

    for pi, p in enumerate(pnsw):
        if p['SPECIAL_AREA'] is None:
            dodaj((pi, 'SPECIAL_AREA'), 'PNSW1', 'Brak powierzchni PNSW')
        if not p['LOCATION_CD']:
            dodaj((pi, 'LOCATION_CD'), 'PNSW2', 'Brak położenia PNSW')
        if p['SPECIAL_AREA_CD'] in Z_GATUNKIEM and not p['gatunki']:
            dodaj((pi, ('SPECIES_CD', 0)), 'PNSW3',
                  f'{p["SPECIAL_AREA_CD"]} - brak gatunku')
        for gi, g in enumerate(p['gatunki']):
            if g['SP_AGE'] is None:
                dodaj((pi, ('SP_AGE', gi)), 'PNSW4',
                      f'{g["SPECIES_CD"]} - brak wieku')
    suma = round(sum(p['SPECIAL_AREA'] or 0 for p in pnsw), 4)
    if pow_wydz and suma > pow_wydz + 0.00005:
        for pi, p in enumerate(pnsw):
            dodaj((pi, 'SPECIAL_AREA'), 'PNSW5',
                  f'Suma pow. PNSW {suma} ha > pow. wydzielenia {pow_wydz} ha')
    return wyn


def liczba_ostrzezen(walidacja):
    return sum(len(v) for v in walidacja.values())


def _rekord(p):
    return [None if p[k] in ('', None) else p[k] for k in POLA_PNSW]


def _gatunki_ops(aint, p):
    return [('insert into F_SPECIES_SPAREA (ARODES_INT_NUM, '
             'AROD_SPAREA_ORDER, SP_RANK_ORDER, SPECIES_CD, SP_AGE) '
             'values (?, ?, ?, ?, ?)',
             (aint, p['NR'], r, g['SPECIES_CD'], g['SP_AGE']))
            for r, g in enumerate(p['gatunki'], 1)]


def plan_zapisu(aint, stare, nowe):
    """[(sql, parametry)] zmian PNSW wydzielenia (w transakcji zapisu
    karty). Niezmienione PNSW - bez zapytań; zmienione gatunki PNSW -
    usunięcie i wpis od nowa (rangi = kolejność)."""
    ops = []
    stare_nr = {p['NR']: p for p in stare}
    nowe_nr = {p['NR']: p for p in nowe}
    for nr in stare_nr:
        if nr not in nowe_nr:
            ops.append(('delete from F_SPECIES_SPAREA where ARODES_INT_NUM = ? '
                        'and AROD_SPAREA_ORDER = ?', (aint, nr)))
            ops.append(('delete from F_AROD_SPEC_AREA where ARODES_INT_NUM = ? '
                        'and AROD_SPAREA_ORDER = ?', (aint, nr)))
    for p in nowe:
        s = stare_nr.get(p['NR'])
        if s is None:
            ops.append(('insert into F_AROD_SPEC_AREA (ARODES_INT_NUM, '
                        'AROD_SPAREA_ORDER, ' + ', '.join(POLA_PNSW) +
                        ', SPECIAL_AREA_NUM) values (?, ?, ?, ?, ?, 1)',
                        (aint, p['NR'], *_rekord(p))))
            ops += _gatunki_ops(aint, p)
            continue
        if _rekord(p) != _rekord(s):
            ops.append(('update F_AROD_SPEC_AREA set ' +
                        ', '.join(f'{k} = ?' for k in POLA_PNSW) +
                        ' where ARODES_INT_NUM = ? and AROD_SPAREA_ORDER = ?',
                        (*_rekord(p), aint, p['NR'])))
        if p['gatunki'] != s['gatunki']:
            ops.append(('delete from F_SPECIES_SPAREA where ARODES_INT_NUM = ? '
                        'and AROD_SPAREA_ORDER = ?', (aint, p['NR'])))
            ops += _gatunki_ops(aint, p)
    return ops


def do_dziennika(lista):
    """PNSW jako JSON do dziennika edycji (bez pól pomocniczych)."""
    return json.dumps([{k: v for k, v in p.items() if k != '_BAZA'}
                       for p in lista], ensure_ascii=False, default=str)
