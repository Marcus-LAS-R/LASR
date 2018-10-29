from qgis.core import Qgis, QgsMessageLog, QgsFeatureRequest
from collections import Counter


class SprawdzWydzielenia():
    """Klasa poboczna wymaga aby klasa dziedzicząca miałą już dodany wskaxnik
    do wydz i bazy taksatora. Sprawdza poprawność pól w wydzieleniach, czy nie
    ma niepołączonych wydzieleń."""

    def __init__(self):
        pass

    def poprawne_wydz(self):
        """Metoda grupujaca wszystkie sprawdzenia danych i bazy"""
        spr = [
            self.spr_baza_polacz,
            self.spr_popr,
            self.spr_adrles,
            self.spr_wydz_baza,
            self.spr_wydz_duble,
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
        if not self.wydz.isValid() or not self.fo.isValid():
            if not self.wydz.isValid():
                self.iface.messageBar().pushMessage(
                    'Wydzielenia',
                    'Nie mogę otworzyć warstwy do odczytu',
                    Qgis.Critical,
                    10)
                return False
        return True

    def spr_adrles(self):
        if 'ADR_LES' not in self.wydz.dataProvider().fieldNameMap():
            self.iface.messageBar().pushMessage(
                'Wydzielenia',
                'Brak kolumny ADR_LES w warstwie',
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
        braki = [x for x in adr_w if x not in adr_b]

        QgsMessageLog.logMessage(
            'Znaleziono poligonów w shp: ' + str(len(adr_w)),
            'LasR',
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            'Znaleziono wydzieleń w shp: ' + str(len(set(adr_w))),
            'LasR',
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            'Znaleziono wydzieleń w bazie: ' + str(len(adr_b)),
            'LasR',
            Qgis.Info
        )

        if len(braki) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W shp znajdują się wydzielenia, które nie są dopisane do ' +
                'Bazy! Patrz log LasR',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage('Brakujące wydzielenia w bazie:',
                                     'LasR',
                                     Qgis.Critical)
            for b in braki:
                QgsMessageLog.logMessage(b, 'LasR', Qgis.Critical)
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
