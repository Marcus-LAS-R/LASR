from qgis.core import Qgis, QgsMessageLog, QgsFeatureRequest
from .baza_wrapper import znajdz_baze_do_wydz, Baza


class DopiszWydzielenia():
    def __init__(self, iface):
        self.iface = iface

        self.sl_wydz_shp = {}  # {adr_les: arodes_int_num} wydz z shp
        self.sl_wydz_baza = {}  # {adr_les: arodes_int_num} wydz z bazy
        self.arodes = []  # wszystkie rekordy z bazy z kolumny F_arodes

        self.dodano = 0  # liczba wpisanych wydzieleń
        self.bledy = 0  # liczba błędów podczas wpisywania
        self.obecne = 0  # liczba obecnych wydzieleń w bazie

        # arodes_int_num z ktorym wpisany zostanie do bazy aktualny wpis
        self.current_arod = 0

        self.sl_woj = {
                "D": "02",
                "C": "04",
                "L": "06",
                "F": "08",
                "E": "10",
                "K": "12",
                "W": "14",
                "O": "16",
                "R": "18",
                "B": "20",
                "G": "22",
                "S": "24",
                "T": "26",
                "N": "28",
                "P": "30",
                "Z": "32",
                }

    def sprawdz_dane(self):
        try:
            self.wydz = self.iface.activeLayer()
        except:  # nopep8
            return False

        if 'ADR_LES' not in [x.name() for x in
                             self.wydz.dataProvider().fields().toList()]:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak kolumny ADR_LES w warstwie WYDZ!',
                Qgis.Critical,
                0
            )
            return False

        baza_sc = znajdz_baze_do_wydz(self.iface, self.wydz)
        if baza_sc is not False:
            self.iface.messageBar().pushMessage(
                'Przetwarzam',
                'Dodaje dane do bazy, proszę czekać...',
                Qgis.Info,
                5
            )
            self.baza = Baza(baza_sc)
            self.baza.polacz()
            return True

        return False

    def wczytaj_wydz_shp(self):
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['ADR_LES'],
                                                   self.wydz.fields()
                                               )

        for feat in self.wydz.getFeatures(request):
            self.sl_wydz_shp[feat['ADR_LES']] = 1

    def wczytaj_wydz_baza(self):
        self.sl_wydz_baza = self.baza.pobierz_wydzielenia()

        arod = self.baza.pobierz(
            'select ADRESS_FOREST, ARODES_INT_NUM from F_ARODES;'
        )
        if arod is not False:
            if len(arod) > 0:
                self.arodes = [x[0] for x in arod]
                self.current_arod = max([x[1] for x in arod]) + 1
            return True
        return False

    def dopisz_wydz(self):
        """ Metoda dopisuje do bazy taksatora wydzielenia z shp o ile ich juz,
        tam nie ma, wtedy są pomijane.
        """
        for it in self.sl_wydz_shp.keys():
            dodaj = []  # tablica, ktora trzyma rzeczy do dopisania do bazy
            if it not in self.arodes:
                funk = [
                    self.stworz_ops_oddz,
                    self.stworz_ops_obrebu,
                    self.stworz_ops_lctwa,
                    self.stworz_ops_wydz,
                ]

                # wygeneruj tylko te zestawy, których jescze nie ma w bazie
                for f in funk:
                    d = f(it)
                    if d[0] not in self.arodes:
                        dodaj.append(d)

            else:
                self.obecne += 1

            if len(dodaj) > 0:
                for d in dodaj:
                    sql =  \
                        "INSERT INTO F_ARODES (" + \
                        "ARODES_INT_NUM, " + \
                        "ADRESS_FOREST, " + \
                        "ARODES_TYP_CD, " + \
                        "ORDER_KEY, " + \
                        "ADRESS_VALID" + \
                        " ) VALUES ( " + \
                        str(self.current_arod) + ", '" + \
                        '\', \''.join(d) + '\' );'
                    wpisanie = self.baza.wpisz(sql)

                    if not wpisanie:
                        QgsMessageLog.logMessage(
                            d[0]+' - nie udało się wpisać do F_ARODES',
                            'Las-R'
                        )
                        self.bledy += 1

                    else:
                        if 'WYDZIEL' == d[1]:
                            sql = "INSERT INTO F_SUBAREA " + \
                                "(ARODES_INT_NUM, SUB_AREA) VALUES (" + \
                                str(self.current_arod) + ", 0 )"

                            if not self.baza.wpisz(sql):
                                QgsMessageLog.logMessage(
                                    d[0]+' - nie udało się wpisać do '
                                    'F_SUBAREA',
                                    'Las-R'
                                )
                                self.bledy += 1
                            else:
                                self.dodano += 1

                        self.arodes.append(d[0])
                        self.current_arod += 1

    def wyswietl_info(self):
        self.iface.messageBar().clearWidgets()
        if self.bledy > 0:
            self.iface.messageBar().pushMessage(
                "BŁĘDY",
                'Podczas wpisywania stwierdzono błędów: ' + str(self.bledy) +
                ', Wpisano poprawnie: ' + str(self.dodano),
                Qgis.Warning,
                0
            )
            return

        if self.dodano > 0:
            wpis = 'Wpisano poprawnie: ' + str(self.dodano) + ' wydzieleń'
        else:
            wpis = 'Wpisano poprawnie: 0 wydzieleń, tak powinno być??'

        if self.obecne > 0:
            wpis += ', w bazie wpisane było: ' + str(self.obecne) + \
                ' wydzieleń'

        self.iface.messageBar().pushMessage(
            "OK",
            wpis,
            Qgis.Success,
            10
        )
        self.baza.zamknij()
        del self.baza

    def stworz_ops_obrebu(self, wiersz):
        k1 = wiersz[:6] + '    -      -    -  '
        k2 = self.sl_woj[wiersz[0]] + wiersz[1:6] + '00000000 000'
        return [k1, u'OBRĘB', k2, 'T']

    def stworz_ops_lctwa(self, wiersz):
        k1 = wiersz[:10] + "-      -    -  "
        k2 = self.sl_woj[wiersz[0]] + wiersz[1:10] + '0000 000'
        return [k1, 'L-CTWO', k2, 'T']

    def stworz_ops_oddz(self, wiersz):
        k1 = wiersz[:17] + '-    -  '
        k2 = str(
            self.sl_woj[wiersz[0]] +
            wiersz[1:10]+(4-len(str(int(wiersz[13:17])))) * '0' +
            str(int(wiersz[13:17])) +
            ' 000'
        )
        return [k1, 'ODDZ', k2, 'T']

    def stworz_ops_wydz(self, wiersz):
        if 'LZ' in wiersz.upper():
            k2 = str(
                self.sl_woj[wiersz[0]] +
                wiersz[1:10] +
                (4-len(str(int(wiersz[13:17]))))*'0' +
                str(int(wiersz[13:17])) + 'zL00')

        else:
            if wiersz[19] == " ":
                w = " " + wiersz[18]
            else:
                w = wiersz[18:20][::-1]
            k2 = str(
                self.sl_woj[wiersz[0]] + wiersz[1:10] +
                (4-len(str(int(wiersz[13:17])))) * '0' +
                str(int(wiersz[13:17])) + w + '00'
            )

        return [wiersz, 'WYDZIEL', k2, 'T']
