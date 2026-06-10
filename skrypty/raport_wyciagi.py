import os
import uuid
import datetime
import traceback

from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtGui import QFont, QPolygonF, QColor
from PyQt5.QtCore import Qt, QPointF, QVariant

from qgis.core import QgsVectorLayer, QgsExpression, QgsPrintLayout, Qgis,  \
    QgsFeatureRequest, QgsProject, QgsLayoutItemPage, QgsLayoutSize, \
    QgsLayoutItemLabel, QgsLayoutItem, QgsUnitTypes, QgsLayoutPoint, QgsField,\
    QgsLayoutItemPolyline, QgsRectangle, QgsLayoutItemMap, \
    QgsLayoutItemPicture, QgsLayoutExporter, QgsMessageLog

import processing

from .baza_wrapper import Baza
from .ui.ui_raport_wyciagi import Ui_Dialog


def isNone(a):
    if a in [None, 'NULL', '', ]:
        return ''

    elif isinstance(a, QVariant):
        if a.isNull():
            return ''
        else:
            return str(a)
    else:
        return str(a)


class Struktura:
    def przygotuj_strukture_baza(self):
        """Pobiera z bazy niezbędne dane do generowania wyciągów i pakuje je
        w odpowiednia strukture
        """
        self.sl_wl = {}  # sl z wlascicielami, opis patrz pobierz_wyk_wlasc!
        self.sl_gr = {}  # sl z grej w obrebach
        self.sl_pint = {}  # sl {pint: 'gggoooo.ark.nrdz'}
        self.aint = {}  # {aint: 'adr_les'}
        self.zab = {}  # {aint: {sl z danymi opisowym}}-patrz baza.pobierz_wyk

        self.sl_wl, self.sl_gr, self.sl_pint = self.baza.pobierz_wyk_wlasc()
        self.obr_w_gm, self.obr = self.baza.pobierz_obr_w_gm()
        self.aint = self.baza.pobierz_wydzielenia()
        self.zab = self.baza.pobierz_wyk_zalec()

        # wszyscy wlasciciele wpisani do bazy
        self.wl_all = {x[0]: isNone(x[1])+' '+isNone(x[2]) for x in
                       self.baza.pobierz_wlascicieli_all()}
        self.sl_gat, self.sl_zab = self.baza.pobierz_wyk_slowniki()

        # lista z warstwami uzytkow do mapek
        self.warstwy_klastrow = []

        # lista z warstwami dzialek z grej
        self.warstwy_dzialek = []

    def przygotuj_strukture_shp(self):
        self.wydz = QgsVectorLayer(os.path.join(self.kat, 'shp', 'WYDZ.shp'),
                                   'wydz', 'ogr')
        self.ls = QgsVectorLayer(os.path.join(self.kat, 'shp', 'LS.shp'),
                                 'ls', 'ogr')
        self.dz = QgsVectorLayer(os.path.join(self.kat, 'shp', 'DZKAT.shp'),
                                 'dz', 'ogr')
        self.ewid = QgsVectorLayer(os.path.join(self.kat, 'shp', 'EWID.shp'),
                                   'ewid', 'ogr')

        self.tempkat = os.path.join(self.kat, 'shp', 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        processing.run(
            "native:intersection",
            {
                'INPUT': self.wydz,
                'OVERLAY': self.ls,
                'INPUT_FIELDS': "",
                'OVERLAY_FILEDS': "",
                'OUTPUT': os.path.join(self.tempkat,
                                       '__ls_wydz_wyciagi.shp'
                                       )
            })

        self.inter = QgsVectorLayer(
            os.path.join(self.tempkat, '__ls_wydz_wyciagi.shp'),
            'inter', 'ogr'
        )

        # oblicz na nowo pole LAND_POW
        self.inter.startEditing()
        pole = QgsField("INTER_POW", QVariant.Double, "double", 10, 4)
        self.inter.dataProvider().addAttributes([pole])
        self.inter.updateFields()
        fni = self.inter.dataProvider().fieldNameIndex('INTER_POW')
        sl = {}
        for feat in self.inter.getFeatures():
            sl[feat.id()] = {fni: round(feat.geometry().area()/10000, 4)}
        self.inter.dataProvider().changeAttributeValues(sl)
        self.inter.commitChanges()

        # zaladuj style
        plug_dir = os.path.dirname(__file__)
        self.ewid.loadNamedStyle(
            os.path.join(plug_dir, '..', 'qml', 'wyc_EWID.qml'))
        self.wydz.loadNamedStyle(
            os.path.join(plug_dir, '..', 'qml', 'wyc_WYDZ_POL.qml'))

        # dodaj warstwy do TOC
        # QgsProject.instance().addMapLayer(self.ewid)
        # QgsProject.instance().addMapLayer(self.wydz)

    def przygotuj_strukture_eks(self):
        """Tworzy strukture katalogów z gmin i obrebow do ktorych wgrywane
        będą zalecenia dla wlasicicieli,
        """

        if not self.baza.polacz():
            return False

        folder = os.path.abspath(os.path.join(self.kat, 'WYCIAGI'))
        if not os.path.exists(folder):
            os.mkdir(folder)

        if not self.grupowanie_wyciagow:
            return

        for key, val in self.obr_w_gm.items():
            # stworz folder gminy jesli nie istnieje
            gm_folder = os.path.abspath(
                os.path.join(self.kat, 'WYCIAGI',  val))
            if not os.path.exists(gm_folder):
                os.mkdir(gm_folder)

            # stworz folder obr jesli nie istnieje
            obr_folder = os.path.abspath(
                os.path.join(self.kat, 'WYCIAGI', val, key))
            if not os.path.exists(obr_folder):
                os.mkdir(obr_folder)

            # katalog na inne
        obr_folder = os.path.abspath(os.path.join(self.kat, 'WYCIAGI', 'INNE'))
        if not os.path.exists(obr_folder):
            os.mkdir(obr_folder)


class Wyciag:
    def przygotuj_wyciag(self, addr):
        """Rozpocznij przygotowywac wyciag dla podanego nr addr wlasciciela
        """
        self.addr = addr
        self.w_grej = self.sl_wl[addr]['grej']
        self.kred = ''  # imie i nazwisko wlasciciela

        # slownik z featurkami nalezacymi do poszczegolnych grup rejestrowych
        # fdz - zawiera dzialki
        # fwy - zawiera wydzielenia lezace na tych dzialkach przeciete z lsami
        self.w_sl_fdz_grej = {}
        self.w_sl_fwy_grej = {}

        # listy z gatunkami i Cięciami wystepujacymi w tym wlascicielu
        self.lgat = []
        self.lzab = []

        self.w_pobierz_feats()

    def eksportuj_wyciag(self):
        """ Wyeksportuj wygenerowany wyciag do pdf """

        kred = self.kred.replace(' ', '_')
        if self.grupowanie_wyciagow:
            miej = self.sl_wl[self.addr]['opis']['miejscowosc'].upper()
            if miej in self.obr_w_gm:
                sc = os.path.join(
                    self.kat,
                    'WYCIAGI',
                    self.obr_w_gm[miej],
                    miej,
                    kred + '_' + str(self.addr) + '.pdf'
                )
            else:
                sc = os.path.join(
                    self.kat, 'WYCIAGI', 'INNE',
                    kred + '_' + str(self.addr) + '.pdf'
                )
        else:
            sc = os.path.join(
                self.kat, 'WYCIAGI',
                kred + '_' + str(self.addr) + '.pdf'
            )

        print(sc)
        exporter = QgsLayoutExporter(self.lay)
        exporter.exportToPdf(sc, QgsLayoutExporter.PdfExportSettings())

        # self.w_usun_layout()

    def w_pobierz_feats(self):
        """ Wybiera dzialki i feats z inter dla grej z aktywnego addr_nr
            uzupelnia w_sl_fdz_grej i w_sl_fwy_grej
            2 slowniki ktore przetrymuja featurki z podzialem na grej
            w postaci   {grej: [feat, ]}
        """
        if len(self.w_grej) == 0:
            return

        for gi in self.w_grej:
            # sprawdz czy taka grej jest w slowniku, jak nie - olej
            if gi[:7] not in self.sl_gr:
                continue
            if gi[8:] not in self.sl_gr[gi[:7]]:
                continue

            # lista ze spisem adresow dzialek w postaci: 'gggoooo.ark.nr'
            dz = [self.sl_pint[pid]
                  for pid in self.sl_gr[gi[:7]][gi[8:]]['dz']]
            pdz, pli = self._wybierz_feats(dz)
            self.w_sl_fdz_grej[gi] = pdz
            self.w_sl_fwy_grej[gi] = pli

    def _wybierz_feats(self, lista):
        """Wybiera z inter i dz odpowiednie featurki i zwraca je w postaci
        2 list posortowanych wg wysuniecia najbardziej na N
        return [dz_feats], [inter_feats]
        """
        ldz = []
        lit = []
        for li in lista:
            zaz = '"MUNICIP"=\'' + li[:3] + '\' and "COMMUNITY"=\''
            zaz += li[3:7] + '\' and '
            if li.count('.') == 2:
                zaz += '"ARK"=\'' + li.split('.')[1] + '\' and '
            zaz += '"PARCELNR"=\'' + li.split('.')[-1] + '\''

            exp = QgsExpression(zaz)
            req = QgsFeatureRequest(exp)
            lit += sorted([x for x in self.inter.getFeatures(req)
                           if x.geometry().area() > 0.5],
                          key=lambda x: x.geometry().boundingBox().yMaximum(),
                          reverse=True)
            ldz += [x for x in self.dz.getFeatures(req)]

        return ldz, lit

    def _klastruj(self, lista):
        """Klastruje featurki z listy w konglomeraty z ktore bedą mieścić się
        na mapie wkomponowanej w A4
        return [klaster, klaster]
            """

        # robocza lista wszystkich wydziele w obrebie
        wRob = [x for x in lista]
        klastry = []  # lista z klastrami
        i = 0  # analizowana pozycja na liscie z nieprzrypisanymi wydz
        kl = False
        dopis = False

        while len(wRob) > 0:
            if i == len(wRob):
                i = 0

            if i == 0 and not dopis:
                if isinstance(kl, Klaster):
                    klastry.append(kl)
                kl = Klaster(self.minOdl)
                kl.skala = self.skala
                if kl.dodaj_wydz(wRob[0]):
                    wRob.pop(0)

            if len(wRob) == 0:
                break

            dopis = False

            # wydzielenie w zasiegu klastra
            if kl.kwalifikuj(wRob[i]):
                if kl.dodaj_wydz(wRob[i]):
                    wRob.pop(i)
                    dopis = True
                    i = -1

            i += 1

        klastry.append(kl)
        # sortuj od najwiekszego do najmniejszego
        return sorted(
            klastry, reverse=True, key=lambda x: x.zwrocPow()
        )

    def rysuj(self):
        """Dodaje Layout i rysuje wyciag na stronach layoutu
        """
        self.w_dodaj_layout()
        self.w_strona_tytulowa()

        for x in self.warstwy_klastrow:
            del x
        for y in self.warstwy_dzialek:
            del y

        # zawsze zaczynaj 20 mm od gory strony
        pp = 20
        for gr in self.w_grej:
            pp = self.w_rysuj_grej(gr, pp)

        self.w_generuj_slownik(pp)
        self.w_dodaj_nr_stron()
        # self.w_dodaj_do_pazystej()

    def w_rysuj_grej(self, grej, pp):
        """Rysuje wszystkie klastry na kolejnych stronach wyciągu"""

        # lista klastrow z wydzieleniami na Ls w tej grej
        if self.bez_mapy:
            kl = Klaster()
            kl.skala = self.skala
            [kl.dodaj_wydz(x) for x in self.w_sl_fwy_grej[grej]]
            self.lfgr = [kl]
        else:
            self.lfgr = self._klastruj(self.w_sl_fwy_grej[grej])
            # dzew z tej jednostki rejestrowej
            self.dz_temp = self.w_dodaj_warstwe_dzew(self.w_sl_fdz_grej[grej])

        for kl in self.lfgr:
            wys_grej = self.w_oblicz_wys_nag_grej(grej)

            if self.bez_mapy:
                wys_klas = 0
            else:
                # dodaj dzialki to tymczasowej warstwy z tej grej

                wys_klas, ram, poz = self.w_oblicz_wys_klastra(kl)

            geo_wys = ram[3] - ram[1] if not self.bez_mapy else 0
            pp_po_nag_fresh = 20 + wys_grej + 2
            avail_fresh = max(277 - pp_po_nag_fresh, 30)
            skala_fresh = max(geo_wys * 1000 / avail_fresh, 5000) if geo_wys > 0 else 5000
            map_wys_fresh = geo_wys * 1000 / skala_fresh if geo_wys > 0 else 0
            content_needs = wys_grej + map_wys_fresh + 27

            if content_needs + pp > 277 and content_needs + 20 <= 277:
                pp = 20
                self.strona += 1
                self.w_dodaj_strone()

            pp += self.w_generuj_nag_grej(pp, grej) + 2

            # ma byc bez mapy
            if not self.bez_mapy:
                pp += self.w_generuj_klaster(pp, kl, ram, poz) + 2

            if pp > 277:
                pp = pp-277+20
                self.strona += 1
                self.w_dodaj_strone()

            pp = self.w_generuj_tabelke(pp, kl)
            pp += 12

        return pp

    def w_dodaj_layout(self):
        self.uuid = uuid.uuid4()
        self.mn = QgsProject.instance().layoutManager()
        self.lay = QgsPrintLayout(QgsProject.instance())
        self.lay.initializeDefaults()
        self.lay.setName(str(self.uuid))
        self.mn.addLayout(self.lay)
        self.strona = 0
        self.y = 0

    def w_usun_layout(self):
        self.mn.removeLayout(self.lay)
        del self.lay

    def w_generuj_tabelke(self, pp, kl):  # noqa
        """Generuj tabelke na stronie dla podanego klastra"""

        # opis i struktura patrz opis w metodzie
        tab, sl, wys_tab = self.w_przygotuj_tabelke(kl)

        # kolejnosc poszczegolnych wydz
        kolej = [x[:3] for x in tab if x[0] != '']

        # sprawdz czy mozemy wygenerowac naglowek z pierwszym wydzieleniem
        # jezeli nie, to przerzuc na nowa stronę
        try:
            h_wiersza = sl[kolej[0][0]][kolej[0][1]][kolej[0][2]]
        except Exception:
            h_wiersza = 6

        if pp + 27 + h_wiersza > 276:
            pp = 20
            self.strona += 1
            self.w_dodaj_strone()

        pp += self.w_naglowek_tabeli(pp)

        # aktualne adresy:
        anr = ''
        aklu = ''
        aadr = ''
        for i, ti in enumerate(tab):
            if i == 0:
                anr = ti[0]
                aklu = ti[1]
                aadr = ti[2]

            # jezeli zmienia sie aktualne wydz
            trig = False
            if ti[0] not in [anr, '', 'Razem:']:
                anr = ti[0]
                trig = True
            if ti[1] not in [aklu, '']:
                aklu = ti[1]
                trig = True
            if ti[2] not in [aadr, '']:
                aadr = ti[2]
                trig = True

            try:
                wys = sl[anr][aklu][aadr]
            except Exception:
                wys = 6

            if trig and pp + wys > 276:
                self.strona += 1
                self.w_dodaj_strone()
                pp = 20 + self.w_naglowek_tabeli(20)

            if trig is False and ti[0] == anr:
                ti[0] == ' '

            pod = False
            # jezeli zmienia sie ktorys aktual, odkresl wiersz
            if ti[0] == 'Razem:':
                pp += self.w_generuj_wiersz(pp, ti, 1)
            else:
                if tab[i+1][2] not in [aadr, '']:
                    pod = 3
                if tab[i+1][1] not in [aklu, '']:
                    pod = 2
                if tab[i+1][0] not in [anr, '']:
                    pod = 1

                pp += self.w_generuj_wiersz(pp, ti, pod)

        return pp

    def w_przygotuj_tabelke(self, kl):  # noqa
        """Zestawia wiersze tabelki do wpisania do wyciagu
        in:
            kl - Klaster()
        zwraca:
            [[12*string], ], sl[dz][klu][oddzwydz]=int(wierszy), sum_wierszy
        """
        # sortuj po adr les
        f1 = sorted([x for x in kl.lista], key=lambda y: y['ADR_LES'])
        # sortuj po klu
        f2 = sorted([x for x in f1], key=lambda y: y['AU']+isNone(y['SQ']))
        # sortuj po dzkat
        try:
            fts = sorted([x for x in f2],
                         key=lambda y: int(y['PARCELNR'].split('/'))[0])
        except Exception:
            fts = sorted([x for x in f2], key=lambda y: y['PARCELNR'])

        ll = []  # lista przetrzymujaca wiersze
        sl = {}  # sl z wysokoscia komorek
        # ostatni wiersz z sumami na klu [pow, miaz, brutto, netto]
        razem = [0, 0, 0, 0]
        wys = 0  # sumaryczna wysokosc tabeli

        for i, f in enumerate(fts):
            # pomin wszystkie sciepki ponizej 0.5 m2
            if f.geometry().area() < 0.5:
                continue

            adrp = f['ADR_LES']
            adr = (adrp[13:17]+adrp[18:22]).replace(' ', '')
            klu = f['AU'] + isNone(f['SQ'])
            nr = f['PARCELNR']

            if nr not in sl:
                sl[nr] = {klu: {adr: 0}}
            elif klu not in sl[nr]:
                sl[nr] = {klu: {adr: 0}}
            elif adr not in sl[nr][klu]:
                sl[nr][klu][adr] = 0
            sl[nr][klu][adr] += 3

            # sprawdz czy cos czasem sie nie powtarza, jak tak to niepowielaj
            li = []
            if i == 0:
                # poprzednie wartosci
                li_pop = [nr, klu, adr, ]
                # aktualne wartosci dla tego wiersza
                li = [nr, klu, adr, ]
            else:
                if nr == li_pop[0]:
                    li.append('')

                    # klu usuwamy tylko w obrebie tej samej dzialki
                    if klu == li_pop[1]:
                        li.append('')
                    else:
                        li_pop[1] = klu
                        li.append(klu)

                else:
                    li_pop[0] = nr
                    li_pop[1] = klu
                    li = [nr, klu]

                li_pop[2] = adr
                li.append(adr)

            aint = self.aint[adrp]
            if aint not in self.zab:
                # konczymy z ta komorka
                li += ['' for x in range(10)]
                ll.append(li)
                wys += 3
                continue
            else:
                # pow rejestrowa dla wydz na klu
                area = f['INTER_POW']*f['LAND_AR']/f['LAND_POW']

                # miazszosc obliczona dla wydz na klu, sumujemy wszystkie gat
                if self.zab[aint]['miazsz'] not in ['', 0, None]:
                    # miaz = round((self.zab[aint]['miazsz']*area) /
                    #              self.zab[aint]['pow'])
                    miaz = round((self.zab[aint]['miazsz']*area))
                else:
                    miaz = 0

                if self.zab[aint]['gat'] not in self.lgat and \
                        self.zab[aint]['gat'] not in [None, '']:
                    self.lgat.append(self.zab[aint]['gat'])

                li += [
                    self.zab[aint]['rpow'],
                    self.zab[aint]['gat'],
                    self.zab[aint]['wiek'],
                    self.zab[aint]['bhd'],
                    self._zaok_do_4(area),
                    str(miaz),
                ]

                # dodaj pow klu do sumy
                razem[0] += area
                razem[1] += miaz

                if len(self.zab[aint]['zab']) == 0:
                    li += ['', '', '']
                    ll.append(li)
                    wys += 3
                    continue

                for i, zi in enumerate(self.zab[aint]['zab']):
                    # skopiuj orginalny poczatek wiersza
                    if i == 0:
                        liz = [xx for xx in li]
                    else:
                        liz = ['', '', '', '', '', '', '', '', '', ]

                    # dodaj nazwe zabiegu
                    liz.append(zi[0])
                    if zi[0] not in self.lzab:
                        self.lzab.append(zi[0])

                    # oblicz pow zab na klu
                    area_proc = zi[1]
                    if zi[1] is None:
                        area_proc = 100

                    pzab = (area*area_proc) / 100
                    liz.append(self._zaok_do_4(pzab))

                    brutto = ''
                    if isinstance(zi[3], int):
                        brutto = int(round((area*zi[3])/self.zab[aint]['pow']))
                    netto = ''
                    if isinstance(zi[4], int):
                        netto = int(round((area*zi[4])/self.zab[aint]['pow']))

                    if brutto != '' and netto != '':
                        liz.append(str(brutto)+'/'+str(netto))
                    else:
                        liz.append('')

                    if brutto != '':
                        razem[2] += brutto
                    if netto != '':
                        razem[3] += netto

                    ll.append(liz)
                    if i > 0:
                        wys += 3
                        sl[nr][klu][adr] += 3

        ll.append(['Razem:', '', '', '', '', '', '', self._zaok_do_4(razem[0]),
                   str(razem[1]), '', '', str(razem[2])+'/'+str(razem[3])])
        wys += 3
        return ll, sl, wys

    def w_generuj_slownik(self, pp):
        """ Generuj skrocony slownik opisowy dla gatunkow i zabiegow wyst.
        w generowanych jedn. grej.
        """
        mrek = max([len(self.lgat), len(self.lzab)])
        wys = mrek * 3 + 3

        if pp + wys > 280:
            pp = 20
            self.strona += 1
            self.w_dodaj_strone()

        lab = self._dodaj_lab(20, pp, 35, 3, 'Słownik gatunków z wyciągu:')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(100, pp, 35, 3, 'Słownik zabiegów z wyciągu:')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        self.lzab.sort()
        self.lgat.sort()

        pp += 3
        for i in range(mrek):
            if i < len(self.lgat):
                gi = self.lgat[i]
                if gi in self.sl_gat:
                    gi = gi + ' - ' + self.sl_gat[gi]
                else:
                    gi = gi + ' - (Brak w bazie)'
                lab = self._dodaj_lab(25, pp+3*i, 80, 3, gi)
                lab.setFont(QFont("Arial", 6, QFont.Normal))
                lab.setHAlign(Qt.AlignLeft)
                self.lay.addItem(lab)

            if i < len(self.lzab):
                zi = self.lzab[i]
                if zi in self.sl_zab:
                    zi = zi + ' - ' + self.sl_zab[zi]
                else:
                    zi = zi + ' - (Brak w bazie)'
                lab = self._dodaj_lab(105, pp+3*i, 80, 3, zi)
                lab.setFont(QFont("Arial", 6, QFont.Normal))
                lab.setHAlign(Qt.AlignLeft)
                self.lay.addItem(lab)

    def _zaok_do_4(self, a):
        area_s = str(round(a, 4))
        if '.' in area_s:
            area_s += (4-len(area_s.split('.')[1])) * '0'
        else:
            area_s += '.0000'

        return area_s.replace('.', ',')

    def w_dodaj_strone(self):
        pages = self.lay.pageCollection()
        page = QgsLayoutItemPage(self.lay)
        page.setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)
        pages.addPage(page)

    def w_dodaj_do_pazystej(self):
        """ sprawdz czy liczba strone w wyciagu jest pazysta, jesli nie
        dodaj pusta
        """

        if self.strona % 2 == 0:
            return

        self.w_dodaj_strone()

    def w_strona_tytulowa(self):
        pages = self.lay.pageCollection()
        pages.clear()
        self.w_dodaj_strone()

        # nazwa starostwa
        lab = self._dodaj_lab(self.star_x, self.star_y, 45, 10, self.star)
        lab.setFont(QFont("Arial", 8, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        # adres starostwa
        lab = self._dodaj_lab(
            self.star_x, self.star_y+10, 45, 10, self.star_adr
        )
        lab.setFont(QFont("Arial", 8, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        # wlasciciel
        lab = self._dodaj_lab(self.wl_x, self.wl_y, 35, 2, 'Sz. Pan/Pani')
        lab.setFont(QFont("Arial", 5, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        kred = ' '.join([self.sl_wl[self.addr]['opis']['nazwisko'],
                         isNone(self.sl_wl[self.addr]['opis']['imie'])])
        self.kred = kred

        lab = self._dodaj_lab(self.wl_x-10, self.wl_y+2.5, 90, 6, kred)
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        _adr = ''
        if self.sl_wl[self.addr]['opis']['miejscowosc'] != '':
            _adr += self.sl_wl[self.addr]['opis']['miejscowosc'] + ', '
        if self.sl_wl[self.addr]['opis']['ulica'] != '':
            _adr += self.sl_wl[self.addr]['opis']['ulica'].replace(
                'd:', '').replace('l:', '') + '\n'

        _adr += self.sl_wl[self.addr]['opis']['kod'] + ' '
        if self.sl_wl[self.addr]['opis']['poczta'] != '':
            _adr += self.sl_wl[self.addr]['opis']['poczta'].strip('\n\t\r ')
        else:
            _adr += \
                self.sl_wl[self.addr]['opis']['miejscowosc'].strip('\n\t\r ')

        lab = self._dodaj_lab(self.wl_x-10, self.wl_y+10, 90, 9, _adr)
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        # Wyciag z planu UPUL
        lab = self._dodaj_lab(
            20, 160, 170, 8,
            'Wyciąg z uproszczonego planu urządzenia lasu'
        )
        lab.setFont(QFont("Arial", 9, QFont.Bold))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        # tytul
        lab = self._dodaj_lab(
            20, 170, 170, 8,
            'Zadania w zakresie gospodarki leśnej dla właścicieli'
        )
        lab.setFont(QFont("Arial", 9, QFont.Bold))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(
            20, 180, 170, 8,
            'na okres od ' + str(self.od) + ' do ' + str(self.do)
        )
        lab.setFont(QFont("Arial", 8, QFont.Bold))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(
            20, 200, 70, 8, 'Przygotowano dla numerów rejestrowych:'
        )
        lab.setFont(QFont("Arial", 8, QFont.Bold))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(
            20, 208, 90, 70, '\n'.join(self.sl_wl[self.addr]['grej'])
        )
        lab.setFont(QFont("Arial", 7, QFont.Bold))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        # dodaj kolejna strone
        self.w_dodaj_strone()
        self.strona += 1

    def w_naglowek_tabeli(self, przes):
        """ rysuje naglowek tabeli z opisem wydzielenia, przesunieta od gornej
        krawedzi o wartosc podana przez uzytkownika"""

        # wysokosc naglowka 27 mm
        pp = przes - 30.5

        lab = self._dodaj_lab(51, 31+pp, 54, 3.2, 'Opis wydzielenia')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(125, 31+pp, 64, 3.2, 'Wskazania gospodarcze')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(20, 35.6+pp, 15, 3.2, 'Nr działki')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(35, 35.6+pp, 10, 3.2, 'Użytek')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(45, 34.2+pp, 6, 6, 'Oddz.\nwydz.')
        lab.setFont(QFont("Arial", 6, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(51, 35.6+pp, 14, 3.2, 'R. pow.')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(65, 35.6+pp, 10, 3.2, 'Gat.')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(75, 35.6+pp, 10, 3.2, 'Wiek')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(85, 35.6+pp, 7, 3.2, 'Bonit.')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(92, 35.6+pp, 13, 3.2, 'Pow. [ha]')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(105, 34.2+pp, 20, 6, 'Miąższość\n[m³] brutto')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(125, 35.6+pp, 20, 3.2, 'Zabieg')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(145, 35.6+pp, 20, 3.2, 'Pow. [ha]')
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(
            165, 34.2+pp, 25, 6, 'Miąższość [m³]\nBrutto/Netto'
        )
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignCenter)
        self.lay.addItem(lab)

        # numerki kolumn
        tab_nr = [
            [20, 15], [35, 10], [45, 6], [51, 14], [65, 10], [75, 10], [85, 7],
            [92, 13], [105, 20], [125, 20], [145, 25], [165, 25],
        ]

        for i, ti in enumerate(tab_nr):
            lab = self._dodaj_lab(ti[0], 40.33+pp, ti[1], 2.5, str(i+1))
            lab.setFont(QFont("Arial", 5, QFont.Normal))
            lab.setHAlign(Qt.AlignCenter)
            self.lay.addItem(lab)

        # dodaj linie oddzielajace w naglowku
        poly = QPolygonF()
        poly.append(QPointF(53.9, (self.strona*307)+34.187+pp))
        poly.append(QPointF(121, (self.strona*307)+pp+34.187))
        line1 = QgsLayoutItemPolyline(poly, self.lay)
        self.lay.addItem(line1)

        poly = QPolygonF()
        poly.append(QPointF(127, (self.strona*307)+34.187+pp))
        poly.append(QPointF(190, (self.strona*307)+pp+34.187))
        line2 = QgsLayoutItemPolyline(poly, self.lay)
        self.lay.addItem(line2)

        poly = QPolygonF()
        poly.append(QPointF(20, (self.strona*307)+40.2+pp))
        poly.append(QPointF(190, (self.strona*307)+pp+40.2))
        line3 = QgsLayoutItemPolyline(poly, self.lay)
        self.lay.addItem(line3)

        poly = QPolygonF()
        poly.append(QPointF(20, (self.strona*307)+42.689+pp))
        poly.append(QPointF(190, (self.strona*307)+pp+42.689))
        line3 = QgsLayoutItemPolyline(poly, self.lay)
        self.lay.addItem(line3)

        return 12

    def w_dodaj_warstwe_klastra(self, ll):
        """dodaj do projektu nowa warstwe z uzytkami tylko dla tego klastra
        ll - lista featurkow z inter
        zwraca:
            QgsVectorLayer()
        """

        ls_wyb = QgsVectorLayer(
            "MultiPolygon?crs=epsg:2180", 'ls_wybrane', 'memory'
        )
        ls_wyb.startEditing()
        ls_wyb.dataProvider().addAttributes(
            self.inter.dataProvider().fields().toList()
        )
        ls_wyb.updateFields()
        ls_wyb.dataProvider().addFeatures(ll)
        ls_wyb.commitChanges()

        plug_dir = os.path.dirname(__file__)
        ls_wyb.loadNamedStyle(
            os.path.join(plug_dir, '..', 'qml', 'wyc_LS_wyb.qml'))

        self.warstwy_klastrow.append(ls_wyb)
        return ls_wyb

    def w_dodaj_warstwe_dzew(self, ll):
        """dodaje do projektu nowa warstwe z uzytkami tylko dla jed rej
        ll - lista z feats
        zwraca:
            QgsVectorLayer
        """

        dz_wyb = QgsVectorLayer(
            "MultiPolygon?crs=epsg:2180", 'dz_wybrane', 'memory'
        )
        dz_wyb.startEditing()
        dz_wyb.dataProvider().addAttributes(
            self.dz.dataProvider().fields().toList()
        )
        dz_wyb.updateFields()
        dz_wyb.dataProvider().addFeatures(ll)
        dz_wyb.commitChanges()

        plug_dir = os.path.dirname(__file__)
        dz_wyb.loadNamedStyle(
            os.path.join(plug_dir, '..', 'qml', 'wyc_DZKAT_wyb.qml'))

        self.warstwy_dzialek.append(dz_wyb)
        return dz_wyb

    def w_dodaj_nr_stron(self):
        """Uruchamiać po wygenerowaniu całego wyciagu """
        for si in range(0, self.strona+1):
            lab = self._dodaj_lab(
                170, 10, 20.8, 5,
                'Strona '+str(si+1)+'/'+str(self.strona+1),
                st=si)
            lab.setFont(QFont("Arial", 6, QFont.Normal))
            lab.setHAlign(Qt.AlignCenter)
            self.lay.addItem(lab)

    def _dodaj_lab(self, x, y, w, h, t, st=-1):
        lab = QgsLayoutItemLabel(self.lay)
        lab.setReferencePoint(QgsLayoutItem.UpperLeft)
        lab.setText(str(t))
        lab.setFontColor(QColor("#000000"))
        if st == -1:
            st = self.strona
        lab.attemptResize(
           QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
        lab.attemptMove(
            QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters),
            page=st)
        return lab

    def w_oblicz_wys_nag_grej(self, grej):
        """Zwraca int z wysokoscia naglowka dla podanej grej
        gggoooo.grej
        """
        wwlas = []
        _obr, _gr = grej.split('.')
        if _obr in self.sl_gr:
            if _gr in self.sl_gr[_obr]:
                for x in self.sl_gr[_obr][_gr]['wl']:
                    if x in self.sl_wl and x != self.addr:
                        ww = self.sl_wl[x]['opis']['nazwisko'] + ' '
                        ww += self.sl_wl[x]['opis']['imie'] + ' ['
                        ww += self.sl_wl[x]['udzial'][grej] + ']'
                        wwlas.append(ww)

        if len(wwlas) == 0:
            return 13

        ww_wys = 3 * int(len(wwlas)/3)
        if len(wwlas) % 3 > 0:
            ww_wys += 3
        return 13 + 3 + ww_wys

    def w_generuj_nag_grej(self, pp, grej):  # noqa
        """Generuje nagloweka dla jednostki rejestrowej w przesunieciu od gory
        strony podanym przez uzytkownika.
        grej w postaci: GGGOOOO.NR
        pp - przesuniecie od gory mm
        """

        ff = self.lfgr[0]
        adr_adm = '-'.join(list(map(str, [ff.woj, ff.pow, ff.gm, ff.obr])))
        if str(ff.gm) + str(ff.obr) in self.obr:
            adr_adm += ' - ' + self.obr[str(ff.gm) + str(ff.obr)]

        nazwisko = self.sl_wl[self.addr]['opis']['nazwisko'] + ' ' + \
            self.sl_wl[self.addr]['opis']['imie']
        sec = self.sl_wl[self.addr]['opis']['wspl']
        if sec not in ['', None, 'NULL', 0]:
            # if sec in self.wl_all[sec]:
            nazwisko += ', ' + self.wl_all[sec]

        adres = ''
        if self.sl_wl[self.addr]['opis']['ulica'] != '':
            adres += self.sl_wl[self.addr]['opis']['ulica'] + ', '

        adres += self.sl_wl[self.addr]['opis']['kod'] + ' ' +  \
            self.sl_wl[self.addr]['opis']['miejscowosc']

        udzial = ''
        if grej in self.sl_wl[self.addr]['udzial']:
            udzial = self.sl_wl[self.addr]['udzial'][grej]

        wwlas = []
        _obr, _gr = grej.split('.')
        if _obr in self.sl_gr:
            if _gr in self.sl_gr[_obr]:
                for x in self.sl_gr[_obr][_gr]['wl']:
                    if x in self.sl_wl and x != self.addr:
                        ww = self.sl_wl[x]['opis']['nazwisko'] + ' '
                        ww += self.sl_wl[x]['opis']['imie']
                        if len(ww) > 20:
                            ww = self.sl_wl[x]['opis']['nazwisko'] + ' '
                            ims = self.sl_wl[x]['opis']['imie'].strip().split(' ')
                            if len(ims) > 0:
                                ww += '. '.join(im[0] for im in ims).strip()
                        ww += ' [' + self.sl_wl[x]['udzial'][grej] + ']'
                        wwlas.append(ww)

        # nazwa obiektu
        lab = self._dodaj_lab(20, 1.5+pp, 10, 3, 'obiekt:', st=self.strona)
        lab.setFont(QFont("Arial Narrow", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(30, 0+pp, 90, 5, adr_adm, st=self.strona)
        lab.setFont(QFont("Arial", 10, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        # nazwisko i adres wlasciciela
        lab = self._dodaj_lab(20, 8.5+pp, 10, 3, 'właściciel:', st=self.strona)
        lab.setFont(QFont("Arial Narrow", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(30, 5+pp, 90, 5, nazwisko, st=self.strona)
        lab.setFont(QFont("Arial", 10, QFont.Bold))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(30, 10+pp, 90, 3, adres, st=self.strona)
        lab.setFont(QFont("Arial", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        # Nr rejstrowy
        lab = self._dodaj_lab(125, 2+pp, 10, 3, 'Nr rej.:', st=self.strona)
        lab.setFont(QFont("Arial Narrow", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(
            138, 1+pp, 30, 4, grej.split('.')[-1], st=self.strona
        )
        lab.setFont(QFont("Arial", 10, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        # udzial
        lab = self._dodaj_lab(125, 7+pp, 10, 3, 'udział:', st=self.strona)
        lab.setFont(QFont("Arial Narrow", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        lab = self._dodaj_lab(138, 6+pp, 30, 4, udzial, st=self.strona)
        lab.setFont(QFont("Arial", 10, QFont.Bold))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        if not len(wwlas):
            return 13

        lab = self._dodaj_lab(
            20, 13.5+pp, 20, 3, 'współwłasność:', st=self.strona
        )
        lab.setFont(QFont("Arial Narrow", 7, QFont.Normal))
        lab.setHAlign(Qt.AlignLeft)
        self.lay.addItem(lab)

        # przesuniecia poszczegolnych kolumn wspolw
        offset = [25, 79, 133]

        kol = 0
        wiersz = 0
        for i, wi in enumerate(wwlas):
            lab = self._dodaj_lab(
                offset[kol], 16.65+pp+wiersz, 51, 3,
                str(i+1)+'. '+wi, st=self.strona
            )
            lab.setFont(QFont("Arial", 7, QFont.Normal))
            lab.setHAlign(Qt.AlignLeft)
            self.lay.addItem(lab)

            kol += 1
            if kol == 3:
                wiersz += 3
            kol = 0 if kol == 3 else kol

        ww_wys = 3 * int(len(wwlas)/3)
        if len(wwlas) % 3 > 0:
            ww_wys += 3
        return 13 + 3 + ww_wys

    def w_oblicz_wys_klastra(self, kl):
        """Oblicza wysokosc podanego klastra w mm
        zwraca:
            wys (int),
            ramkę z wsp [xmnin, ymin, xmax, ymax],
            poz leg
        """
        ramka, poz = kl.ustaw_ramke()

        return int((ramka[3]-ramka[1])/5), ramka, poz

    def _kasuj_feats(self, x):
        """Kasuje wszystkie feats z warstwy
        """

        x.startEditing()
        fids = [y.id() for y in x.getFeatures()]
        x.dataProvider().deleteFeatures(fids)
        x.commitChanges()

    def w_generuj_klaster(self, pp, kl, ram=[], pozycja=''):
        """Generuje mapę dla podanego klastra na podanej wysokosci
        pp - int
        kl - Klaster()
        """

        war = self.w_dodaj_warstwe_klastra(kl.lista)

        if ram != [] and pozycja != '':
            ramka = list(ram)
            poz = pozycja
        else:
            r, poz = kl.ustaw_ramke()
            ramka = list(r)

        geo_wys = ramka[3] - ramka[1]          # geograficzna wysokość [m]
        avail_wys = max(277 - pp, 30)           # dostępna wysokość na stronie [mm]

        # Skala tak żeby mapa zmieściła się na stronie; minimum 1:5000
        skala = max(geo_wys * 1000 / avail_wys, 5000)

        # Rozszerz zasięg X żeby mapa zawsze wypełniała pełne 174mm
        geo_szer_174 = skala * 174 / 1000
        x_sr = (ramka[0] + ramka[2]) / 2
        ramka[0] = x_sr - geo_szer_174 / 2
        ramka[2] = x_sr + geo_szer_174 / 2

        map_wys = geo_wys * 1000 / skala       # rzeczywista wysokość mapy [mm]

        wyn_it = QgsLayoutItemMap(self.lay)
        wyn_it.setLayers([self.wydz, war, self.dz_temp, self.ewid, ])
        wyn_it.attemptMove(
            QgsLayoutPoint(20, pp, QgsUnitTypes.LayoutMillimeters),
            page=self.strona
        )
        wyn_it.attemptResize(
            QgsLayoutSize(174, map_wys, QgsUnitTypes.LayoutMillimeters)
        )
        wyn_it.setExtent(QgsRectangle(*ramka))
        wyn_it.setScale(skala)
        wyn_it.setId('wyn '+str(int(ramka[0])))
        wyn_it.setBackgroundColor(QColor('white'))
        wyn_it.setFrameEnabled(True)
        self.lay.addItem(wyn_it)

        # dodaj legende
        if poz.upper() == 'LD':
            legx = 20
            legy = pp + map_wys - 30
        elif poz.upper() == 'PD':
            legx = 158
            legy = pp + map_wys - 30
        elif poz.upper() == 'PG':
            legx = 158
            legy = pp
        if poz.upper() == 'LG':
            legx = 20
            legy = pp
        elif poz.upper() == 'XX':
            legx = -40
            legy = 0

        h = QgsLayoutItemPicture(self.lay)
        h.attemptResize(
            QgsLayoutSize(36, 30, QgsUnitTypes.LayoutMillimeters))
        h.attemptMove(
            QgsLayoutPoint(legx, legy, QgsUnitTypes.LayoutMillimeters),
            page=self.strona)
        h.setPicturePath(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), '..', 'jpg', 'wyciag_leg.jpg'
                )
            )
        )
        self.lay.addItem(h)

        return map_wys

    def w_generuj_wiersz(self, pp, zaw, pod=False):
        """ generuj linie tabeli ze wskazowkami
        pp - przesuniecie (int)
        zaw - lista z zawartoscia wiersza (len=12)
        pod - podkreslenie wiersza (1-calego, 2-od uzytku, 3-od oddz)
        """

        # poczatek i dlugos kolumny
        # wysokosc ustawiona dla kazdej komorki na 3.2
        kol = [[20, 15], [35, 10], [45, 6], [51, 14], [65, 10], [75, 10],
               [85, 7], [92, 13], [105, 20], [125, 20], [145, 20], [165, 25]]

        if len(zaw) != 12:
            return 0

        for i, zz in enumerate(zaw):
            if zz == '':
                continue
            lab = self._dodaj_lab(kol[i][0], pp, kol[i][1], 3.2, zz)
            lab.setFont(QFont("Arial", 7, QFont.Normal))
            lab.setHAlign(Qt.AlignCenter)
            self.lay.addItem(lab)

        if not pod:
            return 3

        poly = QPolygonF()
        pocz = 20
        if pod == 2:
            pocz = 35
        if pod == 3:
            pocz = 45

        poly.append(QPointF(pocz, (self.strona*307)+pp+3))
        poly.append(QPointF(190, (self.strona*307)+pp+3))
        line = QgsLayoutItemPolyline(poly, self.lay)
        self.lay.addItem(line)

        return 3


class GenerujWyciagi(Struktura, Wyciag):
    def __init__(self, iface):
        self.iface = iface
        self.kat = ''

        # lista addr_nr z bazy do wygenerowania
        self.lista_addr = []
        # lista z błędnymi numerami addr_id, nie zostały wygenerowane
        self.bledy_generowania = []

        self.minOdl = 250
        self.skala = 5000

    def generowanie(self):
        """Metoda zbiorcza - auto"""

        if not self.pobierz_dane():
            return False

        ok, mess = self.sprawdz_wejsciowe()
        if not ok:
            self.iface.messageBar().pushMessage(
                'Błąd wejsciowy', mess, Qgis.Critical)
            return
        self.iface.messageBar().pushMessage(
            'Generuję wyciągi', '...', Qgis.Success)

        self.przygotuj_strukture_baza()
        self.przygotuj_strukture_shp()
        self.przygotuj_strukture_eks()

        l_wl = []
        if self.wszystkie:
            l_wl = sorted([x for x in self.sl_wl.keys()])
        else:
            l_wl = sorted([x for x in self.lista_addr if int(x) in self.sl_wl])

        for adr in l_wl:
            try:
                self.przygotuj_wyciag(int(adr))
                self.rysuj()
                self.eksportuj_wyciag()
            except Exception:
                QgsMessageLog.logMessage(
                    f'Błąd wyciągu addr_id={adr}:\n' + traceback.format_exc(),
                    'Las-R', Qgis.Critical)
                self.bledy_generowania.append(adr)

        self.iface.messageBar().clearWidgets()
        if len(self.bledy_generowania) > 0:
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało wygenerować się wszystkich wyciągów'
                ' (błędy podczas generowania wyciągów: '
                f'{len(self.bledy_generowania)})'
                '- pełna lista addr_id w logu Las-R',
                Qgis.Warning)
            QgsMessageLog.logMessage(
                'Niewygenerowane numery właścicieli: ' +
                ', '.join([str(x) for x in self.bledy_generowania]),
                'Las-R', Qgis.Warning)
        else:
            self.iface.messageBar().pushMessage(
                'OK', 'Wygenerowano wszystkie zadane wyciągi ' +
                f'[{len(l_wl)}]',
                Qgis.Success)

    def pobierz_dane(self):
        """Pobiera dane od uzytkownika przez wyswietlone okno dialogowe"""
        dd = PobierzDane()
        dd.exec_()

        if not dd.kontynuuj:
            return False

        self.baza = Baza(dd.baza)
        self.kat = os.path.dirname(dd.baza)

        self.star = dd.starostwo.replace('Powiatowe', 'Powiatowe\n')
        self.star_adr = dd.star_adr
        self.star_x = dd.poz_st_x
        self.star_y = dd.poz_st_y

        self.wl_x = dd.poz_wl_x
        self.wl_y = dd.poz_wl_y

        self.od = dd.od
        self.do = dd.do

        self.bez_mapy = dd.bez_mapy

        self.grupowanie_wyciagow = dd.grupowanie_wyciagow

        self.wszystkie = True
        if not dd.wszystkie:
            self.wszystkie = False
            self.lista_addr = dd.lista_addr

        return True

    def sprawdz_wejsciowe(self):
        """Sprawdz czy w katalogu z baza jest odpowiednia struktura i warstwy
        """
        if not os.path.isdir(os.path.join(self.kat, 'shp')):
            return False, 'Brak katalogu shp?? (bez warstw ani rusz)'

        if not os.path.isfile(os.path.join(self.kat, 'shp', 'LS.shp')):
            return False, 'Brak warstwy LS w katalogu shp'

        if not os.path.isfile(os.path.join(self.kat, 'shp', 'DZKAT.shp')):
            return False, 'Brak warstwy DZKAT w katalogu shp'

        if not os.path.isfile(os.path.join(self.kat, 'shp', 'WYDZ.shp')):
            return False, 'Brak warstwy WYDZ w katalogu shp'

        if not self.baza.polacz():
            return False, 'Brak możliwości połączenia się z bazą'

        self.przygotuj_strukture_baza()
        return True, ''


class Klaster(object):
    def __init__(self, zasieg=800):
        self.ustawiony = False  # czy klaster jest sprawdzony do mapy
        self.zas = zasieg  # zdefiniowany max zasieg klastrowania
        self.max_szer = 870
        self.xmin = 9999999
        self.xmax = 0
        self.ymin = 9999999
        self.ymax = 0
        self.skala = 5000
        self.lista = []

        self.woj = ''
        self.pow = ''
        self.gm = ''
        self.obr = ''

        # wspolrzedne lewego gornego rogu klastra do wrysowania na mapie,
        # wspolrzedne sa w metrach epsg:2180
        self.xpocz = 0
        self.ypocz = 0

    def dodaj_wydz(self, feat):
        """
        Dodaje wydz do klastra
        feat = QgsFeature
        """

        tab = [
            feat.geometry().boundingBox().xMinimum(),
            feat.geometry().boundingBox().yMinimum(),
            feat.geometry().boundingBox().xMaximum(),
            feat.geometry().boundingBox().yMaximum(),
        ]

        if len(self.lista) == 0:
            nazwy = [x.name() for x in feat.fields().toList()]
            if 'COUNTY' in nazwy:
                self.woj = feat['COUNTY']
            if 'DISTRICT' in nazwy:
                self.pow = feat['DISTRICT']
            if 'MUNICIP' in nazwy:
                self.gm = feat['MUNICIP']
            if 'COMMUNITY' in nazwy:
                self.obr = feat['COMMUNITY']

        self.lista.append(feat)
        if self.xmin > tab[0]:
            self.xmin = tab[0]
        if self.ymin > tab[1]:
            self.ymin = tab[1]
        if self.ymax < tab[3]:
            self.ymax = tab[3]
        if self.xmax < tab[2]:
            self.xmax = tab[2]
        return True

    def kwalifikuj(self, feat):
        """
        Sprawdza czy wydzielenia kwalifikuje sie do klastra
        feat = QgsFeature
        """
        tab = [
            feat.geometry().boundingBox().xMinimum(),
            feat.geometry().boundingBox().yMinimum(),
            feat.geometry().boundingBox().xMaximum(),
            feat.geometry().boundingBox().yMaximum(),
        ]

        odl = []
        if tab[0] > self.xmax:
            odl.append(tab[0]-self.xmax)
        if tab[1] > self.ymax:
            odl.append(tab[1]-self.ymax)
        if tab[2] < self.xmin:
            odl.append(self.xmin-tab[2])
        if tab[3] < self.ymin:
            odl.append(self.ymin-tab[3])

        # jezeli nie dodano zadnej odl, wydzielenie jest juz w zasiegu klastra
        if len(odl) == 0:
            odl = [0]

        if max(odl) < self.zas:
            return True

        # wyjatek, gdy featurek jest wiekszy niz spodziewany zasieg i tak do
        # dodaj, gdzies trzeba go umiescic...
        if max(odl) > self.zas and len(self.lista) == 0:
            return True

        return False

    def zwrocPow(self):
        return (self.xmax-self.xmin) * (self.ymax-self.ymin)

    def zwrocWymiary(self):
        return [self.xmax-self.xmin, self.ymax-self.ymin]

    def zwrocZakres(self):
        return [self.xmin, self.ymin, self.xmax, self.ymax]

    def ustaw_ramke(self):
        """ Ustawia rozmiar ramki tak aby dobrze wygladala na A4 i miescila sie
        jako tako na stronie
        zwraca [xmin, ymin, xmax, ymax],
        pozycje leg (int)  # 1-LD, 2-PD, 3-LG, 4-PG, 9-xx
        """
        _xmn = 0
        _ymn = 0
        _xmx = 0
        _ymx = 0

        szer, wys = self.zwrocWymiary()

        # ustaw pozycje klastra domyslnie przy prawej krawedzi, nie sprawdzam
        # szerokosci bo to zostalo sprawdzone przy klasyfikowaniu
        if szer < 680:
            pop2 = (690 - szer) / 2
            _xmn = self.xmin - 180 - pop2
            _xmx = self.xmax + pop2
        else:
            _xmn = self.xmin - (870-(self.xmax-self.xmin)-50)
            _xmx = self.xmax + 50

        if wys < 350:
            popr = (350 - wys) / 2
            _ymx = self.ymax + popr + 10
            _ymn = self.ymin - popr - 10
        else:
            _ymn = self.ymin - 50
            _ymx = self.ymax + 50

        # legenda w LD, nie ma co sprawdzac preciec bo miesci sie poza obsz
        if szer < 681 and wys < 350:
            return [_xmn, _ymn, _xmx, _ymx], 'LD'

        lok = 'xx'
        while _ymx - _ymn < 870:
            wyn = self._sprawdz_leg([_xmn, _ymn, _xmx, _ymx])

            # TODO: przetestowac najprostszy scenariusz a potem ew dopisac
            # przesuwanie wydzielen do przeciwleglych krawedzi w stosunku do
            # testowanej pozycji legendy...
            if wyn is False:
                _ymn -= 50
            else:
                lok = wyn
                break

        return [_xmn, self.ymin-10, _xmx, self.ymax+10], lok

    def _sprawdz_leg(self, tab):
        """Sprawdz czy podanej tablicy zasiegu, uda sie umiescic legende w
        ktoryms rogu i nie bedzie przykrywac wydzielen z tego klastra
        tab - [xmin, ymin, xmax, ymax]
        return True
        """

        # lokalizacje legendy w podanym zakresie
        lok = {0: 'LD', 1: 'PD', 2: 'LG', 3: 'PG'}

        r_ld = QgsRectangle(tab[0], tab[1], tab[0]+181, tab[1]+151)
        r_pd = QgsRectangle(tab[2]-181, tab[1], tab[2], tab[1]+151)
        r_lg = QgsRectangle(tab[0], tab[3]-151, tab[0]+181, tab[3])
        r_pg = QgsRectangle(tab[2]-181, tab[1]-151, tab[2], tab[3])

        # [ld, pd, lg, pg]
        legs = [r_ld, r_pd, r_lg, r_pg]
        trig = [False, False, False, False, ]

        for feat in self.lista:
            for i, ll in enumerate(legs):
                if feat.geometry().intersects(ll):
                    trig[i] = True

        for i, val in enumerate(trig):
            if not val:
                return lok[i]

        return False


class PobierzDane(QDialog):
    def __init__(self, k=False, d=False):
        super(PobierzDane, self).__init__()

        self.kontynuuj = False
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.baza = ''
        # self.baza = '/home/pawel/temp/PLONSK_WYCIAGI/baza.sqlite'
        # self.baza = '/home/pawel/temp/cieszyn/baza.sqlite'

        self.ui.lineEdit_baza.setText('')
        self.poz_st_x = 20
        self.poz_st_y = 30
        self.starostwo = 'Starostwo Powiatowe w .....'
        self.star_adr = '[Adres Starostwa]'

        self.poz_wl_x = 120
        self.poz_wl_y = 90

        self.ui.lineEdit_od.setText(
            '-'.join([str(datetime.datetime.now().year+1), '01', '01'])
        )
        self.ui.lineEdit_do.setText(
            '-'.join([str(datetime.datetime.now().year+10), '12', '31'])
        )

        self.od = str(datetime.datetime.now().year+1) + '-01-01'
        self.do = str(datetime.datetime.now().year+9) + '-12-31'

        self.ui.pushButton_porzuc.clicked.connect(self.porzuc)
        self.ui.pushButton_ok.clicked.connect(self.ok)
        self.ui.pushButton_baza.clicked.connect(self.wskaz_baze)

    def porzuc(self):
        self.hide()

    def ok(self):
        self.baza = self.ui.lineEdit_baza.text()

        self.starostwo = self.ui.lineEdit_starostwo.text()
        self.star_adr = self.ui.lineEdit_star_adr.text()

        self.poz_st_x = self.ui.spinBox_poz_st_x.value()
        self.poz_st_y = self.ui.spinBox_poz_st_y.value()

        self.poz_wl_x = self.ui.spinBox_poz_wl_x.value()
        self.poz_wl_y = self.ui.spinBox_poz_wl_y.value()

        self.od = self.ui.lineEdit_od.text()
        self.do = self.ui.lineEdit_do.text()

        self.bez_mapy = not self.ui.checkBox_mapy.isChecked()

        self.grupowanie_wyciagow = self.ui.radioButton_gr_tak.isChecked()

        self.wszystkie = False
        if self.ui.radioButton_wszyscy.isChecked():
            self.wszystkie = True
        elif self.ui.radioButton_wybrani.isChecked():
            self.lista_addr = self.ui.lineEdit_wybrani.text().split(',')
        elif self.ui.radioButton_zakres.isChecked():
            wl_od = self.ui.lineEdit_wl_od.text()
            wl_do = self.ui.lineEdit_wl_do.text()

            if wl_od.isdigit() and wl_do.isdigit():
                self.lista_addr = [x for x in range(int(wl_od), int(wl_do)+1)]
            else:
                message = QMessageBox()
                message.setIcon(QMessageBox.Information)
                message.setWindowTitle('Błąd')
                message.setText(
                    'Zakresy addr_nr muszą być liczbami całkowitymi!')
                message.addButton(u"Zamknij", QMessageBox.ActionRole)
                message.exec_()
                return

        self.kontynuuj = True
        self.hide()

    def wskaz_baze(self):
        sc = QFileDialog().getOpenFileName(
            self,
            'Wskaż bazę Taksatora',
            '',
            "Access MDB (*.mdb);;SQLite (*.sqlite)")[0]

        if sc != '':
            self.ui.lineEdit_baza.setText(sc)
