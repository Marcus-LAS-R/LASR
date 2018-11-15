from qgis.core import Qgis, QgsMessageLog, QgsFeatureRequest
from collections import Counter


class SprawdzWydzielenia():
    """Klasa poboczna wymaga aby klasa dziedzicząca miałą już dodany wskaznik
    do wydz i bazy taksatora. Sprawdza poprawność pól w wydzieleniach, czy nie
    ma niepołączonych wydzieleń."""

    def __init__(self):
        pass

    def poprawne_wydz(self):
        """Metoda grupujaca wszystkie sprawdzenia danych i bazy"""
        spr = [
            self.spr_baza_polacz,
            self.spr_popr,
            self.spr_kolumn,
            self.spr_crs,
            self.spr_wydz_baza,
            self.spr_wydz_duble,
        ]

        komunikaty = [
            'Połączenie z bazą: OK',
            'Sprawdzenie poprawności warstwy wydz: OK',
            'Sprawdzenie obecności niezbędnych kolumn: OK',
            'Sprawdzenie układu wspł. (EPSG:2180) : OK',
            'Porównanie wydzieleń w warstwie z bazą: OK',
            'Sprawdzenie zdublowanych wydzieleń w warstwie: OK'
        ]

        for i, s in enumerate(spr):
            tt = s
            if not tt():
                if self.baza.con:
                    self.baza.zamknij()
                QgsMessageLog.logMessage(
                    'Warstwa wydzieleń niepoprawna!',
                    'LasR')
                return False
            else:
                QgsMessageLog.logMessage(
                    komunikaty[i],
                    'LasR',
                    Qgis.Info
                )

        return True

    def spr_baza_polacz(self):
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA',
                'Nie udało się połączyć ze wskazaną bazą!',
                Qgis.Critical,
                10)
            QgsMessageLog.logMessage(
                        'Brak dostepu do bazy',
                        'LasR')
            return False
        return True

    def spr_popr(self):
        if not self.wydz.isValid():
            if not self.wydz.isValid():
                self.iface.messageBar().pushMessage(
                    'Wydzielenia',
                    'Nie mogę otworzyć warstwy do odczytu',
                    Qgis.Critical,
                    10)
                return False
        return True

    def spr_crs(self):
        """Metoda sprwdza układ wspł. warstwy, jeżeli nie jest to EPSG:2180,
        zwraca False"""
        if self.wydz.crs().authid() != 'EPSG:2180':
            self.iface.messageBar().pushMessage(
                'Wydzielenia',
                'Warstwa ma inny układ współrzędnych niż PUWG92 (EPSG:2180)',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_kolumn(self):
        pola = [x for x in ['WYDZ', 'ODDZ', 'ADR_LES']
                if x not in self.wydz.dataProvider().fieldNameMap()]
        if len(pola) > 0:
            self.iface.messageBar().pushMessage(
                'Wydzielenia',
                'Brak kolumn '+', '.join(pola)+' w warstwie',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_wydz_baza(self):
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['ADR_LES'],
                                                   self.wydz.fields()
                                               )
        adr_w = [x['ADR_LES'] for x in self.wydz.getFeatures(request)]
        adr_b = self.baza.pobierz_wydzielenia()
        brakiw = [x for x in adr_w if x not in adr_b]
        brakib = [x for x in adr_b if x not in adr_w]

        QgsMessageLog.logMessage(
            '   Znaleziono poligonów w shp: ' + str(len(adr_w)),
            'LasR',
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            '   Znaleziono wydzieleń w shp: ' + str(len(set(adr_w))),
            'LasR',
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            '   Znaleziono wydzieleń w bazie: ' + str(len(adr_b)),
            'LasR',
            Qgis.Info
        )

        if len(brakiw) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W shp znajdują się wydzielenia, które nie są dopisane do ' +
                'Bazy! Patrz log LasR',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage('Brakujące wydzielenia w bazie:',
                                     'LasR',
                                     Qgis.Critical)
            for b in brakiw:
                QgsMessageLog.logMessage(b, 'LasR', Qgis.Critical)

        if len(brakib) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W bazie znajdują się wydzielenia, które nie są dopisane do ' +
                'warstwy! Patrz log LasR',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage('Brakujące wydzielenia w warstwie:',
                                     'LasR',
                                     Qgis.Critical)
            for b in brakib:
                QgsMessageLog.logMessage(b, 'LasR', Qgis.Critical)

        if len(brakib) > 0 or len(brakiw) > 0:
            return False

        return True

    def spr_wydz_duble(self):
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['ADR_LES'],
                                                   self.wydz.fields()
                                               )
        adr_w = [x['ADR_LES'] for x in self.wydz.getFeatures(request)]
        adr_b = self.baza.pobierz_wydzielenia()

        if len(adr_w) != len(set(adr_b)):
            self.iface.messageBar().pushMessage(
                'wydzielenia [shp]',
                'Połącz wydzielenia w multipoligony! (Spis w logu)',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage(
                '\nNiepołączone wydzielenia: \n' + '\n'.join(
                    [y[0] + '   (x' + str(y[1]) + ')'
                     for y in Counter(adr_w).most_common() if y[1] > 1]),
                'LasR'
            )
            return False
        return True
