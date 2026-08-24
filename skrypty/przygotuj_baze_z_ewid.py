import os
import re
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QTableWidgetItem,
)
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer

from .baza_wrapper import Baza
from .baza_korekta_gmin_dialog import KorektaGminDialog
from .ui.ui_przygotuj_baze_z_ewid import Ui_Dialog

_WYMAGANE_POLA_SHP = (
    'wojewodztw', 'powiat', 'gmina', 'obreb', 'arkusz', 'nr_dzialki', 'teryt')

# format identyfikatora dzialki z geoportalu: WOJ(2)POW(2)GMI(2)_RODZ(1).
# OBREB(4).<reszta>, np. "121201_1.0001.1/11" - <reszta> to zwykle sam numer
# dzialki, ale bywa tez "ARKUSZ.NR_DZIALKI" (numery dzialek w tym formacie
# nie zawieraja kropek, wiec pierwsza kropka w <reszta>, jesli jest, zawsze
# rozdziela arkusz od numeru dzialki) - stad nie anchorujemy wzorca do konca
# stringa, tylko dopasowujemy sam prefiks do obrebu
_WZORZEC_TERYT = re.compile(r'^(\d{2})(\d{2})(\d{2})_(\d)\.(\d{4})\.(.+)$')


# ---------------------------------------------------------------------
# rozbior TERYT / budowa wierszy z warstwy SHP
# ---------------------------------------------------------------------

def _rozbierz_teryt(teryt):
    """ Rozbija identyfikator dzialki z geoportalu na kody administracyjne,
    plus ewentualny numer arkusza wyciagniety z <reszta> (fallback, gdy
    kolumna 'arkusz' jest pusta). Zwraca None, jesli prefiks nie pasuje. """
    dopasowanie = _WZORZEC_TERYT.match(teryt)
    if not dopasowanie:
        return None
    woj, pow_, gmi, rodz, obreb, reszta = dopasowanie.groups()
    arkusz_z_terytu = None
    if '.' in reszta:
        arkusz_z_terytu = reszta.split('.', 1)[0].strip() or None
    return {
        'county': woj,
        'district': pow_,
        'municipality': gmi + rodz,
        'community': obreb,
        'arkusz_z_terytu': arkusz_z_terytu,
    }


def _pow_ha(feature):
    return round(feature.geometry().area() / 10000, 4)


def _nazwy_pol(warstwa):
    return {f.name().lower(): f.name() for f in warstwa.fields()}


def _tekst(f, nazwy_pol, klucz):
    if klucz not in nazwy_pol:
        return ''
    wartosc = f[nazwy_pol[klucz]]
    return '' if wartosc is None else str(wartosc).strip()


def _sprawdz_wymagane_pola(warstwa):
    nazwy = set(_nazwy_pol(warstwa))
    return [p for p in _WYMAGANE_POLA_SHP if p not in nazwy]


def _zbuduj_wiersze(cechy, nazwy_pol):
    """ Zwraca (dobre, bledy_formatu). 'dobre' to lista dictow (jeden na
    dzialke), 'bledy_formatu' to lista czytelnych komunikatow dla dzialek
    odrzuconych (teryt nie pasuje do wzorca albo brak nr_dzialki). """
    dobre = []
    bledy = []
    for f in cechy:
        teryt = _tekst(f, nazwy_pol, 'teryt')
        nr_dzialki = _tekst(f, nazwy_pol, 'nr_dzialki')
        rozbite = _rozbierz_teryt(teryt) if teryt else None
        if rozbite is None or not nr_dzialki:
            bledy.append(
                (nr_dzialki or '(brak nr)') + '  teryt="' + teryt + '"')
            continue
        dobre.append({
            'feature': f,
            'county': rozbite['county'],
            'district': rozbite['district'],
            'municipality': rozbite['municipality'],
            'community': rozbite['community'],
            'parcel_nr': nr_dzialki,
            'arkusz': _tekst(f, nazwy_pol, 'arkusz') or
            rozbite['arkusz_z_terytu'],
            'nazwa_obreb': _tekst(f, nazwy_pol, 'obreb'),
            'nazwa_gmina': _tekst(f, nazwy_pol, 'gmina'),
            'nazwa_powiat': _tekst(f, nazwy_pol, 'powiat'),
            'nazwa_woj': _tekst(f, nazwy_pol, 'wojewodztw'),
        })
    return dobre, bledy


def _zbuduj_liste_obrebow(dobre):
    """ Grupuje dzialki po (MUNICIPALITY_CD, COMMUNITY_CD), sortuje rosnaco
    po tym kluczu i przydziela kolejne numery grup G1, G2, ... - jeden numer
    na caly obreb, niezaleznie od liczby dzialek w nim. """
    grupy = {}
    for w in dobre:
        klucz = (w['municipality'], w['community'])
        if klucz not in grupy:
            grupy[klucz] = {
                'municipality_cd': w['municipality'],
                'community_cd': w['community'],
                'county_cd': w['county'],
                'district_cd': w['district'],
                'nazwa_obreb': w['nazwa_obreb'],
                'gmina': w['nazwa_gmina'],
                'powiat': w['nazwa_powiat'],
                'wojewodztwo': w['nazwa_woj'],
                'liczba_dzialek': 0,
            }
        grupy[klucz]['liczba_dzialek'] += 1
        if not grupy[klucz]['nazwa_obreb'] and w['nazwa_obreb']:
            grupy[klucz]['nazwa_obreb'] = w['nazwa_obreb']

    posortowane = sorted(
        grupy.values(), key=lambda o: (o['municipality_cd'], o['community_cd']))
    for i, obr in enumerate(posortowane):
        obr['land_register_nr'] = 'G' + str(i + 1)
    return posortowane


def _oznacz_duplikaty(dobre, klucze_w_bazie):
    """ Zwraca (unikalne, duplikaty). Klucz biznesowy dzialki to
    (MUNICIPALITY_CD, COMMUNITY_CD, PARCEL_NR) - identyfikuje ja jednoznacznie
    w ramach obrebu. 'klucze_w_bazie' to zbior takich samych kluczy juz
    obecnych w F_PARCEL (z Baza.pobierz_klucze_dzialek()) - dzieki temu
    ponowne uruchomienie skryptu na czesciowo wypelnionej bazie nie tworzy
    duplikatow. """
    widziane = set(klucze_w_bazie)
    unikalne = []
    duplikaty = []
    for w in dobre:
        klucz = (w['municipality'], w['community'], w['parcel_nr'])
        if klucz in widziane:
            duplikaty.append(w)
            continue
        widziane.add(klucz)
        unikalne.append(w)
    return unikalne, duplikaty


def _znajdz_niepasujace_gminy(dobre, gminy_valid):
    """ {(county, district, municipality): {nazwa_gminy, ...}} dla trojek
    spoza gminy_valid - format oczekiwany przez KorektaGminDialog. """
    niepasujace = {}
    for w in dobre:
        klucz = (w['county'], w['district'], w['municipality'])
        if klucz not in gminy_valid:
            niepasujace.setdefault(klucz, set()).add(
                w['nazwa_gmina'] or '(brak nazwy)')
    return niepasujace


# ---------------------------------------------------------------------
# dialog
# ---------------------------------------------------------------------

def _znajdz_shp_w_toc(iface):
    """ Jesli aktywna warstwa w QGIS to plikowy SHP z wszystkimi wymaganymi
    polami, zwraca jej sciezke zrodlowa - do auto-uzupelnienia dialogu. """
    warstwa = iface.activeLayer()
    if warstwa is None:
        return ''
    try:
        sc = warstwa.dataProvider().dataSourceUri().split('|')[0]
    except Exception:
        return ''
    if not sc or not sc.lower().endswith('.shp') or not os.path.isfile(sc):
        return ''
    sprawdzana = QgsVectorLayer(sc, 'sprawdzana', 'ogr')
    if not sprawdzana.isValid() or _sprawdz_wymagane_pola(sprawdzana):
        return ''
    return sc


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._dobre = []
        self._bledy_formatu = []
        self._obreby = []

        shp_toc = _znajdz_shp_w_toc(iface)
        if shp_toc:
            self.ui.lineEdit_shp.setText(shp_toc)

        self.ui.pushButton_shp.clicked.connect(self._wybierz_shp)
        self.ui.pushButton_baza.clicked.connect(self._wybierz_baze)
        self.ui.lineEdit_shp.textChanged.connect(self._na_zmiane_shp)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj)
        self.ui.lineEdit_name1.textChanged.connect(self._aktualizuj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        if shp_toc:
            self._na_zmiane_shp()
        self._aktualizuj()

    def _wybierz_shp(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę SHP działek ewidencyjnych',
            os.path.dirname(self.ui.lineEdit_shp.text().strip()),
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_shp.setText(sc)

    def _wybierz_baze(self):
        startowy = os.path.dirname(self.ui.lineEdit_baza.text().strip()) or \
            os.path.dirname(self.ui.lineEdit_shp.text().strip())
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż pustą bazę docelową', startowy,
            'Access MDB (*.mdb)',
        )[0]
        if sc:
            self.ui.lineEdit_baza.setText(sc)

    def _na_zmiane_shp(self):
        self._dobre = []
        self._bledy_formatu = []
        self._obreby = []

        sc = self.ui.lineEdit_shp.text().strip()
        self.ui.tableWidget_obreby.blockSignals(True)
        self.ui.tableWidget_obreby.setRowCount(0)

        if sc and os.path.isfile(sc):
            warstwa = QgsVectorLayer(sc, 'ewid', 'ogr')
            if not warstwa.isValid():
                self.ui.label_status.setText(
                    'Nie można wczytać wskazanej warstwy SHP.')
            else:
                brakujace = _sprawdz_wymagane_pola(warstwa)
                if brakujace:
                    self.ui.label_status.setText(
                        'Brak wymaganych pól w warstwie: ' +
                        ', '.join(brakujace))
                else:
                    nazwy_pol = _nazwy_pol(warstwa)
                    cechy = list(warstwa.getFeatures())
                    self._dobre, self._bledy_formatu = _zbuduj_wiersze(
                        cechy, nazwy_pol)
                    self._obreby = _zbuduj_liste_obrebow(self._dobre)
                    self._wypelnij_tabele()

                    tekst = (
                        'Wczytano ' + str(len(self._dobre)) + ' działek, ' +
                        str(len(self._obreby)) + ' obrębów.')
                    if self._bledy_formatu:
                        tekst += (
                            ' Błędy formatu terytu (pominięte): ' +
                            str(len(self._bledy_formatu)) + '.')
                    self.ui.label_status.setText(tekst)
        else:
            self.ui.label_status.setText('')

        self.ui.tableWidget_obreby.blockSignals(False)
        self._aktualizuj()

    def _wypelnij_tabele(self):
        tabela = self.ui.tableWidget_obreby
        tabela.setRowCount(len(self._obreby))
        for wiersz, obr in enumerate(self._obreby):
            wartosci = [
                obr['land_register_nr'],
                (obr['nazwa_obreb'] or '(brak nazwy)') + '  [' +
                obr['municipality_cd'] + '/' + obr['community_cd'] + ']',
                obr['gmina'], obr['powiat'], obr['wojewodztwo'],
                str(obr['liczba_dzialek']),
            ]
            for kolumna, wartosc in enumerate(wartosci):
                item = QTableWidgetItem(wartosc)
                item.setFlags(Qt.ItemIsEnabled)
                tabela.setItem(wiersz, kolumna, item)

    def _aktualizuj(self, *_):
        ok = (
            bool(self._dobre) and
            bool(self.ui.lineEdit_baza.text().strip()) and
            bool(self.ui.lineEdit_name1.text().strip())
        )
        self.ui.pushButton_ok.setEnabled(ok)

    def shp_sc(self):
        return self.ui.lineEdit_shp.text().strip()

    def baza_sc(self):
        return self.ui.lineEdit_baza.text().strip()

    def dobre(self):
        return self._dobre

    def bledy_formatu(self):
        return self._bledy_formatu

    def obreby(self):
        return self._obreby

    def dane_wlasciciela(self):
        """ {'NAME_1': ...} - jeden wlasciciel dla calej bazy, wpisany
        recznie w oknie "Wlasciciel". Jedyne wymagane pole (walidowane w
        _aktualizuj/pushButton_ok). """
        return {'NAME_1': self.ui.lineEdit_name1.text().strip() or None}


# ---------------------------------------------------------------------
# uruchomienie: dialog glowny + (jesli trzeba) korekta gmin
# ---------------------------------------------------------------------

def uruchom(iface):
    """ Pokazuje dialog wyboru warstwy SHP, bazy docelowej i danych
    wlasciciela (jeden na cala baze), nastepnie - jesli w warstwie sa gminy
    spoza F_MUNICIPALITY bazy docelowej - monituje o reczna korekte
    (KorektaGminDialog, ten sam mechanizm co w "Aktualizuj strukture bazy")
    zanim cokolwiek zostanie zapisane. Anulowanie korekty przerywa caly
    import. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    shp_sc = dlg.shp_sc()
    baza_sc = dlg.baza_sc()
    dobre = dlg.dobre()
    obreby = dlg.obreby()
    wlasciciel = dlg.dane_wlasciciela()
    bledy_formatu = dlg.bledy_formatu()

    slownik = Baza(baza_sc)
    if not slownik.polacz():
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie udało się połączyć ze wskazaną bazą',
            Qgis.Critical, 10)
        return False
    gminy_sql = slownik.pobierz(
        'SELECT COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD FROM F_MUNICIPALITY;')
    slownik.zamknij()
    if gminy_sql is False:
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie udało się odczytać słownika F_MUNICIPALITY.',
            Qgis.Critical, 10)
        return False
    gminy_valid = {tuple(w) for w in gminy_sql}

    niepasujace = _znajdz_niepasujace_gminy(dobre, gminy_valid)
    if niepasujace:
        dlg_korekta = KorektaGminDialog(iface, niepasujace, gminy_valid)
        if dlg_korekta.exec_() != QDialog.Accepted:
            iface.messageBar().pushMessage(
                'Przygotuj bazę z EWID',
                'Anulowano - brak korekty gmin, baza nie została zmieniona.',
                Qgis.Warning, 10)
            return False
        korekty = dlg_korekta.wybor()

        for w in dobre:
            klucz = (w['county'], w['district'], w['municipality'])
            if klucz in korekty:
                w['municipality'] = korekty[klucz]

        # wlasciciel jest jeden dla calej bazy (niezalezny od obrebu), wiec
        # korekta gmin wymaga tylko przeliczenia obrebow/numeracji G z juz
        # skorygowanych dzialek - bez zadnego przemapowania
        obreby = _zbuduj_liste_obrebow(dobre)

    return PrzygotujBazeZEWID(
        iface, shp_sc, baza_sc, dobre, obreby, wlasciciel, bledy_formatu)


# ---------------------------------------------------------------------
# funkcja robocza - zapis do bazy w jednej transakcji
# ---------------------------------------------------------------------

def PrzygotujBazeZEWID(iface, shp_sc, baza_sc, dobre, obreby, wlasciciel,
                        bledy_formatu):  # noqa
    """ Zapisuje do wskazanej, pustej bazy Access szkielet ewidencyjny na
    podstawie warstwy SHP dzialek z geoportalu: brakujace obreby do
    F_COMMUNITY, JEDEN wlasciciel dla calej bazy do V_ADDRESS (dane wpisane
    recznie w dialogu), po jednej dzialce do F_PARCEL/F_PARCEL_LAND_USE
    (uzytek 'Ls') oraz powiazanie kazdej dzialki z tym jednym wlascicielem w
    V_PARCEL_PARTICIPATION. Cala operacja to JEDNA transakcja - blad w
    jakiejkolwiek fazie wycofuje wszystkie zmiany. """
    QgsMessageLog.logMessage(
        '------ PRZYGOTUJ BAZĘ Z EWID --------- ', 'Las-R', Qgis.Info)

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie udało się połączyć ze wskazaną bazą',
            Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    baza.utworz_kopie('przygotuj_baze_z_ewid')

    ls_ok = baza.pobierz(
        "SELECT COUNT(*) FROM F_AREA_USE_DIC WHERE AREA_USE_CD='Ls';")
    if not ls_ok or not ls_ok[0][0]:
        baza.zamknij()
        iface.messageBar().pushMessage(
            'BŁĄD',
            "Brak kodu użytku 'Ls' w słowniku F_AREA_USE_DIC - przerwano.",
            Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    klucze_w_bazie = baza.pobierz_klucze_dzialek() or []
    klucze_w_bazie = {
        (k[2], k[3], k[4]) for k in klucze_w_bazie
    }  # (MUNICIPALITY_CD, COMMUNITY_CD, PARCEL_NR)
    unikalne, duplikaty = _oznacz_duplikaty(dobre, klucze_w_bazie)

    if not unikalne:
        baza.zamknij()
        iface.messageBar().pushMessage(
            'Przygotuj bazę z EWID',
            'Brak działek do zapisania (wszystkie odrzucone lub duplikaty).',
            Qgis.Warning, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    klucze_obecne = {(w['municipality'], w['community']) for w in unikalne}
    land_register_nr_po_obrebie = {
        (o['municipality_cd'], o['community_cd']): o['land_register_nr']
        for o in obreby
    }

    odp = QMessageBox.question(
        iface.mainWindow(),
        'Podsumowanie',
        'Działek do zapisania: ' + str(len(unikalne)) + '\n'
        'Obrębów: ' + str(len(klucze_obecne)) + '\n'
        'Błędy formatu terytu (pominięte): ' + str(len(bledy_formatu)) + '\n'
        'Duplikaty działek (pominięte): ' + str(len(duplikaty)) + '\n\n'
        'Kontynuować zapis do bazy?',
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if odp != QMessageBox.Yes:
        baza.zamknij()
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    community_dopisane = 0
    zapisano = 0
    try:
        istniejace_community = {
            tuple(r) for r in (baza.pobierz(
                'SELECT COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, '
                'COMMUNITY_CD FROM F_COMMUNITY') or [])
        }

        for obr in obreby:
            klucz_obr = (obr['municipality_cd'], obr['community_cd'])
            if klucz_obr not in klucze_obecne:
                continue

            klucz_com = (
                obr['county_cd'], obr['district_cd'], obr['municipality_cd'],
                obr['community_cd'])
            if klucz_com not in istniejace_community:
                baza.cur.execute(
                    'INSERT INTO F_COMMUNITY (COUNTY_CD, DISTRICT_CD, '
                    'MUNICIPALITY_CD, COMMUNITY_CD, COMMUNITY_NAME) '
                    'VALUES (?,?,?,?,?)',
                    (obr['county_cd'], obr['district_cd'],
                     obr['municipality_cd'], obr['community_cd'],
                     (obr['nazwa_obreb'] or '')[:30]))
                istniejace_community.add(klucz_com)
                community_dopisane += 1

        # jeden wlasciciel dla calej bazy - wspolny dla wszystkich dzialek
        baza.cur.execute(
            'INSERT INTO V_ADDRESS (NAME_1, VIEW_ADDRESS_FL, LP_PRICE) '
            'VALUES (?,?,?)',
            (wlasciciel['NAME_1'], False, False))
        addr_nr = int(baza.cur.execute('SELECT @@IDENTITY').fetchval())

        for w in unikalne:
            pow_ha = _pow_ha(w['feature'])
            klucz_obr = (w['municipality'], w['community'])
            grupa = land_register_nr_po_obrebie[klucz_obr]

            kolumny = [
                'PARCEL_NR', 'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD',
                'COMMUNITY_CD', 'PARCEL_AREA', 'LAND_REGISTER_NR']
            wartosci = [
                w['parcel_nr'], w['county'], w['district'], w['municipality'],
                w['community'], pow_ha, grupa]
            if w['arkusz']:
                # brak arkusza -> kolumny REG_SHEET_NR1/2 w ogole pomijane w
                # INSERT (nie wpisujemy tam jawnego NULL), zamiast tego
                # zostaja domyslna wartoscia pola w bazie
                kolumny += ['REG_SHEET_NR1', 'REG_SHEET_NR2']
                wartosci += [w['arkusz'], w['arkusz']]

            baza.cur.execute(
                'INSERT INTO F_PARCEL (' + ', '.join(kolumny) + ') VALUES (' +
                ','.join('?' * len(kolumny)) + ')',
                tuple(wartosci))
            parcel_int_num = int(
                baza.cur.execute('SELECT @@IDENTITY').fetchval())

            baza.cur.execute(
                'INSERT INTO F_PARCEL_LAND_USE (PARCEL_INT_NUM, SHAPE_NR, '
                'AREA_USE_CD, LAND_USE_AREA, AFFORESTATION) '
                'VALUES (?,?,?,?,?)',
                (parcel_int_num, 1, 'Ls', pow_ha, False))

            baza.cur.execute(
                'INSERT INTO V_PARCEL_PARTICIPATION (addr_nr, '
                'parcel_int_num, part_numerator, part_denominator) '
                'VALUES (?,?,?,?)',
                (addr_nr, parcel_int_num, 1, 1))
            zapisano += 1

        baza.con.commit()
    except Exception as e:
        baza.con.rollback()
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Zapis nie powiódł się, wycofano wszystkie zmiany: ' + str(e),
            Qgis.Critical, 10)
        QgsMessageLog.logMessage(
            'Zapis nie powiódł się, rollback: ' + str(e), 'Las-R',
            Qgis.Critical)
        baza.zamknij()
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    czas = datetime.datetime.now().isoformat(
    ).replace(':', '')[:-7].replace('-', '')

    wypis = (
        '---- PRZYGOTUJ BAZĘ Z EWID ----\n\n'
        'Warstwa SHP: ' + shp_sc + '\n'
        'Baza: ' + baza_sc + '\n\n'
        'Obrębów: ' + str(len(klucze_obecne)) + '\n'
        'Działek w warstwie: ' + str(len(dobre) + len(bledy_formatu)) + '\n'
        'Zapisano do bazy: ' + str(zapisano) + '\n'
        'Dopisano brakujących obrębów do F_COMMUNITY: ' +
        str(community_dopisane) + '\n'
        'Właściciel (V_ADDRESS, wspólny dla całej bazy): ' +
        str(wlasciciel['NAME_1']) + '\n\n'
        'Numeracja grup (LAND_REGISTER_NR):\n'
    )
    for obr in obreby:
        klucz_obr = (obr['municipality_cd'], obr['community_cd'])
        if klucz_obr not in klucze_obecne:
            continue
        wypis += (
            '  ' + obr['land_register_nr'] + '  ' +
            (obr['nazwa_obreb'] or '') + ', ' + (obr['gmina'] or '') +
            '  (' + str(obr['liczba_dzialek']) + ' działek)\n')

    wypis += (
        '\nBłędy formatu TERYT (pominięte - ' + str(len(bledy_formatu)) +
        '):\n')
    for b in bledy_formatu:
        wypis += '  ' + b + '\n'

    wypis += (
        '\nDuplikaty działek (pominięte - ' + str(len(duplikaty)) + '):\n')
    for w in duplikaty:
        wypis += (
            '  ' + w['parcel_nr'] + '  ' + w['municipality'] + '/' +
            w['community'] + '\n')

    sciezka_raportu = os.path.join(
        os.path.dirname(shp_sc),
        'raport_przygotuj_baze_z_ewid_' + czas + '.txt')
    with open(sciezka_raportu, 'w', encoding='utf-8') as plik:
        plik.write(wypis)

    baza.zamknij()

    message = QMessageBox()
    message.setIcon(QMessageBox.Information)
    message.setWindowTitle('Raport')
    message.setText('Zakończono. Czy pokazać raport?')
    message.addButton("Zamknij", QMessageBox.ActionRole)
    message.addButton("Zamknij i pokaż raport", QMessageBox.ActionRole)
    if message.exec_() == 1:
        os.startfile(sciezka_raportu)

    QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
    return True
