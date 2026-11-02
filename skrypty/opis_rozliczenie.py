# -*- coding: utf-8 -*-
"""Edytor opisu, zakładka "Rozliczenie powierzchni": użytki wydzielenia jak
w Taksatorze + rozliczenie tylko użytków tego wydzielenia, bez przeliczania
całej bazy (np. po wydzieleniu nowego wydzielenia ze starego).

Rozlicza się użytek, nie wydzielenie (rozliczenie_uzytku.py): liczone są
wszystkie wydzielenia na użytkach wybranego, a SUB_AREA to suma WSZYSTKICH
rekordów wydzielenia - także z użytków, które nie były przeliczane. Geometria
jak w pełnym rozliczeniu: wydzielenia po częściach, przecięcia poniżej 1 m2
pomijane. Nie zastępuje końcowego pełnego rozliczenia: zmiana kształtu innego
wydzielenia na użytku spoza tych nie zostanie tu policzona.
"""
from collections import Counter

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)
from qgis.core import QgsFeatureRequest

from . import opis_ewidencja_dane as dane
from . import rozliczenie_uzytku as ru
from .opis_ewidencja import _ha, _tabela, _wypelnij

KOLUMNY = (('dzialka', 'Nr działki'), ('au', 'Rodzaj użytku'),
           ('klasa', 'Klasa'), ('pow_uzytku', 'Pow. użytku'),
           ('rozliczona', 'Pow. w wydz.'))
MIN_PRZECIECIE = 1  # [m2]
# [ha] - jak w pełnym rozliczeniu (sprawdz_rozlicz_graf)
PROG_NIEROZLICZONEJ = 0.0005
MAX_WIERSZY_PYTANIA = 30


class Plan:
    """Wynik policzenia, jeszcze bez zapisu."""

    def __init__(self):
        self.blad = ''
        self.uwagi = []
        self.klucze = set()      # (działka, nr użytku) do podmiany
        self.rekordy = []        # (działka, nr użytku, aint, pow.)
        self.zmiany = []         # (adres, aint, stara pow., nowa pow.)
        self.zabiegi = {}        # {aint: [(kod, nowa pow.)]}
        self.nierozliczone = []  # (adres, pow. poligonu poza warstwą Ls)


def _tekst(wartosc):
    # puste pole warstwy to pusty QVariant, nie None (str() dałoby 'NULL')
    if wartosc is None or (hasattr(wartosc, 'isNull') and wartosc.isNull()):
        return ''
    return str(wartosc).strip()


def _poprawna(geom):
    return geom if geom.isGeosValid() else geom.makeValid()


def _czesci(geom):
    return geom.asGeometryCollection() if geom.isMultipart() else [geom]


def _powierzchnie_na_uzytku(ls_geom, lyr_wydz):
    """{ADR_LES: pow. graficzna [ha]} wydzieleń na użytku - jak przecięcie
    w pełnym rozliczeniu."""
    wyn = {}
    zapytanie = QgsFeatureRequest().setFilterRect(ls_geom.boundingBox())
    for f in lyr_wydz.getFeatures(zapytanie):
        if not f.hasGeometry():
            continue
        adr = _tekst(f['ADR_LES'])
        for czesc in _czesci(_poprawna(f.geometry())):
            pole = czesc.intersection(ls_geom).area()
            if pole >= MIN_PRZECIECIE:
                wyn[adr] = round(wyn.get(adr, 0) + pole / 10000, 4)
    return wyn


def zaplanuj(lyr_wydz, lyr_ls, baza, adr, wydz):
    """Plan rozliczenia użytków wydzielenia `adr`. wydz: {ADR_LES: aint}."""
    plan = Plan()
    if lyr_wydz.crs() != lyr_ls.crs():
        plan.blad = 'Warstwy wydzieleń i Ls mają różne układy współrzędnych.'
        return plan
    aint = wydz[adr]
    cur = baza.cur

    wyr = '"ADR_LES" = \'' + adr.strip().replace("'", "''") + "'"
    poligony = [_poprawna(f.geometry()) for f in lyr_wydz.getFeatures(
        QgsFeatureRequest().setFilterExpression(wyr)) if f.hasGeometry()]
    if not poligony:
        plan.blad = 'Wydzielenie nie ma poligonu na warstwie.'
        return plan

    # użytki z bazy: LANDID -> (działka, nr użytku, pow. rejestrowa)
    uzytki, landid_uz = {}, {}
    for x in baza.uzytki():
        landid = f'{x[12]}.{x[9]}{_tekst(x[10])}'
        uzytki[landid] = (x[6], x[8], x[11])
        landid_uz[(x[6], x[8])] = landid

    # geometria Ls: LANDID -> geometria; zdublowany LANDID jak w pełnym
    # rozliczeniu blokuje liczenie
    ls_geom, dubli = {}, set()
    for f in lyr_ls.getFeatures():
        landid = _tekst(f['LANDID'])
        if not f.hasGeometry() or not landid:
            continue
        if landid in ls_geom:
            dubli.add(landid)
        ls_geom[landid] = _poprawna(f.geometry())

    rekordy_bazy = [tuple(w) for w in cur.execute(
        'select PARCEL_INT_NUM, SHAPE_NR, ARODES_INT_NUM, AROD_LAND_USE_AREA '
        'from F_AROD_LAND_USE').fetchall()]

    # użytki, których dotyczy: pod poligonem + dotychczas rozliczone
    dotyczy = {uz for uz, g in ls_geom.items() if any(
        p.boundingBox().intersects(g.boundingBox())
        and p.intersection(g).area() >= MIN_PRZECIECIE for p in poligony)}
    dotyczy |= {landid_uz[(r[0], r[1])] for r in rekordy_bazy
                if r[2] == aint and (r[0], r[1]) in landid_uz}
    if not dotyczy:
        plan.blad = 'Wydzielenie nie leży na żadnym użytku warstwy Ls.'
        return plan
    zdublowane = sorted(dotyczy & dubli)
    if zdublowane:
        plan.blad = ('Zdublowane użytki na warstwie Ls: ' +
                     ', '.join(zdublowane))
        return plan

    na_uzytkach = {adr.strip()}
    for uz in sorted(dotyczy):
        if uz not in uzytki:
            plan.uwagi.append(f'Użytku {uz} nie ma w bazie - pominięty.')
            continue
        pid, sh, pow_rej = uzytki[uz]
        plan.klucze.add((pid, sh))
        if uz not in ls_geom:
            plan.uwagi.append(f'Użytku {uz} nie ma na warstwie Ls - jego '
                              'dotychczasowe rozliczenie zostanie usunięte.')
            continue
        pow_na_uz = _powierzchnie_na_uzytku(ls_geom[uz], lyr_wydz)
        na_uzytkach |= set(pow_na_uz)
        if not pow_na_uz:
            continue
        pow_graf = round(ls_geom[uz].area() / 10000, 4)
        for ad, pow_ha in ru.rozlicz_uzytek(pow_na_uz, pow_rej, pow_graf):
            if ad in wydz:
                plan.rekordy.append((pid, sh, wydz[ad], pow_ha))
            else:
                plan.uwagi.append(f'Na użytku {uz} leży poligon '
                                  f'{ad or "bez adresu"}, którego nie ma '
                                  'w bazie.')

    duble = _zdublowane_adresy(lyr_wydz) & na_uzytkach
    if duble:
        plan.blad = ('Kilka poligonów z tym samym adresem na warstwie '
                     'wydzieleń - połącz je w multipoligony albo popraw adres: '
                     + ', '.join(sorted(duble)))
        return plan

    _policz_zmiany(plan, rekordy_bazy, wydz, cur)
    _policz_nierozliczone(plan, lyr_wydz, ls_geom)
    return plan


def _zdublowane_adresy(lyr_wydz):
    zapytanie = QgsFeatureRequest().setFlags(
        QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            ['ADR_LES'], lyr_wydz.fields())
    licznik = Counter(_tekst(f['ADR_LES'])
                      for f in lyr_wydz.getFeatures(zapytanie))
    return {a for a, n in licznik.items() if a and n > 1}


def _policz_nierozliczone(plan, lyr_wydz, ls_geom):
    """Część poligonu liczonego wydzielenia poza warstwą Ls (dziura, błąd
    topologii) - te metry nie mają rekordu, więc SUB_AREA wyjdzie za małe."""
    adresy = {a.strip() for a, _i, _s, _n in plan.zmiany}
    for f in lyr_wydz.getFeatures():
        adr = _tekst(f['ADR_LES'])
        if adr not in adresy or not f.hasGeometry():
            continue
        geom = _poprawna(f.geometry())
        reszta = round(geom.area() / 10000, 4)
        for czesc in _czesci(geom):
            ramka = czesc.boundingBox()
            for g in ls_geom.values():
                if ramka.intersects(g.boundingBox()):
                    pole = czesc.intersection(g).area()
                    if pole >= MIN_PRZECIECIE:
                        reszta = round(reszta - pole / 10000, 4)
        if reszta > PROG_NIEROZLICZONEJ:
            plan.nierozliczone.append((adr, reszta))


def _policz_zmiany(plan, rekordy_bazy, wydz, cur):
    """SUB_AREA dotkniętych wydzieleń = suma wszystkich ich rekordów."""
    zostaja = [r for r in rekordy_bazy if (r[0], r[1]) not in plan.klucze]
    dotkniete = {r[2] for r in plan.rekordy} | {
        r[2] for r in rekordy_bazy if (r[0], r[1]) in plan.klucze}
    sumy = dict.fromkeys(dotkniete, 0.0)
    for r in zostaja + plan.rekordy:
        if r[2] in sumy:
            sumy[r[2]] += float(r[3] or 0)
    adresy = {a: ad for ad, a in wydz.items()}
    stare = {r[0]: r[1] for r in cur.execute(
        'select ARODES_INT_NUM, SUB_AREA from F_SUBAREA').fetchall()}
    for a in sorted(dotkniete, key=lambda x: adresy.get(x, '')):
        if a not in adresy or a not in stare:
            continue
        nowa = round(sumy[a], 4)
        stara = None if stare[a] is None else round(float(stare[a]), 4)
        plan.zmiany.append((adresy[a], a, stara, nowa))
        if stara != nowa:
            zabiegi = [(_tekst(z[0]), z[1], z[2]) for z in cur.execute(
                'select MEASURE_CD, CUTTING_AREA, PROC_AREA from F_AROD_CUE '
                'where ARODES_INT_NUM = ?', (a,)).fetchall()]
            plan.zabiegi[a] = ru.zabiegi_po_zmianie(zabiegi, stara or 0, nowa)


def wykonaj(plan, baza):
    """Zapis w jednej transakcji. Pozyskanie zmienionych zabiegów czyszczone
    (policzy je TPU), jak przy kopiowaniu opisu. Błąd - rollback i wyjątek."""
    cur = baza.cur
    try:
        for pid, sh in plan.klucze:
            cur.execute('delete from F_AROD_LAND_USE where PARCEL_INT_NUM = ? '
                        'and SHAPE_NR = ?', (pid, sh))
        for pid, sh, aint, pow_ha in plan.rekordy:
            cur.execute(
                'insert into F_AROD_LAND_USE (PARCEL_INT_NUM, SHAPE_NR, '
                'ARODES_INT_NUM, AROD_LAND_USE_AREA, LARGE_TIMBER_VALUE) '
                'values (?, ?, ?, ?, 0)', (pid, sh, aint, pow_ha))
        for _adr, aint, stara, nowa in plan.zmiany:
            if stara != nowa:
                cur.execute('update F_SUBAREA set SUB_AREA = ? where '
                            'ARODES_INT_NUM = ?', (nowa, aint))
            for kod, pow_ha in plan.zabiegi.get(aint, []):
                cur.execute(
                    'update F_AROD_CUE set CUTTING_AREA = ?, '
                    'LARGE_TIMBER_VALUE = NULL where ARODES_INT_NUM = ? '
                    'and MEASURE_CD = ?', (pow_ha, aint, kod))
        baza.con.commit()
    except Exception:
        baza.con.rollback()
        raise


def tresc_pytania(plan, czytelny, niezgodnosc=''):
    """Krótkie pytanie przed rozliczeniem. czytelny(adres) -> tekst,
    niezgodnosc - skrót niezgodności całej warstwy z bazą (nie blokuje, nie
    zmienia wyniku tego rozliczenia)."""
    def pow_tekst(v):
        return 'brak' if v is None else _ha(v)

    bez_zmian = [f'{czytelny(a)}   {_ha(n)} ha'
                 for a, _i, st, n in plan.zmiany if st == n]
    zmiany = [f'{czytelny(a)}   {pow_tekst(st)} -> {_ha(n)} ha'
              for a, _i, st, n in plan.zmiany if st != n]
    # skracana tylko pierwsza grupa - zmiany trzeba móc sprawdzić wszystkie
    if len(bez_zmian) > MAX_WIERSZY_PYTANIA:
        bez_zmian = bez_zmian[:MAX_WIERSZY_PYTANIA] + \
            [f'... i {len(bez_zmian) - MAX_WIERSZY_PYTANIA} kolejnych']
    grupy = []
    if bez_zmian:
        grupy.append('Bez zmiany powierzchni:\n' + '\n'.join(bez_zmian))
    grupy.append('Zmiana powierzchni:\n' + '\n'.join(zmiany) if zmiany
                 else 'Powierzchnie bez zmian.')
    tekst = ('Rozliczyć powierzchnię w następujących wydzieleniach?\n\n' +
             '\n\n'.join(grupy))
    ile = sum(len(v) for v in plan.zabiegi.values())
    if ile:
        tekst += f'\n\nZmieni się też powierzchnia zabiegów: {ile}.'
    if plan.nierozliczone:
        tekst += '\n\n' + '\n'.join(
            f'{czytelny(a)}: nierozliczone {_ha(h)} ha'
            for a, h in plan.nierozliczone[:10])
    if plan.uwagi:
        tekst += '\n\nUwagi:\n' + '\n'.join(plan.uwagi[:10])
    if niezgodnosc:
        tekst += f'\n\nWarstwa i baza są niezgodne: {niezgodnosc}'
    return tekst


class WidokRozliczenia(QWidget):
    """Treść zakładki: tabela jak w Taksatorze i przycisk rozliczenia."""

    def __init__(self, karta):
        super().__init__(karta)
        self.karta = karta

        uklad = QVBoxLayout(self)
        uklad.setContentsMargins(4, 6, 4, 4)
        uklad.addWidget(QLabel('<b>Dane ewidencyjne</b>'))
        h = QHBoxLayout()
        self.tabela = _tabela(KOLUMNY)
        h.addWidget(self.tabela, 1)
        prawa = QVBoxLayout()
        wiersz = QHBoxLayout()
        wiersz.addWidget(QLabel('Powierzchnia'))
        self.ed_pow = QLineEdit()
        self.ed_pow.setReadOnly(True)
        self.ed_pow.setAlignment(Qt.AlignRight)
        self.ed_pow.setFixedWidth(80)
        self.ed_pow.setToolTip('Powierzchnia wydzielenia w bazie (SUB_AREA)')
        wiersz.addWidget(self.ed_pow)
        prawa.addLayout(wiersz)
        self.btn_rozlicz = QPushButton('Rozlicz powierzchnię użytków')
        self.btn_rozlicz.setToolTip(
            'Przelicza użytki tego wydzielenia razem ze wszystkimi '
            'wydzieleniami na nich leżącymi i powierzchnię ich zabiegów '
            '(procent zostaje, pozyskanie do przeliczenia w TPU). Reszta bazy '
            'bez zmian. Przed oddaniem i tak potrzebne jest pełne rozliczenie.')
        self.btn_rozlicz.clicked.connect(karta.rozlicz_uzytki)
        prawa.addWidget(self.btn_rozlicz)
        self.lbl_uwaga = QLabel()
        self.lbl_uwaga.setWordWrap(True)
        self.lbl_uwaga.setMaximumWidth(240)
        self.lbl_uwaga.setStyleSheet('color: #b36b00;')
        prawa.addWidget(self.lbl_uwaga)
        prawa.addStretch(1)
        h.addLayout(prawa)
        uklad.addLayout(h)

    def aktywuj(self, aint):
        """Tabela z bazy dla wydzielenia (None - pusta)."""
        wiersze, uwaga = [], ''
        try:
            if aint is not None:
                wiersze = dane.wczytaj(self.karta.baza.cur) \
                    .dzialki_wydzielenia(aint)
        except Exception as e:
            uwaga = f'Nie udało się odczytać użytków: {e}'
        _wypelnij(self.tabela, KOLUMNY, wiersze)
        if not uwaga and aint is not None and not wiersze:
            uwaga = 'Wydzielenie nie jest rozliczone.'
        if aint is None and self.karta.dane is not None:
            uwaga = 'Rozliczenie po zapisaniu nowego wydzielenia.'
        self.lbl_uwaga.setText(uwaga)
        self.ed_pow.setText(_ha(self.karta.pow_wydz) if aint is not None
                            else '')
        self.btn_rozlicz.setEnabled(
            aint is not None and not self.karta.tylko_odczyt)
