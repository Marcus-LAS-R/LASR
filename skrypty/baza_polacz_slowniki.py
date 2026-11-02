# -*- coding: utf-8 -*-
"""Kody użytków i klas spoza słowników bazy docelowej przy łączeniu baz.

Relacje w bazie TPU odrzucają wiersz F_PARCEL_LAND_USE z kodem spoza
F_AREA_USE_DIC albo F_SOIL_QUALITY_DIC, a razem z nim przypisania wydzieleń
w F_AROD_LAND_USE. Łączenie zapisuje wtedy resztę i zgłasza błędy dopiero
w raporcie, a baza traci powierzchnię ewidencyjną. Moduł wykrywa takie kody
przed łączeniem i dopisuje je do słowników bazy wynikowej, z definicją
skopiowaną z bazy źródłowej.

Porównanie bez względu na wielkość liter i spacje końcowe, tak jak relacje
Accessa - dane mają np. IIIa przy słownikowym IIIA i to nie jest brak.

Bez importów QGIS-a: funkcje dostają gotowe obiekty Baza.
"""

# (pole w F_PARCEL_LAND_USE, tabela słownika, pole numeru, etykieta)
SLOWNIKI = (
    ('AREA_USE_CD', 'F_AREA_USE_DIC', 'AREA_USE_NR', 'użytek'),
    ('SOIL_QUALITY_CD', 'F_SOIL_QUALITY_DIC', 'SOIL_QUALITY_NR', 'klasa'),
)


def norm(kod):
    """Klucz porównania kodu; None dla pustego kodu (pusty nie jest brakiem,
    bo relacja go nie sprawdza)."""
    if kod is None:
        return None
    tekst = str(kod).strip().lower()
    return tekst or None


class Brak:
    """Kod używany w bazach źródłowych, nieobecny w słowniku docelowym."""

    def __init__(self, slownik, kod):
        self.pole, self.tabela, self.pole_nr, self.etykieta = slownik
        self.kod = str(kod).strip()
        self.ile = 0
        self.ha = 0.0
        self.bazy = {}        # {sciezka_bazy: liczba wierszy}
        self.definicja = None  # {kolumna: wartość} ze słownika źródła


def dolicz(braki, slownik, kody_celu, wiersze, baza_sc, dozwolone=None):
    """Dolicza do braków {(tabela, norm(kod)): Brak} wiersze jednej bazy:
    (COUNTY, DISTRICT, MUNICIPALITY, COMMUNITY, kod, ile, ha). dozwolone to
    zbiór obrębów z dialogu albo None, gdy baza idzie w całości."""
    for w in wiersze:
        if dozwolone is not None and tuple(w[:4]) not in dozwolone:
            continue
        klucz = norm(w[4])
        if klucz is None or klucz in kody_celu:
            continue
        brak = braki.setdefault((slownik[1], klucz), Brak(slownik, w[4]))
        brak.ile += w[5]
        brak.ha += float(w[6] or 0)
        brak.bazy[baza_sc] = brak.bazy.get(baza_sc, 0) + w[5]


def numer_w_slowniku(nr_zrodla, zajete):
    """Numer ze źródła, gdy wolny w słowniku docelowym, inaczej kolejny po
    największym zajętym."""
    if nr_zrodla is not None and nr_zrodla not in zajete:
        return nr_zrodla
    return max(zajete, default=0) + 1


def _kody_slownika(baza, slownik):
    """{norm(kod): {kolumna: wartość}} albo None, gdy słownik jest nieczytelny."""
    wiersze = baza.pobierz('SELECT * FROM ' + slownik[1])
    if wiersze is False:
        return None
    kolumny = [d[0] for d in baza.cur.description]
    idx = kolumny.index(slownik[0])
    return {norm(w[idx]): dict(zip(kolumny, w))
            for w in wiersze if norm(w[idx]) is not None}


def _uzycie_kodow(baza, pole):
    return baza.pobierz(
        'SELECT p.COUNTY_CD, p.DISTRICT_CD, p.MUNICIPALITY_CD, p.COMMUNITY_CD, '
        'u.' + pole + ', Count(*), Sum(u.LAND_USE_AREA) '
        'FROM F_PARCEL_LAND_USE AS u INNER JOIN F_PARCEL AS p '
        'ON u.PARCEL_INT_NUM = p.PARCEL_INT_NUM '
        'GROUP BY p.COUNTY_CD, p.DISTRICT_CD, p.MUNICIPALITY_CD, '
        'p.COMMUNITY_CD, u.' + pole)


def znajdz_braki(baza_cel, bazy_zrodlowe, obreby_wybrane=None):
    """baza_cel: połączona Baza; bazy_zrodlowe: lista (ścieżka, połączona
    Baza). Zwraca (lista Brak, niesprawdzone), gdzie niesprawdzone to opisy
    tego, czego nie dało się odczytać (np. stara struktura bazy)."""
    braki = {}
    niesprawdzone = []
    for slownik in SLOWNIKI:
        kody_celu = _kody_slownika(baza_cel, slownik)
        if kody_celu is None:
            niesprawdzone.append('baza docelowa: ' + slownik[1])
            continue
        for sc, baza in bazy_zrodlowe:
            wiersze = _uzycie_kodow(baza, slownik[0])
            if wiersze is False:
                niesprawdzone.append(sc + ': F_PARCEL_LAND_USE')
                continue
            dozwolone = (obreby_wybrane or {}).get(sc)
            dolicz(braki, slownik, kody_celu, wiersze, sc, dozwolone)
            definicje = _kody_slownika(baza, slownik) or {}
            for (tabela, klucz), brak in braki.items():
                if tabela == slownik[1] and brak.definicja is None:
                    brak.definicja = definicje.get(klucz)
    wynik = sorted(braki.values(),
                   key=lambda b: (b.tabela, -b.ile, b.kod))
    return wynik, niesprawdzone


def dopisz_braki(baza_cel, braki):
    """Dopisuje kody do słowników bazy wynikowej. Zwraca (dopisane kody,
    [(tabela, kod, błąd)]). Błąd jednego kodu nie zatrzymuje pozostałych."""
    dopisane = []
    bledy = []
    for brak in braki:
        try:
            baza_cel.cur.execute('SELECT * FROM ' + brak.tabela)
            kolumny = [d[0] for d in baza_cel.cur.description]
            zajete = {w[kolumny.index(brak.pole_nr)]
                      for w in baza_cel.cur.fetchall()
                      if w[kolumny.index(brak.pole_nr)] is not None}
            wiersz = {k: v for k, v in (brak.definicja or {}).items()
                      if k in kolumny}
            wiersz[brak.pole] = wiersz.get(brak.pole) or brak.kod
            pole_nazwy = brak.pole[:-2] + 'NAME'
            if pole_nazwy in kolumny and not wiersz.get(pole_nazwy):
                wiersz[pole_nazwy] = brak.kod
            wiersz[brak.pole_nr] = numer_w_slowniku(
                wiersz.get(brak.pole_nr), zajete)
            pola = list(wiersz)
            baza_cel.cur.execute(
                'INSERT INTO ' + brak.tabela + ' (' + ', '.join(pola) +
                ') VALUES (' + ', '.join('?' * len(pola)) + ')',
                [wiersz[p] for p in pola])
            baza_cel.con.commit()
            dopisane.append(brak.kod)
        except Exception as e:
            baza_cel.con.rollback()
            bledy.append((brak.tabela, brak.kod, str(e)))
    return dopisane, bledy


def ha_tekst(ha):
    return ('%.4f' % ha).replace('.', ',')


def tresc_pytania(braki, nazwa_celu):
    """(tekst okna, szczegóły) pytania o dopisanie kodów."""
    wiersze = ['%s %s: %d rek., %s ha' % (
        b.etykieta.capitalize(), b.kod, b.ile, ha_tekst(b.ha))
        for b in braki[:15]]
    if len(braki) > 15:
        wiersze.append('... i %d kolejnych (w szczegółach)' % (len(braki) - 15))
    tekst = (
        'W bazach źródłowych są kody, których nie ma w słownikach bazy '
        'docelowej ' + nazwa_celu + ':\n\n' + '\n'.join(wiersze) + '\n\n'
        'Bez dopisania te rekordy i rozliczone na nich wydzielenia nie trafią '
        'do połączonej bazy, a jej powierzchnia ewidencyjna będzie zaniżona.\n'
        'Kody zostaną dopisane tylko do bazy wynikowej, wskazany plik bazy '
        'docelowej się nie zmieni.\n\nDopisać je do słowników?')
    szczegoly = []
    for b in braki:
        szczegoly.append('%s (%s): %d rek., %s ha' % (
            b.kod, b.tabela, b.ile, ha_tekst(b.ha)))
        szczegoly += ['   %s: %d' % (sc, ile)
                      for sc, ile in sorted(b.bazy.items())]
    return tekst, '\n'.join(szczegoly)
