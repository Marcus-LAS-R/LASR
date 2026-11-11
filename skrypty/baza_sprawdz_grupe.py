# -*- coding: utf-8 -*-
"""Sprawdź poprawność grupy (menu Aktualizacja UPUL, po "Utwórz ADR_LES dla
starych wydzieleń").

Grupa (forma własności, pozycje [11:13] adresu leśnego) w grafice pochodzi z
nowej ewidencji (LS -> WYDZ), a w bazie bywa stara (np. z BDL zawsze 10) -
wtedy kolejne skrypty (Dopisz wydzielenia do bazy, Usuń nadmiarowe WYDZ)
traktują stare i nowe adresy jako różne wydzielenia. Skrypt:
1. kontrola grafiki (rdzeń "Sprawdź własności w wydzieleniach"): wydzielenie
   na kilku grupach LS albo z grupą inną niż LS pod nim -> warstwa
   BŁĘDY_GRUP, Nawigator i PRZERWANIE (najpierw poprawić grafikę),
2. porównanie adresów z bazy z grafiką z pominięciem grupy
   (grupa_adresu.plan_przemianowania),
3. pytanie i przemianowanie adresów w bazie na grupę z grafiki (kopia
   manipulacyjna przed zmianą, jedna transakcja - Baza.zmien_adresy).
Wyniki (błędy, kolizje, niejednoznaczne, bez pary) - raport TXT i plik dla
Nawigatora błędów w Raporty folderu obiektu."""
import os

from qgis.core import (
    Qgis, QgsFeature, QgsField, QgsMessageLog, QgsProject, QgsRectangle,
    QgsVectorLayer,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout,
)
from .przyciski import QDialogButtonBox, QMessageBox

from .baza_wrapper import Baza
from . import kopie_manipulacyjne
from . import waypointy
from .funkcje import (
    etykiety_warstw, indeks_domyslnej, znajdz_baze_przy, katalog_startowy,
    folder_obiektu,
)
from .grupa_adresu import grupa, plan_przemianowania, bledy_grup
from .shp_spr_wlasn_wydz import przeciecia_wydz_ls
from .znacznik_czasu import znacznik

TYTUL = 'Sprawdź poprawność grupy'


def _puste(v):
    return v is None or str(v).strip().upper() in ('', 'NULL')


class _WyborDialog(QDialog):
    """WYDZ (grafika), LS (grupa z ewidencji) i baza taksatora."""

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(TYTUL)
        self.setMinimumWidth(520)
        self._warstwy = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if isinstance(lyr, QgsVectorLayer)]
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            'Grupa w adresach leśnych bazy zostanie porównana z grupą w '
            'grafice (WYDZ, z nowej ewidencji). Przed tym kontrola, czy '
            'każde wydzielenie leży na jednej grupie z LS.'))

        etykiety = etykiety_warstw(self._warstwy)
        self.cbo_wydz, self.cbo_ls = QComboBox(), QComboBox()
        for etykieta_wiersza, cbo, nazwa in (
                ('Warstwa WYDZ:', self.cbo_wydz, 'WYDZ'),
                ('Warstwa LS:', self.cbo_ls, 'LS')):
            wiersz = QHBoxLayout()
            wiersz.addWidget(QLabel(etykieta_wiersza))
            cbo.addItems(etykiety)
            cbo.setCurrentIndex(indeks_domyslnej(
                self._warstwy, lambda lyr, n=nazwa: lyr.name().upper() == n))
            wiersz.addWidget(cbo, 1)
            lay.addLayout(wiersz)

        wiersz = QHBoxLayout()
        wiersz.addWidget(QLabel('Baza Taksatora:'))
        self.edit_baza = QLineEdit()
        wiersz.addWidget(self.edit_baza, 1)
        btn = QPushButton('Wskaż...')
        btn.clicked.connect(self._wybierz_baze)
        wiersz.addWidget(btn)
        lay.addLayout(wiersz)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.accepted.connect(self.accept)
        przyciski.rejected.connect(self.reject)
        lay.addWidget(przyciski)

        self.cbo_wydz.currentIndexChanged.connect(self._zgadnij_baze)
        self._zgadnij_baze()

    def _wybrana(self, cbo):
        i = cbo.currentIndex()
        return self._warstwy[i] if 0 <= i < len(self._warstwy) else None

    def wydz(self):
        return self._wybrana(self.cbo_wydz)

    def ls(self):
        return self._wybrana(self.cbo_ls)

    def baza_sc(self):
        return self.edit_baza.text().strip() or None

    def _zgadnij_baze(self):
        lyr = self.wydz()
        baza = znajdz_baze_przy(lyr, ('*.mdb',)) if lyr is not None else ''
        if baza:
            self.edit_baza.setText(baza)

    def _wybierz_baze(self):
        start = os.path.dirname(self.edit_baza.text().strip()) or \
            katalog_startowy(self.wydz(), szukaj_bazy=True)
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę Taksatora', start,
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if sc:
            self.edit_baza.setText(os.path.normpath(sc))


class SprawdzGrupe:
    def __init__(self, iface):
        self.iface = iface
        self.wiersze_wp = []
        self.waypointy_sc = None
        self.raport = []

    # ------------------------------------------------------ pomocnicze

    def _wp_xy(self, sekcja, prostokat, crs, opis, kopiuj='', obiekt='',
               blad=''):
        self.wiersze_wp.append(waypointy.wiersz(
            TYTUL, sekcja, waypointy.TYP_XY,
            waypointy.klucz_xy(prostokat, crs.authid()), opis, kopiuj,
            obiekt=obiekt, blad=blad))

    def _wp_adres(self, sekcja, adres, opis, blad=''):
        self.wiersze_wp.append(waypointy.wiersz(
            TYTUL, sekcja, 'ADR_LES', adres, opis, adres,
            obiekt=''.join(str(adres).split()), blad=blad))

    def _zapisz_wyniki(self, wydz):
        kat = folder_obiektu(wydz)
        if not kat:
            return
        kat_rap = waypointy.katalog_raportow(kat)
        czas = znacznik()
        try:
            with open(os.path.join(kat_rap, f'sprawdz_grupe_{czas}.txt'),
                      'w', encoding='utf-8') as plik:
                plik.write('\n'.join(self.raport) + '\n')
            if self.wiersze_wp:
                sc = os.path.join(kat_rap, f'sprawdz_grupe_{czas}.csv')
                waypointy.zapisz(sc, self.wiersze_wp)
                self.waypointy_sc = sc
        except Exception as e:
            self.iface.messageBar().pushWarning(
                TYTUL, 'Nie udało się zapisać raportu: ' + str(e))

    def _warstwa_bledow(self, wydz, bledy):
        """bledy: [(feat_wydz, opis, grupy_ls)] -> warstwa BŁĘDY_GRUP."""
        lyr = QgsVectorLayer(
            f'MultiPolygon?crs={wydz.crs().authid()}', 'BŁĘDY_GRUP', 'memory')
        dp = lyr.dataProvider()
        dp.addAttributes([QgsField('ADR_LES', QVariant.String, len=30),
                          QgsField('BLAD', QVariant.String, len=60),
                          QgsField('GRP_LS', QVariant.String, len=30)])
        lyr.updateFields()
        nowe = []
        for fw, opis, grupy in bledy:
            nf = QgsFeature(lyr.fields())
            nf.setGeometry(fw.geometry())
            nf.setAttributes([str(fw['ADR_LES']), opis, ', '.join(sorted(grupy))])
            nowe.append(nf)
        dp.addFeatures(nowe)
        dodana = QgsProject.instance().addMapLayer(lyr)
        dodana.loadNamedStyle(os.path.join(
            os.path.dirname(__file__), '..', 'qml', 'poly_red_outline.qml'))

    # ------------------------------------------------------ przebieg

    def uruchom(self):
        dlg = _WyborDialog(self.iface)
        if dlg.exec_() != QDialog.Accepted:
            return None
        wydz, ls, baza_sc = dlg.wydz(), dlg.ls(), dlg.baza_sc()
        if wydz is None or ls is None or not baza_sc:
            self.iface.messageBar().pushMessage(
                TYTUL, 'Wskaż warstwy WYDZ i LS oraz bazę', Qgis.Critical, 10)
            return None
        if 'ADR_LES' not in wydz.fields().names() or \
                'GRP' not in ls.fields().names():
            self.iface.messageBar().pushMessage(
                TYTUL, 'WYDZ musi mieć pole ADR_LES, a LS pole GRP',
                Qgis.Critical, 10)
            return None

        self.raport += [f'--- {TYTUL.upper()} ---', '',
                        f'WYDZ: {wydz.dataProvider().dataSourceUri()}',
                        f'LS:   {ls.dataProvider().dataSourceUri()}',
                        f'Baza: {baza_sc}', '']

        if not self._kontrola_grafiki(wydz, ls):
            self._zapisz_wyniki(wydz)
            return self.waypointy_sc
        wynik = self._porownaj_z_baza(wydz, baza_sc)
        self._zapisz_wyniki(wydz)
        return self.waypointy_sc if wynik is not None else None

    def _kontrola_grafiki(self, wydz, ls):
        """True - grafika spójna z LS; False - błędy (warstwa, Nawigator,
        przerwanie)."""
        sl_wydz = {}
        przypisania = []
        bez_adresu = 0
        for fw, fls, _inter in przeciecia_wydz_ls(wydz, ls, 1.0):
            adr = fw['ADR_LES']
            if _puste(adr) or len(str(adr)) < 13:
                continue
            sl_wydz[fw.id()] = fw
            przypisania.append((fw.id(), grupa(adr), fls['GRP']))
        for fw in wydz.getFeatures():
            if _puste(fw['ADR_LES']):
                bez_adresu += 1
        na_kilku, rozne = bledy_grup(przypisania)

        if bez_adresu:
            self.raport.append(f'Wydzielenia bez ADR_LES (pominięte): '
                               f'{bez_adresu}')
        if not na_kilku and not rozne:
            self.raport.append('Grafika: każde wydzielenie leży na jednej '
                               'grupie LS zgodnej z jego adresem - OK')
            self.raport.append('')
            return True

        bledy = []
        self.raport.append('BŁĘDY GRAFIKI - przerwano, popraw i uruchom '
                           'ponownie:')
        for fid, grupy in na_kilku.items():
            fw = sl_wydz[fid]
            opis = 'na kilku grupach LS: ' + ', '.join(sorted(grupy))
            bledy.append((fw, 'wydzielenie na kilku grupach LS', grupy))
            self._wp_xy('WYDZ na kilku grupach LS',
                        fw.geometry().boundingBox(), wydz.crs(), '',
                        str(fw['ADR_LES']),
                        obiekt=''.join(str(fw['ADR_LES']).split()),
                        blad='Wydzielenie na kilku grupach LS: ' +
                        ', '.join(sorted(grupy)))
            self.raport.append(f'  {fw["ADR_LES"]}: {opis}')
        for fid, (gw, grupy) in rozne.items():
            fw = sl_wydz[fid]
            opis = f'grupa w adresie {gw}, w LS {", ".join(sorted(grupy))}'
            bledy.append((fw, 'grupa WYDZ inna niż LS', grupy))
            self._wp_xy('Grupa WYDZ inna niż LS',
                        fw.geometry().boundingBox(), wydz.crs(), '',
                        str(fw['ADR_LES']),
                        obiekt=''.join(str(fw['ADR_LES']).split()),
                        blad=f'Grupa w adresie {gw}, w LS '
                        f'{", ".join(sorted(grupy))}')
            self.raport.append(f'  {fw["ADR_LES"]}: {opis}')
        self._warstwa_bledow(wydz, bledy)
        self.iface.messageBar().pushMessage(
            TYTUL,
            f'Przerwano: wydzielenia na kilku grupach LS: {len(na_kilku)}, '
            f'z grupą inną niż LS: {len(rozne)} - popraw grafikę (warstwa '
            'BŁĘDY_GRUP, Nawigator) i uruchom ponownie. Bazy nie zmieniono.',
            Qgis.Critical, 0)
        return False

    def _porownaj_z_baza(self, wydz, baza_sc):
        baza = Baza(baza_sc)
        if not baza.polacz():
            self.iface.messageBar().pushMessage(
                TYTUL, 'Nie mogłem połączyć się z bazą', Qgis.Critical, 10)
            return None
        rek = baza.pobierz(
            'select ARODES_INT_NUM, ARODES_TYP_CD, ADRESS_FOREST '
            'from F_ARODES')
        if rek is False:
            baza.zamknij()
            self.iface.messageBar().pushMessage(
                TYTUL, 'Nie udało się odczytać F_ARODES', Qgis.Critical, 10)
            return None
        adresy_bazy = {a: t for _i, t, a in rek}
        id_adresu = {a: i for i, _t, a in rek}

        graf = {}  # adres -> [geometrie] (do pokazania w Nawigatorze)
        for fw in wydz.getFeatures():
            if not _puste(fw['ADR_LES']):
                graf.setdefault(str(fw['ADR_LES']), []).append(fw.geometry())
        plan = plan_przemianowania(adresy_bazy, list(graf))

        def prostokat(adres_graf):
            """bbox wydzieleń grafiki o adresie albo (dla ODDZ) prefiksie."""
            r = None
            for a, geomy in graf.items():
                if a == adres_graf or (adres_graf.endswith('-    -  ') and
                                       a[:18] == adres_graf[:18]):
                    for g in geomy:
                        if r is None:
                            r = QgsRectangle(g.boundingBox())
                        else:
                            r.combineExtentWith(g.boundingBox())
            return r

        self.raport += [
            f'Rekordy WYDZIEL/ODDZ zgodne z grafiką: {plan["zgodne"]}',
            f'Do przemianowania (różnią się tylko grupą): '
            f'{len(plan["zmiany"])}']
        self.raport += [f'  {s}  ->  {n}' for s, n in plan['zmiany']]
        self.raport.append(f'Kolizje (nowy adres już jest w bazie - bez '
                           f'zmian, do wyjaśnienia): {len(plan["kolizje"])}')
        for s, n in plan['kolizje']:
            self.raport.append(f'  {s}  ->  {n}')
            r = prostokat(n)
            if r is not None:
                self._wp_xy('Kolizje adresów', r, wydz.crs(),
                            f'{s} -> {n}', n,
                            obiekt=''.join(s.split()) + ' -> ' +
                            ''.join(n.split()),
                            blad='Adres z grupą z grafiki już jest w bazie')
        self.raport.append(f'Niejednoznaczne: {len(plan["niejednoznaczne"])}')
        for s, kand in plan['niejednoznaczne']:
            self.raport.append(f'  {s}  ->  {", ".join(kand)}')
            r = prostokat(kand[0])
            if r is not None:
                self._wp_xy('Niejednoznaczne', r, wydz.crs(),
                            'kandydaci: ' + ', '.join(kand), s,
                            obiekt=''.join(s.split()),
                            blad='Kilka adresów w grafice pasuje bez grupy')
        self.raport.append(f'W bazie bez pary w grafice: '
                           f'{len(plan["bez_pary"])}')
        for s in plan['bez_pary']:
            self.raport.append(f'  {s}')
            self._wp_adres('W bazie bez pary w grafice', s,
                           'pokaż na warstwie starych wydzieleń '
                           '(WYDZ_POL_stare)',
                           blad='Jest w bazie, brak w grafice')

        podsumowanie = (
            f'do przemianowania: {len(plan["zmiany"])}, kolizje: '
            f'{len(plan["kolizje"])}, niejednoznaczne: '
            f'{len(plan["niejednoznaczne"])}, bez pary w grafice: '
            f'{len(plan["bez_pary"])}, zgodne: {plan["zgodne"]}')
        if not plan['zmiany']:
            baza.zamknij()
            self.raport.append('\nNic do przemianowania.')
            self.iface.messageBar().pushMessage(
                TYTUL, 'Nic do przemianowania (' + podsumowanie + ')',
                Qgis.Info if not (plan['kolizje'] or plan['bez_pary'] or
                                  plan['niejednoznaczne'])
                else Qgis.Warning, 15)
            return plan

        przyklad = '\n'.join(f'{s}  ->  {n}' for s, n in plan['zmiany'][:5])
        odp = QMessageBox.question(
            self.iface.mainWindow(), TYTUL,
            f'Grafika jest spójna z LS. Wynik porównania z bazą:\n'
            f'{podsumowanie}.\n\nPrzemianować {len(plan["zmiany"])} adresów '
            f'leśnych w bazie na grupę z grafiki? Np.:\n{przyklad}\n\n'
            'Kolizje, niejednoznaczne i adresy bez pary zostaną bez zmian. '
            'Przed zmianą zostanie zrobiona kopia bazy.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if odp != QMessageBox.Yes:
            baza.zamknij()
            self.raport.append('\nPrzemianowanie anulowane przez '
                               'użytkownika - bazy nie zmieniono.')
            return plan

        if kopie_manipulacyjne.zrob_kopie_manipulacyjna(
                baza_sc, [], 'sprawdz_grupe') is None:
            baza.zamknij()
            self.iface.messageBar().pushMessage(
                TYTUL, 'Nie udało się zrobić kopii bazy - przerwano, nic '
                'nie zmieniono', Qgis.Critical, 10)
            return plan
        ok = baza.zmien_adresy({id_adresu[s]: n for s, n in plan['zmiany']})
        baza.zamknij()
        if not ok:
            self.raport.append('\nBŁĄD przemianowania - zmiany wycofane.')
            self.iface.messageBar().pushMessage(
                TYTUL, 'Błąd przy przemianowaniu - zmiany wycofane (log '
                'Las-R)', Qgis.Critical, 10)
            return plan
        self.raport.append(f'\nPrzemianowano: {len(plan["zmiany"])}')
        QgsMessageLog.logMessage(
            f'{TYTUL}: przemianowano {len(plan["zmiany"])} adresów w '
            f'{baza_sc}', 'Las-R', Qgis.Info)
        self.iface.messageBar().pushMessage(
            TYTUL, f'Przemianowano {len(plan["zmiany"])} adresów leśnych '
            '(kopia bazy w Kopie_manipulacyjne)' +
            ('; kolizje/bez pary - w Nawigatorze' if self.wiersze_wp else ''),
            Qgis.Success, 15)
        return plan


def sprawdz_grupe(iface):
    """Wywołanie z menu - zwraca ścieżkę pliku dla Nawigatora albo None."""
    return SprawdzGrupe(iface).uruchom()
