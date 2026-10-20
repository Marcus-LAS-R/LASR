import os
from collections import Counter

from qgis.core import Qgis, QgsField, QgsFeatureRequest, QgsMessageLog, \
    QgsProject, QgsSpatialIndex, QgsVectorLayer, QgsFeature
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox

from .sprawdzenia_warstw import SprawdzWydzielenia
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .shp_literkuj import Literkuj
from .shp_adr_les import Zaadresuj
from .baza_dopisz_wydz import DopiszWydzielenia
from .funkcje import wybierz_warstwe_z_kandydatow
from .waypointy import katalog_raportow
from . import kopie_manipulacyjne

# wydzielenie należy do oddziału, jeśli leży w nim w co najmniej 99% -
# drzazgi poniżej 1% (niedociągnięte granice) nie są traktowane jako
# przecięcie granicy oddziału (ten sam próg co w shp_dopOddzWydz)
PROG_W_ODDZ = 0.99
PROG_DRZAZGI = 0.01

# maksymalna liczba wydzieleń (bez Lz) w oddziale - powyżej literki się
# kończą (ten sam limit co w shp_dopOddzWydz)
MAX_WYDZ_W_ODDZ = 87


def _norm(wartosc):
    """ Porównywalna postać kodu (ODDZ/COMMUNITY/MUNICIP) - bez spacji
    i zer wiodących, żeby '01' i '1' nie dawały fałszywej zmiany """
    if wartosc is None:
        return ''
    t = str(wartosc).strip()
    if t.upper() == 'NULL':
        return ''
    return str(int(t)) if t.isdigit() else t


class Przeliterkuj(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface
        self.bledy = 0  # liczba błędów podczas wpisywania do bazy
        self.sl_wydz = {}
        self.dopisane_nadrz = []  # dopisane rekordy ODDZ/L-CTWO/OBRĘB
        self.osierocone = 0  # rekordy w bazie bez wydzieleń w warstwie
        self.raport = None

        self.pola = [
            QgsField("ST_ADR_LES", QVariant.String, len=25),
        ]

        self.request = QgsFeatureRequest().setFlags(
            QgsFeatureRequest.NoGeometry
        )

    def sprawdz_warstwe(self):
        """ Sprawdzenie czy wszystkie niezbędne pola znajdują się w warstwie,
        oraz czy nie ma nierozbitych wydzieleń.
        """
        try:
            self.wydz = self.iface.activeLayer()
        except:  # nopep8
            self.iface.messageBar().pushMessage(
                'BRAK WARSTWY', 'Zaznacz coś!', Qgis.Critical, 10)
            return False

        baza_sc = znajdz_baze_do_wydz(self.iface, self.wydz)
        if baza_sc is False:
            self.iface.messageBar().pushMessage(
                'BRAK BAZY', 'Bez bazy ani rusz!', Qgis.Critical, 10)
            return False

        self.baza = Baza(baza_sc)
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA', 'Nie mogłem podłączyć się do bazy', Qgis.Critical, 10)
            return False

        if not self.poprawne_wydz():
            return False

        return True

    def sprawdz_oddzialy(self):
        """ Ustala oddział każdego wydzielenia z położenia geometrycznego
        (warstwa ODDZ z TOC) i porównuje z ODDZ/COMMUNITY/MUNICIP w WYDZ.
        Wydzielenia przecinające granice oddziałów lub leżące poza nimi
        przerywają skrypt (warstwa błędów, bez cięcia). Gdy oddziały się
        zmieniły (nowy oddział, zmiana numeracji, puste ODDZ) - monit
        Kontynuuj/Porzuć; Kontynuuj nadpisuje atrybuty wg geometrii. """
        kandydaci = [x for x in QgsProject.instance().mapLayers().values()
                     if x.name()[:4] == 'ODDZ']
        oddz = wybierz_warstwe_z_kandydatow(self.iface, kandydaci, 'ODDZ')
        if not isinstance(oddz, QgsVectorLayer) or not oddz.isValid():
            self.iface.messageBar().pushMessage(
                'ODDZ',
                'W TOC musi być warstwa ODDZ (oddziały)',
                Qgis.Critical,
                10)
            return False

        pola = ['ODDZ', 'MUNICIP', 'COMMUNITY']
        for lyr in (self.wydz, oddz):
            brak = [x for x in pola if lyr.fields().indexOf(x) == -1]
            if brak:
                self.iface.messageBar().pushMessage(
                    'BRAK KOLUMN',
                    'W warstwie ' + lyr.name() + ' brakuje: ' +
                    ', '.join(brak),
                    Qgis.Critical,
                    10)
                return False

        # indeks przestrzenny oddziałów
        si = QgsSpatialIndex()
        sl_oddz = {}
        for f in oddz.getFeatures():
            si.addFeature(f)
            sl_oddz[f.id()] = f

        bledne = []  # [(feat, opis błędu)]
        zmiany = {}  # {fid wydz: (feat wydz, feat oddz)}
        w_oddz = Counter()  # liczba wydz. (bez Lz) w oddziale wg geometrii
        przed = set()  # oddziały obecne w atrybutach WYDZ przed zmianą

        for fw in self.wydz.getFeatures():
            klucz_w = tuple(_norm(fw[x]) for x in pola)
            przed.add(klucz_w)

            g = fw.geometry()
            pow_w = g.area() if g is not None else 0
            if pow_w <= 0:
                bledne.append((fw, 'pusta geometria'))
                continue

            glowny = None
            czesci = []
            for oid in si.intersects(g.boundingBox()):
                go = sl_oddz[oid].geometry()
                if not g.intersects(go):
                    continue
                frac = g.intersection(go).area() / pow_w
                if frac >= PROG_W_ODDZ:
                    glowny = sl_oddz[oid]
                    break
                if frac > PROG_DRZAZGI:
                    czesci.append((sl_oddz[oid], frac))

            if glowny is None:
                if czesci:
                    bledne.append((fw, 'przecina granicę oddziałów: ' + ', '.join(
                        '{}/{} {:.0%}'.format(
                            o['COMMUNITY'], o['ODDZ'], fr)
                        for o, fr in czesci)))
                else:
                    bledne.append((fw, 'poza oddziałami'))
                continue

            klucz_o = tuple(_norm(glowny[x]) for x in pola)
            if str(fw['WYDZ']).upper() != 'LZ':
                w_oddz[klucz_o] += 1
            if klucz_o != klucz_w:
                zmiany[fw.id()] = (fw, glowny)

        if bledne:
            self.pokaz_bledne(bledne)
            self.baza.zamknij()
            return False

        za_duzo = ['{}/{} ({})'.format(k[2], k[0], n)
                   for k, n in sorted(w_oddz.items()) if n > MAX_WYDZ_W_ODDZ]
        if za_duzo:
            QgsMessageLog.logMessage(
                'Oddziały z liczbą wydzieleń > ' + str(MAX_WYDZ_W_ODDZ) +
                ' (obręb/oddział): ' + ', '.join(za_duzo),
                'Las-R', Qgis.Warning)
            self.iface.messageBar().pushMessage(
                'ZA DUŻO WYDZIELEŃ',
                'Oddziały z liczbą wydzieleń > ' + str(MAX_WYDZ_W_ODDZ) +
                ': ' + ', '.join(za_duzo),
                Qgis.Warning,
                0)

        if not zmiany:
            QgsMessageLog.logMessage(
                'Przeliterkuj: oddziały w WYDZ zgodne z położeniem '
                'geometrycznym', 'Las-R', Qgis.Info)
            return True

        if not self.potwierdz_zmiany(zmiany, przed, oddz):
            self.iface.messageBar().pushMessage(
                'PORZUCONO',
                'Przeliterowanie przerwane - warstwa i baza bez zmian',
                Qgis.Info,
                10)
            self.baza.zamknij()
            return False

        # kopia warstwy i bazy przed nadpisaniem oddziałów
        if kopie_manipulacyjne.zrob_kopie_manipulacyjna(
                self.baza.baza, [self.wydz], 'przeliterkuj_oddzialy') is None:
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało się utworzyć kopii bezpieczeństwa - '
                'przerwano', Qgis.Critical, 10)
            self.baza.zamknij()
            return False

        fnm = self.wydz.dataProvider().fieldNameMap()
        nowe = {}
        for fid, (fw, fo) in zmiany.items():
            attr = {}
            for p in pola:
                if _norm(fw[p]) != _norm(fo[p]):
                    attr[fnm[p]] = str(fo[p]).strip()
            nowe[fid] = attr
        self.wydz.dataProvider().changeAttributeValues(nowe)
        self.wydz.reload()

        QgsMessageLog.logMessage(
            'Przeliterkuj: nadpisano oddział wg geometrii w ' +
            str(len(nowe)) + ' wydzieleniach', 'Las-R', Qgis.Info)
        return True

    def potwierdz_zmiany(self, zmiany, przed, oddz):
        """ Monit z podsumowaniem zmian oddziałów - zwraca True dla
        Kontynuuj """
        grupy = Counter()
        for fw, fo in zmiany.values():
            stary = '{}/{}'.format(_norm(fw['COMMUNITY']) or '?',
                                   _norm(fw['ODDZ']) or 'puste')
            nowy_klucz = (_norm(fo['ODDZ']), _norm(fo['MUNICIP']),
                          _norm(fo['COMMUNITY']))
            nowy = '{}/{}'.format(_norm(fo['COMMUNITY']), _norm(fo['ODDZ']))
            if nowy_klucz not in przed:
                nowy += ' [nowy oddział]'
            grupy[(stary, nowy)] += 1

        wiersze = ['  {} → {}  ({} wydz.)'.format(s, n, c)
                   for (s, n), c in sorted(grupy.items())]
        if len(wiersze) > 25:
            wiersze = wiersze[:25] + [
                '  ... i jeszcze {} pozycji'.format(len(wiersze) - 25)]

        message = QMessageBox()
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle('Zmieniły się oddziały')
        message.setText(
            'Położenie geometryczne {} wydzieleń nie zgadza się z ich '
            'oddziałem w warstwie {}.\n\n'
            'obręb/oddział w WYDZ → wg warstwy {}:\n{}\n\n'
            'Nadpisać oddziały wg położenia geometrycznego i przeliterować?'
            .format(len(zmiany), self.wydz.name(), oddz.name(),
                    '\n'.join(wiersze)))
        message.addButton('Porzuć', QMessageBox.RejectRole)
        kont = message.addButton('Kontynuuj', QMessageBox.AcceptRole)
        message.exec_()
        return message.clickedButton() == kont

    def pokaz_bledne(self, bledne):
        """ Warstwa z wydzieleniami przecinającymi granice oddziałów lub
        leżącymi poza nimi - do ręcznej poprawy """
        lyr = QgsVectorLayer(
            'MultiPolygon?crs=' + self.wydz.crs().authid(),
            'WYDZ_przecinające_ODDZ',
            'memory')
        dp = lyr.dataProvider()
        dp.addAttributes([
            QgsField('ADR_LES', QVariant.String, len=25),
            QgsField('BLAD', QVariant.String, len=254),
        ])
        lyr.updateFields()

        fs = []
        for fw, opis in bledne:
            f = QgsFeature(lyr.fields())
            f.setGeometry(fw.geometry())
            f['ADR_LES'] = fw['ADR_LES']
            f['BLAD'] = opis
            fs.append(f)
            QgsMessageLog.logMessage(
                'Przeliterkuj: ' + str(fw['ADR_LES']) + ' - ' + opis,
                'Las-R', Qgis.Critical)
        dp.addFeatures(fs)

        QgsProject.instance().addMapLayer(lyr)
        lyr.loadNamedStyle(os.path.join(
            os.path.dirname(__file__), '..', 'qml', 'poly_red_outline.qml'))
        lyr.triggerRepaint()

        self.iface.messageBar().pushMessage(
            'PRZERWANO',
            str(len(bledne)) + ' wydzieleń przecina granice oddziałów lub '
            'leży poza nimi - popraw je (warstwa WYDZ_przecinające_ODDZ, '
            'szczegóły w logu Las-R)',
            Qgis.Critical,
            0)

    def przygotuj_literkacje(self):
        """ Metoda kopiuje stary adres leśny do zapasowej kolumny i czyści
        wszystkie literki z kolumny WYDZ  pomijając Lz
        """
        # dodaj niezbedne pola o ile juz ich nie ma
        fnm = self.wydz.dataProvider().fieldNameMap()
        brak_pol = [x for x in self.pola if x.name() not in fnm]
        if len(brak_pol) > 0:
            self.wydz.startEditing()
            self.wydz.dataProvider().addAttributes(brak_pol)
            self.wydz.updateFields()
            self.wydz.commitChanges()

        # skopiuj wart do uprzednio dodanych kolumn i wyczyść kolumny WYDZ I
        # ADR_LES do literkacji, pomijając Lz
        fnm = self.wydz.dataProvider().fieldNameMap()
        self.wydz.startEditing()
        for feat in self.wydz.getFeatures(self.request):
            attr = {
                fnm['ST_ADR_LES']: feat['ADR_LES'],
            }

            # Jezeli wydzielenie nie jest Lz bedziemy przeliterkowywac
            if feat['WYDZ'].upper() != 'LZ':
                attr[fnm['WYDZ']] = ''
                attr[fnm['ADR_LES']] = ''

            self.wydz.dataProvider().changeAttributeValues(
                {feat.id(): attr}
            )

        self.wydz.commitChanges()

    def zaliterkuj(self):
        """ Literkuje na nowo uprzednio wyczyszczoną kolumnę WYDZ"""
        Literkuj(self.iface, self.wydz)

    def wygeneruj_adrles(self):
        """ Metoda generuj adres leśny na podstawie pól z shp """
        Zaadresuj(self.iface, self.wydz)

    def dopisz_do_bazy(self):
        """ Metoda dopisuje do bazy przeliterkowane wydzielenia """
        # klasa z której będziemy korzystać przy generowaniu poprawnych
        # indeksów do nowych wydzieleń
        dw = DopiszWydzielenia(self.iface)

        # slownik ze {stary adr: nowy adr} ale tylko dla tych które się różnią
        self.sl_wydz = {}
        for feat in self.wydz.getFeatures(self.request):
            if feat['ST_ADR_LES'] != feat['ADR_LES']:
                self.sl_wydz[feat['ST_ADR_LES']] = feat['ADR_LES']

        self.baza.utworz_kopie('kopia_przeliterowanie')
        f_arod = self.baza.pobierz_wydzielenia()

        for old, new in self.sl_wydz.items():
            if old in f_arod:
                ops = dw.stworz_ops_wydz(new)
                sql = 'UPDATE F_ARODES SET ADRESS_FOREST = \'' + \
                    new + \
                    '\' , ORDER_KEY = \'' + \
                    ops[2] + \
                    '\' WHERE ARODES_INT_NUM = ' + \
                    str(f_arod[old]) + \
                    ';'
                if not self.baza.wpisz(sql):
                    self.bledy += 1
                    QgsMessageLog.logMessage(
                        'Las-R',
                        'Błąd wpisania do bazy (nowy/stary adr): ' +
                        new + ' <---> ' + old
                    )

        self.dopisz_nadrzedne(dw)
        self.raport_osieroconych()
        self.baza.zamknij()

    def dopisz_nadrzedne(self, dw):
        """ Dopisuje brakujące rekordy ODDZ / L-CTWO / OBRĘB dla wydzieleń
        z warstwy - po przeniesieniu wydzieleń do nowego oddziału w bazie
        nie ma jeszcze jego rekordu """
        arod = self.baza.pobierz(
            'select ADRESS_FOREST, ARODES_INT_NUM from F_ARODES;')
        if not arod:
            return
        istniejace = {x[0] for x in arod}
        nastepny = max(x[1] for x in arod) + 1

        adresy = {f['ADR_LES'] for f in self.wydz.getFeatures(self.request)
                  if f['ADR_LES'] not in (None, '') and
                  str(f['ADR_LES']).upper() != 'NULL'}
        sql = 'INSERT INTO F_ARODES (ARODES_INT_NUM, ADRESS_FOREST, ' \
            'ARODES_TYP_CD, ORDER_KEY, ADRESS_VALID) VALUES (?, ?, ?, ?, ?)'
        for adr in sorted(adresy):
            for funk in (dw.stworz_ops_obrebu, dw.stworz_ops_lctwa,
                         dw.stworz_ops_oddz):
                try:
                    d = funk(adr)
                except Exception:
                    continue
                if d[0] in istniejace:
                    continue
                if self.baza.wpisz_tab((sql, [nastepny] + d)):
                    istniejace.add(d[0])
                    self.dopisane_nadrz.append((nastepny, d[0], d[1]))
                    nastepny += 1
                else:
                    self.bledy += 1
                    QgsMessageLog.logMessage(
                        'Przeliterkuj: nie udało się dopisać ' + d[1] +
                        ' ' + d[0], 'Las-R', Qgis.Critical)

    def raport_osieroconych(self):
        """ Raport (bez kasowania): wydzielenia z bazy bez poligonu
        w warstwie (np. Lz scalone przy literkowaniu) z ich działkami oraz
        oddziały bez wydzieleń (np. stara numeracja) """
        rek = self.baza.pobierz(
            'select ARODES_INT_NUM, ADRESS_FOREST, ARODES_TYP_CD '
            'from F_ARODES;')
        if not rek:
            return

        adr_shp = {f['ADR_LES'] for f in self.wydz.getFeatures(self.request)}
        wydz_baza = [x for x in rek if x[2] == 'WYDZIEL']
        bez_poligonu = sorted(
            [x for x in wydz_baza if x[1] not in adr_shp], key=lambda x: x[1])
        prefiksy = {x[1][:17] for x in wydz_baza if x[1]}
        puste_oddz = sorted(
            [x for x in rek if x[2] == 'ODDZ' and x[1][:17] not in prefiksy],
            key=lambda x: x[1])

        wiersze = []
        if self.dopisane_nadrz:
            wiersze.append('DOPISANE REKORDY NADRZĘDNE (nowe oddziały):')
            wiersze += ['  {} {} (ARODES_INT_NUM {})'.format(t, a, n)
                        for n, a, t in self.dopisane_nadrz]
            wiersze.append('')

        if bez_poligonu:
            numery = ', '.join(str(x[0]) for x in bez_poligonu)
            pow_sub = {x[0]: x[1] for x in self.baza.pobierz(
                'select ARODES_INT_NUM, SUB_AREA from F_SUBAREA '
                'where ARODES_INT_NUM in (' + numery + ');') or []}
            dzialki = self.baza.pobierz(
                'select u.ARODES_INT_NUM, p.PARCEL_NR, '
                'u.AROD_LAND_USE_AREA from F_AROD_LAND_USE u '
                'left join F_PARCEL p on u.PARCEL_INT_NUM = p.PARCEL_INT_NUM '
                'where u.ARODES_INT_NUM in (' + numery + ');')
            if dzialki is False:
                dzialki = self.baza.pobierz(
                    'select ARODES_INT_NUM, PARCEL_INT_NUM, '
                    'AROD_LAND_USE_AREA from F_AROD_LAND_USE '
                    'where ARODES_INT_NUM in (' + numery + ');') or []
            dz_wydz = {}
            for n, dz, p in dzialki:
                dz_wydz.setdefault(n, []).append('{} ({} ha)'.format(dz, p))

            wiersze.append(
                'WYDZIELENIA W BAZIE BEZ POLIGONU W WARSTWIE (np. Lz scalone '
                'przy literkowaniu) - do usunięcia/przepięcia działek:')
            for n, a, _ in bez_poligonu:
                wiersze.append('  {} (ARODES_INT_NUM {}), pow. {} ha, '
                               'działki: {}'.format(
                                   a, n, pow_sub.get(n, '?'),
                                   ', '.join(dz_wydz.get(n, [])) or 'brak'))
            wiersze.append('')

        if puste_oddz:
            wiersze.append('ODDZIAŁY W BAZIE BEZ WYDZIELEŃ (do usunięcia):')
            wiersze += ['  {} (ARODES_INT_NUM {})'.format(a, n)
                        for n, a, _ in puste_oddz]
            wiersze.append('')

        self.osierocone = len(bez_poligonu) + len(puste_oddz)
        if not wiersze:
            return

        for w in wiersze:
            if w:
                QgsMessageLog.logMessage(w, 'Las-R', Qgis.Info)

        kat = katalog_raportow(os.path.dirname(self.baza.baza))
        self.raport = os.path.join(
            kat, 'raport_przeliterkuj_' + self.baza.czas + '.txt')
        try:
            with open(self.raport, 'w', encoding='utf-8') as f:
                f.write('PRZELITERKUJ WYDZIELENIA - ' + self.baza.baza +
                        '\n\n' + '\n'.join(wiersze))
        except OSError:
            self.raport = None

    def wyswietl_info(self):
        if self.bledy > 0:
            self.iface.messageBar().pushMessage(
                'BŁĘDY PRZY WPISYWANIU',
                'Nie udało się wpisać do bazy ' + str(self.bledy) +
                ' wydzieleń - Patrz log Las-R',
                Qgis.Warning, 0)
            return

        if self.osierocone > 0:
            self.iface.messageBar().pushMessage(
                'UWAGA',
                'Przeliterkowano: ' + str(len(self.sl_wydz.keys())) +
                ' wydzieleń; w bazie zostało ' + str(self.osierocone) +
                ' rekordów bez wydzieleń w warstwie - patrz raport: ' +
                str(self.raport),
                Qgis.Warning, 0)
            return

        info = 'Przeliterkowano: ' + str(len(self.sl_wydz.keys())) + \
            ' wydzieleń'
        if self.dopisane_nadrz:
            info += ', dopisano oddziałów/obrębów: ' + \
                str(len(self.dopisane_nadrz))
        self.iface.messageBar().pushMessage('OK', info, Qgis.Success, 10)
