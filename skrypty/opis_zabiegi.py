"""Generator zabiegów Edytora opisu - na stanie KARTY, bez zapisu do bazy.

Ta sama logika co "Dopisz/sprawdź zabiegi" w trybie Dopisz (bez trybu
Janczulewicza): klasa WydzielenieKarty dziedziczy po zabiegi.Wydzielenie
(generowanie, obliczenia, kontrole bez zmian), a nadpisuje tylko:
- wejście: dane w kształcie Baza.pobierz_do_zab() składane z karty
  (opis, warstwy, gatunki, PNSW); z bazy czytane tylko to, czego karta
  nie edytuje (liczba działek F_AROD_LAND_USE, cele hodowlane F_AROD_GOAL
  inne niż TD, wiek rębności),
- wyjście: metody Wpisz zamiast INSERT/UPDATE zbierają wiersze zabiegów
  karty i nowe uwagi SUBAREA_INFO.
Moduł zabiegi/ nie jest zmieniany - skrypt wsadowy działa jak dotąd.

Karta jest czyszczona z zabiegów przed generowaniem (decyzja należy do
operatora) - generator nie widzi wpisanych zabiegów (w tym rębni).
"""
import copy

from . import opis_warstwy as ow
from .zabiegi.wydzielenie import Wydzielenie

MAX_UWAG = 254  # jak Wpisz.uzupelnij_uwagi (SUBAREA_INFO VARCHAR(255))


class WydzielenieKarty(Wydzielenie):
    """Wydzielenie z zabiegi/ zapisujące wynik do list zamiast do bazy."""

    def przygotuj_strukture(self, aid):
        super().przygotuj_strukture(aid)
        self.baza = None  # nic nie może pisać do bazy
        # wygenerowane wiersze F_AROD_CUE: {pole: wartość} w kolejności
        self.wiersze_zab = []

    def _wiersz(self, kod, pow_zab, proc, perc=None, wart=None):
        self.wiersze_zab.append({
            'MEASURE_CD': kod, 'URGENCY': 'N', 'CUTTING_AREA': pow_zab,
            'PROC_AREA': proc, 'LARGE_TIMBER_PERC': perc,
            'LARGE_TIMBER_VALUE': wart})

    # --------------------------------------- Wpisz - zapis do list karty

    def _dopisz_nowa_rebnie(self):
        if self.gen_reb in ['', False, None]:
            return True, ''
        if self.max_cue != 0:
            return False, 'Rębnia powinna być dopisana jako pierwsza...'
        self.max_cue += 1
        self._wiersz(self.gen_reb, self.pow_wydz, 100, self.gen_proc_reb)
        self.zmodyfikowano += 1
        return True, 'OK'

    def _dopisz_ciecie_mlodych(self, zab):
        ciecie = self._oblicz_ciecie(zab[0])
        self._wiersz(zab[0], zab[1], self._proc_zab(zab), ciecie[0],
                     ciecie[1])
        self.dodano += 1
        return True

    def _dopisz_inne_zabiegi(self, zab):
        self._wiersz(zab[0], zab[1], self._proc_zab(zab))
        self.dodano += 1
        return True

    def _dopisz_przest_plaz(self, zab):
        grub = self.przest_vol if zab[0] == 'PRZEST' else self.plaz_vol
        self._wiersz(zab[0], zab[1], self._proc_zab(zab), 100,
                     round(grub, 0))
        self.dodano += 1
        return True

    def _zmodyfikuj_powierzchnie(self, zab):
        # karta bez zabiegów - nie ma czego modyfikować (zabezpieczenie)
        return False

    def uzupelnij_uwagi(self):
        """Nowe uwagi zostają w self.uwagi - karta przejmuje je po
        generowaniu (zbyt długie - tylko do listy uwag, jak w Wpisz)."""
        if self.uwagi != self.uwagi_org and len(self.uwagi) > MAX_UWAG:
            self.uw_baza.append(
                'Nie udało się pisać opisu do f_subarea (za długi): '
                f'{self.uwagi}')
            return False
        return True


# ------------------------------------------------ wejście z karty

def _num(v):
    return 0 if v is None else v


def dane_z_karty(dane, pow_wydz, nr_warstw, ile_dzkat, cele_inne,
                 zabiegi=()):
    """Lista 10 tabel w kształcie Baza.pobierz_do_zab() ze stanu karty.
    zabiegi - wiersze karty (kontrola po wygenerowaniu), cele_inne - liczba
    celów hodowlanych w bazie innych niż TD (TD bierzemy z karty)."""
    aid = 0
    warstwy = ow.posortuj(copy.deepcopy(dane['WARSTWY']), nr_warstw)
    pod_nal = [(aid, w['STOREY_CD'], w['STANDDENSITY_INDEX'], i,
                w['DENSITY_CD'] or None)
               for i, w in enumerate(warstwy, 1)]
    cue = [(aid, z['MEASURE_CD'], z['CUTTING_AREA'], i, z['PROC_AREA'],
            z['LARGE_TIMBER_PERC'], z['LARGE_TIMBER_VALUE'])
           for i, z in enumerate(zabiegi, 1)]
    gat_gl, gat_opisy, przest, pp = [], [], [], False
    for w in warstwy:
        k = w['STOREY_CD']
        for g in w['gatunki']:
            if k in ('PŁAZ', 'PRZES'):
                pp = True
            if k == 'PRZES':
                przest.append((aid, g['SPECIES_CD'], g['PART_CD'],
                               g['SPECIES_AGE'], g['BHD'], g['VOLUME'], k))
            if k in ('DRZEW', 'IP', 'IIP'):
                gat_opisy.append((g['SPECIES_CD'], g['SITE_CLASS_CD'] or None,
                                  g['PART_CD'], g['SPECIES_AGE'], g['BHD'],
                                  g['HEIGHT'], g['VOLUME']))
        if k == 'DRZEW' and w['gatunki']:
            g = w['gatunki'][0]
            gat_gl = [(aid, g['SPECIES_CD'], 1, g['SPECIES_AGE'], g['BHD'],
                       g['VOLUME'])]
    info = dane['SUBAREA_INFO'] or None
    szczeg = [(aid, dane['AREA_TYPE_CD'] or None,
               dane['SITE_TYPE_CD'] or None, pow_wydz, info,
               dane['STAND_STRUCT_CD'] or None,
               dane['DAMAGE_DEGREE_CD'] or None, info,
               dane['VEG_COVER_CD'] or None)]
    luki = [p for p in dane['PNSW'] if p['SPECIAL_AREA_CD'] == 'LUKA']
    luki = [(aid, 'LUKA', sum(_num(p['SPECIAL_AREA']) for p in luki))] \
        if luki else []
    return [pod_nal, cue, gat_gl, [(aid,)] if pp else [], szczeg, przest,
            luki, [(ile_dzkat,)], [(cele_inne + len(dane['TD']),)],
            gat_opisy]


def wyczysc_opis(dane):
    """Jak tryb Dopisz (tam w bazie, globalnie): bez zadrzewienia w PRZES
    i bez masy w PODR/PODSZ/NAL - na karcie."""
    for w in dane['WARSTWY']:
        if w['STOREY_CD'] == 'PRZES':
            w['STANDDENSITY_INDEX'] = None
        if w['STOREY_CD'] in ('PODSZ', 'PODR', 'NAL'):
            for g in w['gatunki']:
                g['VOLUME'] = None


def _wydzielenie(tab, wiek_reb, mod_trzeb):
    w = WydzielenieKarty()
    w.przygotuj_strukture(0)
    w.dodaj_mod_trzeb(mod_trzeb)
    w.o_wiek_rebnosci(wiek_reb)
    if not w.odczytaj_dane_z_bazy(tab):
        raise RuntimeError('nie udało się odczytać opisu z karty')
    if not w.generuj_zabiegi():
        raise RuntimeError('nie wygenerowano wskazówek')
    return w


def generuj(dane, pow_wydz, nr_warstw, ile_dzkat, cele_inne, wiek_reb,
            mod_trzeb):
    """Zabiegi dla stanu karty (karta bez zabiegów). Zwraca (wiersze
    zabiegów, nowe SUBAREA_INFO albo None, uwagi, dodano, zmieniono).
    dane - kopia danych karty (wyczysc_opis jest stosowane tutaj)."""
    dane = copy.deepcopy(dane)
    wyczysc_opis(dane)
    dane['ZABIEGI'] = []
    tab = dane_z_karty(dane, pow_wydz, nr_warstw, ile_dzkat, cele_inne)
    w = _wydzielenie(tab, wiek_reb, mod_trzeb)
    w.modyfikuj_zabiegi('')
    uwagi = list(w.uw_raport) + list(w.uw_baza)
    info = None
    if w.uwagi != w.uwagi_org and len(w.uwagi) <= MAX_UWAG:
        info = w.uwagi
        dane['SUBAREA_INFO'] = info
    # kontrola jak raport zabiegów - na karcie po wygenerowaniu
    tab2 = dane_z_karty(dane, pow_wydz, nr_warstw, ile_dzkat, cele_inne,
                        w.wiersze_zab)
    w2 = _wydzielenie(tab2, wiek_reb, mod_trzeb)
    w2.zbiorcze_sprawdzenie()
    uwagi += [u for u in list(w2.uw_raport) + list(w2.uw_baza)
              if u not in uwagi]
    return w.wiersze_zab, info, uwagi, w.dodano, w.zmodyfikowano
