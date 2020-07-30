from qgis.core import Qgis, QgsField, QgsFeatureRequest, QgsMessageLog
from PyQt5.QtCore import QVariant

from .sprawdzenia_warstw import SprawdzWydzielenia
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .shp_literkuj import Literkuj
from .shp_adr_les import Zaadresuj
from .shp_sprWydzOddz import spr_wydz_oddz
from .baza_dopisz_wydz import DopiszWydzielenia


class Przeliterkuj(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface
        self.bledy = 0  # liczba błędów podczas wpisywania do bazy

        self.pola = [
            QgsField("ST_ADR_LES", QVariant.String, len=25),
            QgsField("ST_ODDZ", QVariant.String, len=6),
            QgsField("ST_WYDZ", QVariant.String, len=4),
        ]

        self.request = QgsFeatureRequest().setFlags(
            QgsFeatureRequest.NoGeometry
        )

    def sprawdz_warstwe(self):
        """ Sprawdzenie czy wszystkie niezbędne pola znajdują się w warstwie,
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

        # Sprawdz zawieranie sie przeliterkowywania w oddzialach
        spr = spr_wydz_oddz(self.iface, wydz=self.wydz)
        if spr[1] > 0:
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Wydzielenia nie zawierają sie w oddziałach',
                Qgis.Critical,
                10
            )
            return False

        return True

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
                fnm['ST_WYDZ']: feat['WYDZ'],
                fnm['ST_ODDZ']: feat['ODDZ'],
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

        self.baza.zamknij()

    def wyswietl_info(self):
        if self.bledy > 0:
            self.iface.messageBar().pushMessage(
                'BŁĘDY PRZY WPISYWANIU',
                'Nie udało się wpisać do bazy ' + str(self.bledy) +
                ' wydzieleń - Patrz log Las-R',
                Qgis.Warning, 0)
            return

        self.iface.messageBar().pushMessage(
            'OK',
            'Przeliterkowano: ' + str(len(self.sl_wydz.keys())) + ' wydzieleń',
            Qgis.Success,
            10)
