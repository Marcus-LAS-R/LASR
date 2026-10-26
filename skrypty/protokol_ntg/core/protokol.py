# -*- coding: utf-8 -*-
"""NTG - zestawienia do protokołu narady (bez Qt-owych okien).

Dane z połączonej bazy UPUL (<eksport>\\Baza_NTG_polaczona_BDO.mdb
z "Przygotuj warstwy i bazę"), nadleśnictwa z warstwy SHP\\NADL (przecinające WYDZ). Wynik:
słownik dla wzoru protokołu docxtpl wskazanego w oknie (plik poza
wtyczką; zmienne: miejscowosc, data_narady, tytul, nr_umowy, data_umowy,
data_umowy_sl, rok_od, rok_do, starostwo, otwierajacy, data_kontroli,
zaproszeni oraz tab_* z DaneProtokolu.policz(), wiersze z polem razem).

Zastępuje kwerendy `__NTG_*` / `_OPRACOWANIE_*` zapisywane dawniej w bazie
(stary skrypt ntg_20200908.py) - te same zestawienia, ale:
- wydzielenie leży w jednym obrębie (gmina/obręb z jego działek, przez
  F_AROD_LAND_USE -> F_PARCEL); wydzielenie z działkami w kilku obrębach
  trafia do ostrzeżeń, liczone w pierwszym;
- średnie w statystykach WAŻONE: suma powierzchni rekordów gminy / liczba
  rekordów (dawniej średnia ze średnich obrębów - np. gm. 042 Jarosław
  1,7981 zamiast 1,3214 ha), działki i użytki Ls liczone unikalnie;
- jednostki rejestrowe G liczone w obrębie i sumowane do gminy (właściciel
  w dwóch obrębach liczy się dwa razy - tak jak dotąd);
- gmina = COUNTY+DISTRICT+MUNICIPALITY (dawniej sam MUNICIPALITY_CD).
"""
from qgis.core import QgsFeatureRequest, QgsSpatialIndex, QgsVectorLayer

from ...baza_wrapper import Baza

# zabiegi hodowlane (pkt 9) - reszta F_AROD_CUE to pozyskanie (pkt 8);
# lista jak w kwerendach _OPRACOWANIE_ZABIEGI_HODOWLA/_POZYSKANIE
HODOWLANE = {
    "AGROT", "MA-FIT", "MA-MIN", "MA-REG", "ODN-HAL", "ODN-IIP", "ODN-LUK",
    "ODN-PLAN", "ODN-POR", "ODN-ZŁOŻ", "ODN-ZRB", "PIEL", "PODSZ", "POPR",
    "ZAL-NIEU", "Z-PIELD", "Z-PIELK", "Z-SADZD", "Z-SADZK", "CP", "CW", "CP-P",
}
MASA_TW_TP = {"TP", "TW"}
BEZ_TSL = "Bez określenia"

# RDLP: miasto (lista w oknie) -> miejscownik ("Regionalnej Dyrekcji Lasów
# Państwowych w ...")
RDLP = {
    "Białystok": "Białymstoku", "Gdańsk": "Gdańsku", "Katowice": "Katowicach",
    "Kraków": "Krakowie", "Krosno": "Krośnie", "Lublin": "Lublinie",
    "Łódź": "Łodzi", "Olsztyn": "Olsztynie", "Piła": "Pile",
    "Poznań": "Poznaniu", "Radom": "Radomiu", "Szczecin": "Szczecinie",
    "Szczecinek": "Szczecinku", "Toruń": "Toruniu", "Warszawa": "Warszawie",
    "Wrocław": "Wrocławiu", "Zielona Góra": "Zielonej Górze",
}

MIESIACE = ("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
            "lipca", "sierpnia", "września", "października", "listopada",
            "grudnia")


def liczba(val, calk=False, miejsca=4):
    """Format jak w dotychczasowych protokołach: 4 miejsca po przecinku
    z zerami (12,3400), zero jako '0', całkowite bez części dziesiętnej."""
    try:
        val = float(val or 0)
    except (TypeError, ValueError):
        return "0"
    if calk:
        return str(int(round(val)))
    if round(val, miejsca) == 0:
        return "0"
    return ("%.*f" % (miejsca, val)).replace(".", ",")


def data_slownie(d):
    """datetime.date -> '20 lutego 2026'"""
    return "%d %s %d" % (d.day, MIESIACE[d.month - 1], d.year)


_ALFABET = "AĄBCĆDEĘFGHIJKLŁMNŃOÓPQRSŚTUVWXYZŹŻ"


def klucz_pl(tekst):
    """Klucz sortowania wg polskiego alfabetu (LŁ przed LMŚW, LMŚW przed
    LMW - jak w dotychczasowych protokołach z Accessa)."""
    wyn = []
    for z in tekst.upper():
        i = _ALFABET.find(z)
        wyn.append((1, i) if i >= 0 else (0, ord(z)))
    return wyn


def _s(x):
    return str(x).strip() if x is not None else ""


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


class DaneProtokolu:
    """Zestawienia z bazy UPUL. Po policz(): self.tabele (klucze tab_*
    szablonu) i self.ostrzezenia (lista tekstów do raportu)."""

    def __init__(self, baza_sc):
        self.baza_sc = baza_sc
        self.ostrzezenia = []
        self.tabele = {}

    # ------------------------------------------------------------ odczyt

    def _pobierz(self, baza, sql, opis):
        w = baza.pobierz(sql)
        if w is False:
            raise RuntimeError("Błąd odczytu z bazy: " + opis)
        return w

    def _wczytaj(self):
        baza = Baza(self.baza_sc)
        if not baza.polacz():
            raise RuntimeError("Nie udało się połączyć z bazą " +
                               self.baza_sc)
        try:
            self.gminy = {
                (_s(c), _s(d), _s(m)): _s(n) for c, d, m, n in self._pobierz(
                    baza, "select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, "
                    "MUNICIPALITY_NAME from F_MUNICIPALITY;", "F_MUNICIPALITY")}
            self.obreby = {
                (_s(c), _s(d), _s(m), _s(o)): _s(n)
                for c, d, m, o, n in self._pobierz(
                    baza, "select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, "
                    "COMMUNITY_CD, COMMUNITY_NAME from F_COMMUNITY;",
                    "F_COMMUNITY")}
            self.wydz_dz = self._pobierz(
                baza,
                "select a.ARODES_INT_NUM, a.ARODES_TYP_CD, a.ADRESS_FOREST, "
                "l.PARCEL_INT_NUM, l.SHAPE_NR, l.AROD_LAND_USE_AREA, "
                "p.COUNTY_CD, p.DISTRICT_CD, p.MUNICIPALITY_CD, "
                "p.COMMUNITY_CD, p.PARCEL_AREA, p.LAND_REGISTER_NR "
                "from (F_ARODES as a inner join F_AROD_LAND_USE as l on "
                "a.ARODES_INT_NUM = l.ARODES_INT_NUM) inner join F_PARCEL "
                "as p on l.PARCEL_INT_NUM = p.PARCEL_INT_NUM;",
                "wydzielenia z działkami")
            self.uzytki = {
                (u, sh): (_s(k), _f(pw)) for u, sh, k, pw in self._pobierz(
                    baza, "select PARCEL_INT_NUM, SHAPE_NR, AREA_USE_CD, "
                    "LAND_USE_AREA from F_PARCEL_LAND_USE;",
                    "F_PARCEL_LAND_USE")}
            self.subarea = {}
            for a, pw, tsl, typ in self._pobierz(
                    baza, "select ARODES_INT_NUM, SUB_AREA, SITE_TYPE_CD, "
                    "AREA_TYPE_CD from F_SUBAREA;", "F_SUBAREA"):
                st = self.subarea.setdefault(a, [0.0, _s(tsl), _s(typ)])
                st[0] += _f(pw)
            self.zabiegi = self._pobierz(
                baza, "select ARODES_INT_NUM, MEASURE_CD, CUTTING_AREA, "
                "LARGE_TIMBER_VALUE from F_AROD_CUE;", "F_AROD_CUE")
            self.przyrost = {
                a: _f(s) for a, s in self._pobierz(
                    baza, "select ARODES_INT_NUM, "
                    "sum(INCREMENT_CURRENT_AREA) from F_STOREY_SPECIES "
                    "group by ARODES_INT_NUM;", "F_STOREY_SPECIES")}
            self.fop = self._pobierz(
                baza, "select s.ARODES_INT_NUM, f.PROTEC_AREA_CD, "
                "f.LAND_PROTECT_NAME, f.LAND_PROTECT_AREA from F_SET as s "
                "inner join F_LAND_PROTECT as f on s.MY_INT_NUM = f.INT_NUM;",
                "F_SET/F_LAND_PROTECT")
            self.etaty = self._pobierz(
                baza, "select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, "
                "ETAT_OKW, ETAT_POKW, ETAT_WSK, ETAT_POZ from F_ETAT;",
                "F_ETAT")
        finally:
            baza.zamknij()

    # ------------------------------------------------------------ obliczenia

    def _przypisz_obreby(self):
        """wydzielenie -> obręb (c, d, m, o); kontrola kilku obrębów."""
        obreby_wydz = {}
        for w in self.wydz_dz:
            obr = (_s(w[6]), _s(w[7]), _s(w[8]), _s(w[9]))
            obreby_wydz.setdefault(w[0], [])
            if obr not in obreby_wydz[w[0]]:
                obreby_wydz[w[0]].append(obr)
        self.obr_wydz = {}
        for a, lista in obreby_wydz.items():
            self.obr_wydz[a] = lista[0]
            if len(lista) > 1:
                adres = next(_s(w[2]) for w in self.wydz_dz if w[0] == a)
                self.ostrzezenia.append(
                    "Wydzielenie %s ma działki w kilku obrębach (%s) - "
                    "liczone w %s" % (adres, ", ".join(
                        "-".join(o) for o in lista), "-".join(lista[0])))
        self.typ_wydz = {w[0]: _s(w[1]) for w in self.wydz_dz}
        self.adres_wydz = {w[0]: _s(w[2]) for w in self.wydz_dz}

    def nazwa_gminy(self, gm):
        return self.gminy.get(gm) or "gm. %s" % "".join(gm)

    def lista_gmin(self):
        """Gminy z wydzieleniami (kolejność kodów)."""
        return sorted({o[:3] for o in self.obr_wydz.values()})

    def _tab_admin(self):
        # sumy per obręb: Ls, inne użytki dodane do wydzieleń, Lz
        sumy = {}
        for (a, _t, adres, dz, sh, pw, c, d, m, o, _pp, _g) in self.wydz_dz:
            obr = (_s(c), _s(d), _s(m), _s(o))
            s = sumy.setdefault(obr, [0.0, 0.0, 0.0])
            pw = _f(pw)
            if self.uzytki.get((dz, sh), ("",))[0].upper() == "LS":
                s[0] += pw
            else:
                s[1] += pw
            if "LZ" in _s(adres).upper():
                s[2] += pw
        wiersze, ogolem = [], [0.0, 0.0, 0.0]
        for gm in self.lista_gmin():
            naz = self.nazwa_gminy(gm)
            razem = [0.0, 0.0, 0.0]
            for obr in sorted(o for o in sumy if o[:3] == gm):
                ls, nie, lz = sumy[obr]
                razem = [razem[0] + ls, razem[1] + nie, razem[2] + lz]
                wiersze.append(self._w_admin(
                    naz, obr[3], self.obreby.get(obr, ""), ls, nie, lz))
            wiersze.append(self._w_admin("Razem:", "", "", *razem,
                                         razem_=True))
            wiersze.append({k: "" for k in wiersze[-1]} | {"razem": False})
            ogolem = [x + y for x, y in zip(ogolem, razem)]
        wiersze.append(self._w_admin("Ogółem:", "", "", *ogolem,
                                     razem_=True))
        return wiersze

    @staticmethod
    def _w_admin(naz, obr, obr_naz, ls, nie, lz, razem_=False):
        return {"naz": naz, "obr": obr, "obr_naz": obr_naz,
                "pow_ls": liczba(ls), "pow_lz": liczba(lz),
                "pow_nie": liczba(nie), "pow_roz": liczba(ls + nie - lz),
                "razem": razem_}

    def _suma_gmina_klucz(self, wartosci):
        """{(gm, klucz): suma} -> wiersze posortowane po gminie i kluczu
        + wiersze Razem po kluczu; klucz BEZ_TSL na końcu gminy."""
        porz = (lambda k: (k == BEZ_TSL, klucz_pl(k)))
        wiersze, razem = [], {}
        for gm in self.lista_gmin():
            for k in sorted({k for g, k in wartosci if g == gm}, key=porz):
                pw = wartosci[(gm, k)]
                wiersze.append((gm, k, pw))
                razem[k] = razem.get(k, 0.0) + pw
        return wiersze, [(k, razem[k]) for k in sorted(razem, key=porz)]

    def _tab_tsl(self):
        wart = {}
        for (a, _t, _ad, _dz, _sh, pw, *_r) in self.wydz_dz:
            tsl = self.subarea.get(a, [0, "", ""])[1] or BEZ_TSL
            k = (self.obr_wydz[a][:3], tsl)
            wart[k] = wart.get(k, 0.0) + _f(pw)
        wiersze, razem = self._suma_gmina_klucz(wart)
        return ([{"gm": self.nazwa_gminy(g), "tsl": k, "pow": liczba(p),
                  "razem": False} for g, k, p in wiersze] +
                [{"gm": "Razem", "tsl": k, "pow": liczba(p), "razem": True}
                 for k, p in razem])

    def _tab_zabiegi(self, hodowlane):
        wart = {}
        for a, zab, pw, _m in self.zabiegi:
            zab = _s(zab)
            if a not in self.obr_wydz or (zab in HODOWLANE) != hodowlane:
                continue
            k = (self.obr_wydz[a][:3], zab)
            wart[k] = wart.get(k, 0.0) + _f(pw)
        wart = {k: v for k, v in wart.items() if round(v, 4) > 0}
        wiersze, razem = self._suma_gmina_klucz(wart)
        if not hodowlane:        # pozyskanie: wg rodzaju zabiegu, potem gmin
            wiersze.sort(key=lambda w: (klucz_pl(w[1]), w[0]))
        return ([{"gm": self.nazwa_gminy(g), "zab": k, "pow": liczba(p),
                  "razem": False} for g, k, p in wiersze] +
                [{"gm": "Razem", "zab": k, "pow": liczba(p), "razem": True}
                 for k, p in razem])

    def _tab_ochr(self):
        wydz = {}
        for a, ozn, naz, powg in self.fop:
            if a not in self.obr_wydz:
                continue
            k = (_s(ozn), _s(naz), _f(powg), self.obr_wydz[a][:3])
            wydz.setdefault(k, set()).add(a)
        wiersze = []
        for (ozn, naz, powg, gm), zb in wydz.items():
            pw = sum(self.subarea.get(a, [0.0])[0] for a in zb)
            if round(pw, 4) > 0:
                wiersze.append({"gm": self.nazwa_gminy(gm), "ozn": ozn,
                                "naz": naz, "powg": liczba(powg, calk=True),
                                "wydz": liczba(pw), "razem": False,
                                "_s": (klucz_pl(ozn), klucz_pl(naz), gm)})
        wiersze.sort(key=lambda w: w["_s"])
        for w in wiersze:
            del w["_s"]
        return wiersze

    def _tab_stat(self):
        """Statystyki gmin - średnie ważone, jednostki G w obrębach."""
        obr = {}      # obręb -> zbiory
        for (a, typ, _ad, dz, sh, _pw, c, d, m, o, ppow, grej) in \
                self.wydz_dz:
            if _s(typ) != "WYDZIEL":
                continue
            ob = (_s(c), _s(d), _s(m), _s(o))
            z = obr.setdefault(ob, {"dz": {}, "g": set(), "ls": {}})
            z["dz"][dz] = _f(ppow)
            if _s(grej):
                z["g"].add(_s(grej))
            uz = self.uzytki.get((dz, sh))
            if uz and uz[0].upper() == "LS":
                z["ls"][(dz, sh)] = uz[1]
        wiersze = []
        sumy = {"lwydz": 0, "grej": 0, "ldz": 0}
        for gm in self.lista_gmin():
            wydz = [a for a, o in self.obr_wydz.items()
                    if o[:3] == gm and self.typ_wydz.get(a) == "WYDZIEL"]
            pow_wydz = sum(self.subarea.get(a, [0.0])[0] for a in wydz)
            przyr = sum(self.przyrost.get(a, 0.0) for a in wydz)
            zb = [z for o, z in obr.items() if o[:3] == gm]
            dz = {}
            ls = {}
            for z in zb:
                dz.update(z["dz"])
                ls.update(z["ls"])
            grej = sum(len(z["g"]) for z in zb)
            wiersze.append({
                "gm": self.nazwa_gminy(gm),
                "lwydz": liczba(len(wydz), calk=True),
                "pwydz": liczba(pow_wydz / len(wydz) if wydz else 0),
                "grej": liczba(grej, calk=True),
                "ldz": liczba(len(dz), calk=True),
                "pdz": liczba(sum(dz.values()) / len(dz) if dz else 0),
                "pls": liczba(sum(ls.values()) / len(ls) if ls else 0),
                "pwaz": liczba(przyr / pow_wydz if pow_wydz else 0,
                               calk=True),
                "razem": False})
            sumy["lwydz"] += len(wydz)
            sumy["grej"] += grej
            sumy["ldz"] += len(dz)
        wiersze.append({
            "gm": "Razem", "lwydz": liczba(sumy["lwydz"], calk=True),
            "pwydz": "-", "grej": liczba(sumy["grej"], calk=True),
            "ldz": liczba(sumy["ldz"], calk=True), "pdz": "-", "pls": "-",
            "pwaz": "-", "razem": True})
        return wiersze

    def _tab_roz(self):
        wart = {}
        for (a, _t, _ad, _dz, _sh, pw, *_r) in self.wydz_dz:
            typ = self.subarea.get(a, [0, "", ""])[2]
            if "LZ" not in typ.upper() and typ != "INNE WYL":
                continue
            k = (self.obr_wydz[a][:3], typ)
            wart[k] = wart.get(k, 0.0) + _f(pw)
        wiersze, razem = self._suma_gmina_klucz(wart)
        return ([{"gm": self.nazwa_gminy(g), "rodz": k, "pow": liczba(p),
                  "razem": False} for g, k, p in wiersze] +
                [{"gm": "Razem", "rodz": k, "pow": liczba(p), "razem": True}
                 for k, p in razem])

    def _tab_etaty(self):
        et = {}
        for c, d, m, *wart in self.etaty:
            gm = (_s(c), _s(d), _s(m))
            s = et.setdefault(gm, [0.0] * 5)
            for i, v in enumerate(wart):
                s[i] += _f(v)
        for a, zab, _pw, masa in self.zabiegi:
            if _s(zab) in MASA_TW_TP and a in self.obr_wydz:
                gm = self.obr_wydz[a][:3]
                et.setdefault(gm, [0.0] * 5)[4] += _f(masa)
        wiersze, razem = [], [0.0] * 5
        for gm in sorted(et):
            s = et[gm]
            razem = [x + y for x, y in zip(razem, s)]
            wiersze.append(self._w_etat(gm[2], self.nazwa_gminy(gm), s))
        if wiersze:
            wiersze.append(self._w_etat("Razem", "-", razem, True))
        return wiersze

    @staticmethod
    def _w_etat(gm, naz, s, razem_=False):
        return {"gm": gm, "naz": naz, "e1": liczba(s[0], calk=True),
                "e2": liczba(s[1], calk=True), "e3": liczba(s[2], calk=True),
                "e4": liczba(s[3], calk=True), "e5": liczba(s[4], calk=True),
                "razem": razem_}

    def policz(self):
        self._wczytaj()
        if not self.wydz_dz:
            raise RuntimeError("W bazie nie ma wydzieleń z działkami "
                               "(F_AROD_LAND_USE/F_PARCEL)")
        self._przypisz_obreby()
        self.tabele = {
            "tab_admin": self._tab_admin(),
            "tab_tsl": self._tab_tsl(),
            "tab_reb": self._tab_zabiegi(hodowlane=False),
            "tab_hod": self._tab_zabiegi(hodowlane=True),
            "tab_ochr": self._tab_ochr(),
            "tab_stat": self._tab_stat(),
            "tab_roz": self._tab_roz(),
            "tab_etaty": self._tab_etaty(),
        }
        return self.tabele


# ---------------------------------------------------------------- warstwy

def nadlesnictwa(nadl_sc, wydz_sc, pole_nazwy, pole_rdlp="reg_name"):
    """Nadleśnictwa (warstwa NADL z "Przygotuj") przecinające WYDZ:
    (lista nazw, lista RDLP) - nazwy z wielkiej litery (w warstwie BDL są
    wersalikami)."""
    nadl = QgsVectorLayer(nadl_sc, "NADL", "ogr")
    wydz = QgsVectorLayer(wydz_sc, "WYDZ", "ogr")
    if not nadl.isValid() or not wydz.isValid():
        return [], []
    pola = [f.name() for f in nadl.fields()]
    indeks = QgsSpatialIndex(wydz.getFeatures())
    nazwy, rdlp = set(), set()
    for f in nadl.getFeatures():
        g = f.geometry()
        if g.isNull():
            continue
        ids = indeks.intersects(g.boundingBox())
        if not ids:
            continue
        zadanie = QgsFeatureRequest().setFilterFids(ids)
        if any(g.intersects(w.geometry()) for w in wydz.getFeatures(zadanie)):
            nazwy.add(_s(f[pole_nazwy]).title())
            if pole_rdlp in pola:
                rdlp.add(_s(f[pole_rdlp]).title())
    return sorted(nazwy), sorted(rdlp)


# ---------------------------------------------------------------- dokument

def zaproszeni(wybor, rdlp_miasto, nadl, starostwo):
    """Lista zaproszonych (kolejność jak w protokołach) z zaznaczonych
    pozycji okna."""
    lista = []
    if "dglp" in wybor:
        lista.append("Dyrekcji Generalnej Lasów Państwowych")
    if "rdlp" in wybor:
        lista.append("Regionalnej Dyrekcji Lasów Państwowych w %s (RDLP)"
                     % RDLP.get(rdlp_miasto, rdlp_miasto))
    if "nadl" in wybor:
        lista.append("Nadleśnictw" + (": " + ", ".join(nadl) if nadl else ""))
    if "rdos" in wybor:
        lista.append("Regionalnej Dyrekcji Ochrony Środowiska (RDOŚ)")
    if "pwis" in wybor:
        lista.append("Państwowego Wojewódzkiego Inspektora Sanitarnego "
                     "(PWIS)")
    if "starostwo" in wybor:
        lista.append("Starostwa Powiatowego w %s" % starostwo)
    if "gminy" in wybor:
        lista.append("Przedstawicieli Gmin")
    lista.append("Wykonawca- LAS-R Sp. z o. o.")
    return lista


def generuj(kontekst, wynik_sc, szablon):
    from docxtpl import DocxTemplate
    tem = DocxTemplate(szablon)
    tem.render(kontekst, autoescape=True)
    tem.save(wynik_sc)
    return wynik_sc
