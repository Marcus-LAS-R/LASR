"""Silnik "Podmień wybrane zabiegi".

W wybranym zakresie (cała baza / obręby / formy ochrony przyrody)
podmienia w F_AROD_CUE zabiegi wg reguł "źródło -> cel, nowy %" albo
usuwa zabieg (cel = None), a potem poprawia odnowienia tak jak
"Dopisz/sprawdź zabiegi" (zabiegi/wygeneruj.py, zab_dstan_odn_reb):

- rębnia zupełna (IA/IB/IC): ODN-ZRB + PIEL + AGROT,
  pow. = % rębni x pow. wydz.,
- rębnia częściowa: ODN-ZŁOŻ + PIEL + AGROT,
  pow. = % rębni x pow. wydz. x (1 - odn_cz),
  odn_cz = NAL + PODR + PODS - 0,1 (gdy suma > 0,1),
- PROC_AREA odnowień = pow. odnowienia / pow. wydz. x 100,
- rębnia usunięta / zamieniona na zabieg nie-rębny: odnowienie po rębni
  usuwane, PIEL/AGROT usuwane, chyba że w wydzieleniu zostaje inne
  odnowienie (ODN-LUK, ODN-HAL, POPR, ODN-ZRB przy PŁAZ) - wtedy
  dostają jego powierzchnię.

Odnowienia poprawiane są tylko w wydzieleniach, w których reguła
dotknęła rębni (przed albo po zmianie), i tylko te kody odnowień, które
same nie są źródłem żadnej reguły. Masa (LARGE_TIMBER_VALUE) nie jest
przeliczana - liczona jest w TPU.
"""

import os
from datetime import datetime

from qgis.core import Qgis, QgsMessageLog

from ...baza_zabiegi_sl import ZabiegiSlownik

_ROZMIAR_PORCJI = 200


def _rebnie():
    s = ZabiegiSlownik()
    s.spisy()
    return tuple(x for x in s.rebnieSpis if x != 'PŁAZ')


REBNIE = _rebnie()
REBNIE_ZUPELNE = ('IA', 'IB', 'IC')
MLODE = ('TP', 'TW', 'CP-P', 'CP', 'CW')
TRZEBIEZE = ('TP', 'TW', 'CP-P')
ODN_REBNI = ('ODN-ZRB', 'ODN-ZŁOŻ')
ODN_INNE = ('ODN-LUK', 'ODN-HAL', 'POPR')
ZAB_ODN = ('PIEL', 'AGROT')


def _txt(w):
    return '' if w is None else str(w).strip()


def _num(w):
    try:
        return float(w) if w is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _porcje(wartosci, rozmiar=_ROZMIAR_PORCJI):
    wartosci = sorted(wartosci)
    for i in range(0, len(wartosci), rozmiar):
        yield wartosci[i:i + rozmiar]


def _pow(x):
    return f'{x:.4f}'.replace('.', ',')


# --------------------------------------------------------------------------
# odczyt słowników do dialogu
# --------------------------------------------------------------------------

def pobierz_obreby(baza):
    """[(klucz (DISTRICT, MUNICIP, COMMUNITY), opis)] z F_COMMUNITY."""
    w = baza.pobierz(
        'select DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, COMMUNITY_NAME '
        'from F_COMMUNITY order by MUNICIPALITY_CD, COMMUNITY_CD;') or []
    return [((_txt(d), _txt(m), _txt(c)), f'{_txt(m)}.{_txt(c)} {_txt(n)}')
            for d, m, c, n in w]


def pobierz_formy_ochrony(baza):
    """[(INT_NUM, opis)] z F_LAND_PROTECT, z liczbą wydzieleń (F_SET)."""
    w = baza.pobierz(
        'select L.INT_NUM, L.PROTEC_AREA_CD, L.LAND_PROTECT_NAME, '
        'count(S.ARODES_INT_NUM) from F_LAND_PROTECT L left join F_SET S '
        'on S.MY_INT_NUM = L.INT_NUM group by L.INT_NUM, L.PROTEC_AREA_CD, '
        'L.LAND_PROTECT_NAME order by L.INT_NUM;') or []
    return [(nr, f'{_txt(kod)} - {_txt(nazwa)} (wydz.: {ile})')
            for nr, kod, nazwa, ile in w]


def pobierz_zabiegi_w_bazie(baza):
    """{MEASURE_CD: liczba wpisów} z F_AROD_CUE."""
    w = baza.pobierz(
        'select MEASURE_CD, count(*) from F_AROD_CUE group by MEASURE_CD;'
    ) or []
    return {_txt(k): n for k, n in w if _txt(k)}


def pobierz_slownik_zabiegow(baza):
    """Kody zabiegów ze słownika F_MEASURE (posortowane)."""
    w = baza.pobierz('select measure_cd from F_MEASURE;') or []
    return sorted({_txt(x[0]) for x in w if _txt(x[0])})


# --------------------------------------------------------------------------
# zakres
# --------------------------------------------------------------------------

def wydzielenia_w_zakresie(baza, zakres, wybrane):
    """{ARODES_INT_NUM: ADRESS_FOREST} wydzieleń (WYDZIEL) w zakresie:
    'baza' - wszystkie, 'obreby' - wybrane klucze (DISTRICT, MUNICIP,
    COMMUNITY) wg adresu leśnego adr[1:10], 'fop' - wydzielenia
    przypisane w F_SET do wybranych F_LAND_PROTECT.INT_NUM."""
    w = baza.pobierz(
        "select ARODES_INT_NUM, ADRESS_FOREST from F_ARODES "
        "where ARODES_TYP_CD = 'WYDZIEL';") or []
    wydz = {a: _txt(adr) for a, adr in w}

    if zakres == 'obreby':
        wybrane = set(wybrane)
        return {a: adr for a, adr in wydz.items()
                if (adr[1:3], adr[3:6], adr[6:10]) in wybrane}

    if zakres == 'fop':
        aids = set()
        for porcja in _porcje(set(wybrane)):
            znaki = ','.join('?' for _ in porcja)
            for (a,) in baza.cur.execute(
                    'select distinct ARODES_INT_NUM from F_SET where '
                    'MY_INT_NUM in (' + znaki + ')', list(porcja)).fetchall():
                aids.add(a)
        return {a: adr for a, adr in wydz.items() if a in aids}

    return wydz


# --------------------------------------------------------------------------
# model wydzielenia
# --------------------------------------------------------------------------

class Wpis:
    """Wiersz F_AROD_CUE w pamięci."""

    def __init__(self, cd, pow_=0.0, proc_area=None, perc=None, rank=0,
                 nowy=False):
        self.cd_bazy = None if nowy else cd  # kod w bazie (przed zmianą)
        self.cd = cd
        self.pow = pow_
        self.proc_area = proc_area
        self.perc = perc
        self.rank = rank
        self.nowy = nowy
        self.usuniety = False
        self.zmiany = set()  # zmienione pola: cd, pow, proc_area, perc

    def ustaw(self, pole, wartosc):
        if getattr(self, pole) != wartosc:
            setattr(self, pole, wartosc)
            self.zmiany.add(pole)

    def opis(self):
        tekst = f'{self.cd} {_pow(self.pow)} ha'
        if self.cd in REBNIE or self.cd in MLODE:
            tekst += f' {self.perc if self.perc is not None else "-"}%'
        return tekst


class PlanWydzielenia:
    def __init__(self, aid, adr, pow_wydz, odn_cz, info):
        self.aid = aid
        self.adr = adr
        self.pow_wydz = pow_wydz
        self.odn_cz = odn_cz
        self.info = info
        self.wpisy = []
        self.przed = ''
        self.uwagi = []      # ostrzeżenia do raportu
        self.pominiete = ''  # powód pominięcia (nic nie zapisujemy)
        self.info_nowe = None

    def aktywne(self):
        return [w for w in self.wpisy if not w.usuniety]

    def znajdz(self, cd):
        for w in self.aktywne():
            if w.cd == cd:
                return w
        return None

    def ma_zmiany(self):
        return any(w.nowy or w.usuniety or w.zmiany for w in self.wpisy)

    def po(self):
        return ', '.join(w.opis() for w in sorted(
            self.aktywne(), key=lambda x: x.rank))


def _wczytaj(baza, aids):
    """Zwraca {aid: (pow_wydz, info, odn_cz, [wiersze cue])}."""
    sub, piet, cue = {}, {}, {}
    for porcja in _porcje(aids):
        znaki = ','.join('?' for _ in porcja)
        for a, pow_, info in baza.cur.execute(
                'select ARODES_INT_NUM, SUB_AREA, SUBAREA_INFO from F_SUBAREA '
                'where ARODES_INT_NUM in (' + znaki + ')', list(porcja)):
            sub[a] = (round(_num(pow_), 4), _txt(info))
        for a, st, ind in baza.cur.execute(
                "select ARODES_INT_NUM, STOREY_CD, STANDDENSITY_INDEX from "
                "F_AROD_STOREY where STOREY_CD in ('NAL', 'PODR', 'PODS') and "
                "ARODES_INT_NUM in (" + znaki + ")", list(porcja)):
            # jak Wydzielenie.o_pod_nal - zaokrąglenie do 0,1
            piet[a] = piet.get(a, 0.0) + round(_num(ind), 1)
        for row in baza.cur.execute(
                'select ARODES_INT_NUM, MEASURE_CD, CUTTING_AREA, PROC_AREA, '
                'LARGE_TIMBER_PERC, CUE_RANK_ORDER from F_AROD_CUE where '
                'ARODES_INT_NUM in (' + znaki + ')', list(porcja)):
            cue.setdefault(row[0], []).append(row[1:])

    wynik = {}
    for a in aids:
        pow_wydz, info = sub.get(a, (0.0, ''))
        np_sum = piet.get(a, 0.0)
        odn_cz = np_sum - 0.1 if np_sum > 0.1 else 0.0
        wynik[a] = (pow_wydz, info, odn_cz, cue.get(a, []))
    return wynik


# --------------------------------------------------------------------------
# planowanie zmian
# --------------------------------------------------------------------------

def zaplanuj(baza, wydzielenia, reguly, uwaga=''):
    """Buduje plan zmian bez zapisu do bazy.

    wydzielenia - {aid: adres} (wydzielenia_w_zakresie),
    reguly - [(zrodlo, cel albo None = usuń, procent albo None)],
    uwaga - tekst dopisywany na końcu SUBAREA_INFO zmienionych wydzieleń.

    Zwraca listę PlanWydzielenia dla wydzieleń, w których jest choć jeden
    zabieg źródłowy (także pominiętych - z powodem w .pominiete)."""
    sl_reg = {z: (c, p) for z, c, p in reguly}
    dane = _wczytaj(baza, list(wydzielenia))
    plany = []
    for aid in sorted(wydzielenia, key=lambda a: wydzielenia[a]):
        pow_wydz, info, odn_cz, wiersze = dane[aid]
        kody = [_txt(r[0]) for r in wiersze]
        if not any(k in sl_reg for k in kody):
            continue
        plan = PlanWydzielenia(aid, wydzielenia[aid], pow_wydz, odn_cz, info)
        for cd, pow_, proc_area, perc, rank in wiersze:
            plan.wpisy.append(Wpis(
                _txt(cd), round(_num(pow_), 4),
                None if proc_area is None else _num(proc_area),
                None if perc is None else _num(perc), rank or 0))
        plan.przed = plan.po()
        _zaplanuj_wydzielenie(plan, sl_reg, uwaga)
        plany.append(plan)
    return plany


def _zaplanuj_wydzielenie(plan, sl_reg, uwaga):  # noqa
    kody = [w.cd for w in plan.wpisy]
    dubel = sorted({k for k in kody if kody.count(k) > 1})
    if dubel:
        plan.pominiete = 'zdublowany zabieg w bazie: ' + ', '.join(dubel)
        return
    if plan.pow_wydz <= 0:
        plan.pominiete = 'brak powierzchni wydzielenia (F_SUBAREA)'
        return

    # --- konflikty kodów po podmianie ---
    po_zmianie = []
    for w in plan.wpisy:
        if w.cd in sl_reg:
            cel = sl_reg[w.cd][0]
            if cel is not None:
                po_zmianie.append(cel)
        else:
            po_zmianie.append(w.cd)
    konfl = sorted({k for k in po_zmianie if po_zmianie.count(k) > 1})
    if konfl:
        plan.pominiete = ('zabieg docelowy już jest w wydzieleniu: ' +
                          ', '.join(konfl))
        return

    rebnia_dotknieta = False
    for w in list(plan.wpisy):
        if w.cd not in sl_reg:
            continue
        cel, proc = sl_reg[w.cd]
        zrodlo = w.cd
        if zrodlo in REBNIE or (cel in REBNIE):
            rebnia_dotknieta = True
        if cel is None:
            w.usuniety = True
            continue
        w.ustaw('cd', cel)
        if cel in REBNIE and zrodlo not in REBNIE:
            # np. TP -> rębnia: rębnia na całej powierzchni wydzielenia
            w.ustaw('pow', plan.pow_wydz)
            w.ustaw('proc_area', 100.0)
        if proc is not None:
            w.ustaw('perc', float(proc))
        elif (zrodlo in REBNIE) != (cel in REBNIE):
            plan.uwagi.append(
                f'{zrodlo} -> {cel}: procent bez zmian '
                f'({w.perc if w.perc is not None else "-"}%) - sprawdź')

    if _kolejnosc_zmian_kodu(plan) is None:
        plan.pominiete = 'cykliczna zamiana kodów (np. A <-> B)'
        return

    if rebnia_dotknieta:
        _popraw_odnowienia(plan, set(sl_reg))

    # uwaga już wpisana (np. ponowne uruchomienie) - bez dublowania
    if uwaga and plan.ma_zmiany() and uwaga not in plan.info:
        nowe = (plan.info + ' ' + uwaga) if plan.info else uwaga
        if len(nowe) > 255:
            plan.uwagi.append(
                'uwaga NIE dopisana - pole opisu przekroczyłoby 255 znaków')
        else:
            plan.info_nowe = nowe


def _dodaj(plan, cd, pow_, proc_area):
    rank = max([w.rank for w in plan.wpisy] + [0]) + 1
    w = Wpis(cd, pow_, proc_area, None, rank, nowy=True)
    plan.wpisy.append(w)
    return w


def _ustaw_lub_dodaj(plan, cd, pow_, proc_area):
    w = plan.znajdz(cd)
    if w is None:
        _dodaj(plan, cd, pow_, proc_area)
    else:
        w.ustaw('pow', pow_)
        w.ustaw('proc_area', proc_area)


def _popraw_odnowienia(plan, zrodla_regul):
    """Odnowienie + PIEL + AGROT po rębni - patrz docstring modułu.
    Kodów będących źródłem jakiejś reguły nie rusza (użytkownik
    zdecydował o nich wprost)."""
    pw = plan.pow_wydz
    rebnie = [w for w in plan.aktywne() if w.cd in REBNIE]
    wolne = lambda cd: cd not in zrodla_regul  # noqa: E731

    if len(rebnie) > 1:
        plan.uwagi.append('więcej niż jedna rębnia w wydzieleniu - '
                          'odnowienia nie poprawione')
        return

    if rebnie:
        reb = rebnie[0]
        proc = min(reb.perc if reb.perc else 100.0, 100.0)
        if reb.cd in REBNIE_ZUPELNE:
            odn_cd, odn_inne = 'ODN-ZRB', 'ODN-ZŁOŻ'
            pow_odn = round(pw * proc / 100, 4)
        else:
            odn_cd, odn_inne = 'ODN-ZŁOŻ', 'ODN-ZRB'
            pow_odn = round(pw * proc / 100 * (1 - plan.odn_cz), 4)
        proc_odn = float(round(pow_odn * 100 / pw, 0))

        if [x for x in plan.aktywne() if x.cd in TRZEBIEZE]:
            plan.uwagi.append('rębnia razem z trzebieżą/CP-P - sprawdź')
        inne = sorted(x.cd for x in plan.aktywne() if x.cd in ODN_INNE)
        if inne:
            plan.uwagi.append(
                'przy rębni zostało też ' + ', '.join(inne) + ' - PIEL/AGROT '
                'ustawione wg odnowienia po rębni, sprawdź')

        if wolne(odn_cd):
            stare = plan.znajdz(odn_inne)
            if stare is not None and wolne(odn_inne) and \
                    plan.znajdz(odn_cd) is None:
                stare.ustaw('cd', odn_cd)
            elif stare is not None and wolne(odn_inne):
                stare.usuniety = True
            _ustaw_lub_dodaj(plan, odn_cd, pow_odn, proc_odn)
        for cd in ZAB_ODN:
            if wolne(cd):
                _ustaw_lub_dodaj(plan, cd, pow_odn, proc_odn)
        return

    # --- brak rębni po zmianie: usuń odnowienie po rębni ---
    plaz = plan.znajdz('PŁAZ') is not None
    for cd in ODN_REBNI:
        w = plan.znajdz(cd)
        if w is None or not wolne(cd):
            continue
        if cd == 'ODN-ZRB' and plaz:
            continue  # odnowienie po płazowinie - zostaje
        w.usuniety = True

    inne = [w for w in plan.aktywne() if w.cd in ODN_INNE or
            (w.cd == 'ODN-ZRB' and plaz)]
    for cd in ZAB_ODN:
        w = plan.znajdz(cd)
        if w is None or not wolne(cd):
            continue
        if not inne:
            w.usuniety = True
        else:
            pow_ = round(min(sum(x.pow for x in inne), pw), 4)
            w.ustaw('pow', pow_)
            w.ustaw('proc_area', float(round(pow_ * 100 / pw, 0)))


# --------------------------------------------------------------------------
# zapis
# --------------------------------------------------------------------------

def _kolejnosc_zmian_kodu(plan):
    """Zmiany MEASURE_CD w kolejności bezpiecznej dla bazy (cel nie może
    już istnieć w wydzieleniu w momencie UPDATE). Zwraca listę wpisów albo
    None przy cyklu (np. zamiana A <-> B)."""
    w_bazie = {w.cd_bazy for w in plan.wpisy
               if not w.nowy and not w.usuniety}
    do_zmiany = [w for w in plan.wpisy if not w.nowy and not w.usuniety
                 and 'cd' in w.zmiany]
    kolejnosc = []
    while do_zmiany:
        gotowe = [w for w in do_zmiany if w.cd not in w_bazie]
        if not gotowe:
            return None
        for w in gotowe:
            w_bazie.discard(w.cd_bazy)
            w_bazie.add(w.cd)
            kolejnosc.append(w)
            do_zmiany.remove(w)
    return kolejnosc


def zapisz(baza, plany):
    """Zapisuje plany (bez pominiętych) w jednej transakcji. Zwraca
    (liczba_wydzielen, liczniki) albo None przy błędzie (rollback)."""
    licz = {'zmienione': 0, 'usuniete': 0, 'dodane': 0, 'uwagi': 0}
    zapisane = 0
    try:
        for plan in plany:
            if plan.pominiete or not plan.ma_zmiany():
                continue
            kolejnosc = _kolejnosc_zmian_kodu(plan)
            if kolejnosc is None:
                plan.pominiete = 'cykliczna zamiana kodów (np. A <-> B)'
                continue
            a = plan.aid
            for w in plan.wpisy:
                if w.usuniety and not w.nowy:
                    baza.cur.execute(
                        'DELETE FROM F_AROD_CUE WHERE ARODES_INT_NUM = ? AND '
                        'MEASURE_CD = ?', (a, w.cd_bazy))
                    licz['usuniete'] += 1
            for w in kolejnosc:
                baza.cur.execute(
                    'UPDATE F_AROD_CUE SET MEASURE_CD = ? WHERE '
                    'ARODES_INT_NUM = ? AND MEASURE_CD = ?',
                    (w.cd, a, w.cd_bazy))
            for w in plan.wpisy:
                if w.nowy or w.usuniety or not w.zmiany:
                    continue
                baza.cur.execute(
                    'UPDATE F_AROD_CUE SET CUTTING_AREA = ?, PROC_AREA = ?, '
                    'LARGE_TIMBER_PERC = ? WHERE ARODES_INT_NUM = ? AND '
                    'MEASURE_CD = ?',
                    (w.pow, w.proc_area, w.perc, a, w.cd))
                licz['zmienione'] += 1
            for w in plan.wpisy:
                if not w.nowy or w.usuniety:
                    continue
                # jak Wpisz._dopisz_inne_zabiegi
                baza.cur.execute(
                    "INSERT INTO F_AROD_CUE (ARODES_INT_NUM, MEASURE_CD, "
                    "URGENCY, CUTTING_AREA, CUE_RANK_ORDER, SITE_NR, "
                    "PROC_AREA) VALUES (?, ?, 'N', ?, ?, 0, ?)",
                    (a, w.cd, w.pow, w.rank, w.proc_area))
                licz['dodane'] += 1
            if plan.info_nowe is not None:
                baza.cur.execute(
                    'UPDATE F_SUBAREA SET SUBAREA_INFO = ? WHERE '
                    'ARODES_INT_NUM = ?', (plan.info_nowe, a))
                licz['uwagi'] += 1
            zapisane += 1
        baza.con.commit()
    except Exception as e:
        baza.con.rollback()
        QgsMessageLog.logMessage(
            f'Podmień wybrane zabiegi: błąd zapisu, wycofano wszystkie '
            f'zmiany: {e}', 'Las-R', Qgis.Critical)
        return None
    return zapisane, licz


# --------------------------------------------------------------------------
# raport
# --------------------------------------------------------------------------

def podsumuj(plany):
    zmieniane = [p for p in plany if not p.pominiete and p.ma_zmiany()]
    return {
        'wydzielenia': len(zmieniane),
        'pominiete': len([p for p in plany if p.pominiete]),
        'z_uwagami': len([p for p in zmieniane if p.uwagi]),
    }


def opis_reguly(zrodlo, cel, proc):
    tekst = f'{zrodlo} -> ' + (cel if cel else 'USUŃ')
    if cel and proc is not None:
        tekst += f' ({proc}%)'
    return tekst


def zapisz_raport(katalog, baza_sc, reguly, zakres_opis, uwaga, plany,
                  folder_kopii):
    os.makedirs(katalog, exist_ok=True)
    czas = datetime.now().strftime('%Y%m%dT%H%M%S')
    sc = os.path.join(katalog, f'podmiana_zabiegow_{czas}.txt')
    linie = [
        'PODMIEŃ WYBRANE ZABIEGI',
        f'Baza: {baza_sc}',
        f'Data: {datetime.now():%Y-%m-%d %H:%M}',
        f'Kopia bazy: {folder_kopii}',
        f'Zakres: {zakres_opis}',
        'Reguły: ' + '; '.join(opis_reguly(*r) for r in reguly),
        f'Uwaga dopisywana do opisu: {uwaga or "(brak)"}',
        '',
    ]
    zmienione = [p for p in plany if not p.pominiete and p.ma_zmiany()]
    linie.append(f'ZMIENIONE WYDZIELENIA ({len(zmienione)})')
    linie.append('-' * 70)
    for p in zmienione:
        linie.append(p.adr)
        linie.append(f'    przed: {p.przed}')
        linie.append(f'    po:    {p.po()}')
        for u in p.uwagi:
            linie.append(f'    UWAGA: {u}')
    linie.append('')

    pominiete = [p for p in plany if p.pominiete]
    if pominiete:
        linie.append(f'POMINIĘTE ({len(pominiete)})')
        linie.append('-' * 70)
        for p in pominiete:
            linie.append(f'{p.adr}: {p.pominiete}')
            linie.append(f'    {p.przed}')
        linie.append('')

    linie.append('Masa (LARGE_TIMBER_VALUE) nie była przeliczana - przelicz '
                 'w TPU.')
    with open(sc, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linie) + '\n')
    return sc
