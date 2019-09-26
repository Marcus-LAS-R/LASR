import os
from collections import defaultdict
from qgis.core import QgsVectorLayer, Qgis, QgsProject, \
    QgsField, QgsMessageLog
from PyQt5.QtCore import QVariant
from shutil import copyfile

from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .sprawdzenia_warstw import SprawdzWydzielenia


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class DopiszKody(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface

        QgsMessageLog.logMessage(
            '--- DOPISZ METADANE DO WYDZIELEŃ ---',
            'Las-R',
            Qgis.Info
        )

    def pobierz_dane(self):
        """Metoda pobiera i sprwdza poprawność wskazanej warstwy oraz
        komplementarnej bazy"""

        self.wydz = self.iface.activeLayer()
        self.wydz_path = \
            self.wydz.dataProvider().dataSourceUri().split("|")[0]
        self.kat = os.path.dirname(self.wydz_path)

        baza_sc = znajdz_baze_do_wydz(self.iface)

        if baza_sc:
            self.baza = Baza(baza_sc)
        else:
            self.iface.messageBar().pushMessage(
                "Błąd",
                'Nie udało się połączyć z bazą danych',
                Qgis.Critical)
            self.koniec()
            return False
        return True

    def koniec(self):
        QgsMessageLog.logMessage(
            '\n\n--- KONIEC ---',
            'Las-R',
            Qgis.Info
        )

    def isNone(self, x, typ='s'):
        if x is None:
            if typ == "s":
                return " "
            if typ == "i":
                return 0
        else:
            return x

    def kody(self, gat, wiek, struk, typ):  # noqa
        a = 0
        wynik = 580
        if typ not in [u'D-STAN', u'PŁAZ', u'HAL', u'ZRĄB', u'LZ-Ł']:
            return 580

        if typ == "LZ-Ł":
            return 590

        if typ == 'ZRĄB':
            return 579

        # Przepisanie dziwnych gatunkow
        if gat[:2] == "SO":
            gat = "SO"
        if gat[:2] == "DB":
            gat = "DB"
        if gat[:2] == "OL":
            gat = "OL"
        if gat[:2] == "KL":
            gat = "KL"
        if gat[:2] == "JS":
            gat = "JS"
        if gat[:2] == "TP":
            gat = "TP"

        if typ == "PŁAZ":
            if gat[:2] in ['SO', 'LB', 'ŚW', 'JD', 'DG', 'MD', ]:
                return 571
            else:
                return 572

        if gat[:2] not in ['SO', 'LB', 'ŚW', 'JD', 'DG', 'MD', 'DB', 'KL',
                           'GB', 'BK', 'JS', 'WZ', 'OL', 'BR', 'AK', 'TP',
                           'WB', 'OS', 'JW', 'LP']:
            QgsMessageLog.logMessage(
                'Nierozpoznany gatunek, traktuję jako Klon: '+gat,
                'Las-R',
                Qgis.Warning
            )
            gat = 'KL'

        if gat == "MD" or gat == "LB":
            gat = "SO"
        if gat == "SO" and wiek < 21 and struk != "KO":
            wynik = 1
        if gat == "SO" and wiek > 20 and struk != "KO":
            wynik = 2
        if gat == "SO" and wiek > 79 and struk != "KO":
            wynik = 3
        if gat == "SO" and struk == "KO":
            wynik = 500
        if gat == "SO" and typ == "HAL":
            wynik = 550

        # SW
        if gat == u'ŚW' and wiek < 21 and struk != "KO":
            wynik = 4
        if gat == u'ŚW' and wiek > 20 and struk != "KO":
            wynik = 5
        if gat == u'ŚW' and wiek > 79 and struk != "KO":
            wynik = 6
        if gat == u'ŚW' and struk == "KO":
            wynik = 501
        if gat == u'ŚW' and typ == "HAL":
            wynik = 551

        # JD, DG
        if gat == "DG":
            if gat == "DG" and wiek > 79 and struk != "KO":
                wynik = 9
                a = 1
            gat = "JD"
        if gat == "JD" and wiek < 21 and struk != "KO":
            wynik = 7
        if gat == "JD" and wiek > 20 and struk != "KO":
            wynik = 8
        if gat == "JD" and wiek > 99 and struk != "KO" and a == 0:
            wynik = 9
        if gat == "JD" and struk == "KO":
            wynik = 502
        if gat == "JD" and typ == "HAL":
            wynik = 552
        a = 0

        # DB
        if gat == "DB" and wiek < 21 and struk != "KO":
            wynik = 10
        if gat == "DB" and wiek > 20 and struk != "KO":
            wynik = 11
        if gat == "DB" and wiek > 119 and struk != "KO":
            wynik = 12
        if gat == "DB" and struk == "KO":
            wynik = 503
        if gat == "DB" and typ == "HAL":
            wynik = 553

        # BK i GB
        if gat == "GB":
            if gat == "GB" and wiek > 59 and struk != "KO":
                wynik = 15
                a = 1
            gat = "BK"
        if gat == "BK" and wiek < 21 and struk != "KO":
            wynik = 13
        if gat == "BK" and wiek > 20 and struk != "KO":
            wynik = 14
        if gat == "BK" and wiek > 99 and struk != "KO" and a == 0:
            wynik = 15
        if gat == "BK" and struk == "KO":
            wynik = 504
        if gat == "BK" and typ == "HAL":
            wynik = 554
        a = 0

        # JS, KL WZ JW
        if gat == "KL" or gat == "JW":
            gat = "JS"
            if gat == "JS" and wiek > 79 and struk != "KO":
                wynik = 18
                a = 1
        if gat == "WZ":
            gat = "JS"

        if gat == "JS" and wiek < 21 and struk != "KO":
            wynik = 16
        if gat == "JS" and wiek > 20 and struk != "KO":
            wynik = 17
        if gat == "JS" and wiek > 119 and struk != "KO" and a == 0:
            wynik = 18
        if gat == "JS" and struk == "KO":
            wynik = 505
        if gat == "JS" and typ == "HAL":
            wynik = 555
        if gat == "JS" and typ[0] == "P" and typ[2:] == "AZ":
            wynik = 572
        a = 0

        # OL
        if gat == "OL" and wiek < 21 and struk != "KO":
            wynik = 19
        if gat == "OL" and wiek > 20 and struk != "KO":
            wynik = 20
        if gat == "OL" and wiek > 59 and struk != "KO":
            wynik = 21
        if gat == "OL" and struk == "KO":
            wynik = 506
        if gat == "OL" and typ == "HAL":
            wynik = 556

        # BRZ i AK
        if gat == "AK":
            gat = "BRZ"
        if gat == "BRZ" and wiek < 21 and struk != "KO":
            wynik = 22
        if gat == "BRZ" and wiek > 20 and struk != "KO":
            wynik = 23
        if gat == "BRZ" and wiek > 59 and struk != "KO":
            wynik = 24
        if gat == "BRZ" and struk == "KO":
            wynik = 507
        if gat == "BRZ" and typ == "HAL":
            wynik = 557

        # TP, OS, WB, LP
        if gat in ["WB", "OS"]:
            gat = "TP"
            if gat == "TP" and wiek > 39 and struk != "KO":
                wynik = 27
                a = 1

        if gat == "LP":
            if gat == "LP" and wiek > 59 and struk != "KO":
                wynik = 27
                a = 1
            gat = "TP"

        if gat == "TP" and wiek < 21 and struk != "KO":
            wynik = 25
        if gat == "TP" and wiek > 20 and struk != "KO":
            wynik = 26
        if gat == "TP" and wiek > 119 and struk != "KO" and a == 0:
            wynik = 27
        if gat == "TP" and struk == "KO":
            wynik = 508
        if gat == "TP" and typ == "HAL":
            wynik = 558
        a = 0

        return wynik

    def pobierzBaze(self):
        # wybierz zaznaczona werstwe WYDZ o odpowiedniej strukturze
        # opis gdzie sie laczymy

        if self.baza.polacz():
            self.dane = self.baza.pobierz_do_mapy()
            self.sl = {x[0]: x[1:] for x in self.dane}
            self.ciecia_raw = self.baza.pobierz_zab_do_mapy()
            self.przetworz_zab()
            self.baza.zamknij()

            QgsMessageLog.logMessage(
                'Przetworzyłem dane z bazy!',
                'Las-R',
                Qgis.Info
            )

            return True

        QgsMessageLog.logMessage(
            'Nie udało się przetworzyć bazy i przygotować danych do dopisania',
            'Las-R',
            Qgis.Critical
        )

        self.koniec()
        return False

    def przetworz_zab(self):
        """Metoda przetwarza pobrane zabiegi, przygotowuj slownik do dopisania
        oraz ustawia odpowiednie flagi do dodania potrzebnych pol"""

        self.przestoje_flag = False
        self.dopis = recursivedefaultdict()

        self.zabiegi = [
            u'IB',
            u'IC',
            u'IA',
            u'IID',
            u'IIDU',
            u'IIB',
            u'IIBU',
            u'IIC',
            u'IICU',
            u'IIA',
            u'IIAU',
            u'IIIB',
            u'IIIBU',
            u'IIIA',
            u'IIIAU',
            u'V',
            u'IVB',
            u'IVC',
            u'IVBU',
            u'IVCU',
            u'IVA',
            u'IVD',
            u'IVDU',
            u'IVAU',
            u'PŁAZ',
            u'CP',
            u'CW',
            u'CS',
            u'CP-P',
            u'TP',
            u'TW',
            u'TPP',
            u'TWP',
            u'DRZEW',
        ]

        for x in self.ciecia_raw:
            if x[0] not in self.dopis:
                self.dopis[x[0]] = recursivedefaultdict()

            if x[1] in self.zabiegi:
                if 'ZABIEG' not in self.dopis[x[0]].keys():
                    self.dopis[x[0]]['ZABIEG'] = []
                self.dopis[x[0]]['ZABIEG'].append([x[1], x[2]])

            elif x[1][:3].upper() == 'ODN':
                if 'ODNOW' not in self.dopis[x[0]].keys():
                    self.dopis[x[0]]['ODNOW'] = []
                self.dopis[x[0]]['ODNOW'].append([x[1], x[2]])

            elif x[1] == 'AGROT':
                self.dopis[x[0]]['AGROT'] = x[2]

            elif x[1] == 'PIEL':
                self.dopis[x[0]]['PIEL'] = x[2]

            elif x[1] == 'PRZEST':
                self.dopis[x[0]]['PRZEST'] = x[2]
                self.przestoje_flag = True
            else:
                if 'INNE' not in self.dopis[x[0]].keys():
                    self.dopis[x[0]]['INNE'] = []
                self.dopis[x[0]]['INNE'].append(x[1])

    def dopisz_kody(self):  # noqa
        # kopiujemy shp
        for roz in ['shp', 'shx', 'prj', 'dbf', 'cpg']:
            try:
                copyfile(self.wydz_path[:-3]+roz,
                         os.path.join(self.kat, 'WYDZ_DOPISANE.' + roz))
            except:  # noqa
                pass

        self.wpol = QgsVectorLayer(os.path.join(self.kat, "WYDZ_DOPISANE.shp"),
                                   "WYDZ_DOPISANE", "ogr")
        self.wpol_data = self.wpol.dataProvider()
        self.wpol_data.setEncoding('UTF-8')

        # Dodajemy odpowiednie kolumny:
        attr_nazwy = [x.name() for x in self.wydz.fields()]
        attr = self.wydz.fields()

        pola = [
            QgsField("COUNTY_L", QVariant.String, len=1),
            QgsField("COUNTY", QVariant.String, len=2),
            QgsField("DISTRICT", QVariant.String, len=2),
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("GRP", QVariant.String, len=2),
            # QgsField("ODDZ", QVariant.String, len=4),
            # QgsField("WYDZ", QVariant.String, len=4),
            # QgsField("ADR_LES", QVariant.String, len=35),
            QgsField("L_EWID", QVariant.String, len=1),
            QgsField("UDZIAL", QVariant.String, len=5),
            QgsField("GAT", QVariant.String, len=10),
            QgsField("WIEK", QVariant.Int),
            QgsField("ZADRZEW", QVariant.Double, 'double', 10, 1),
            QgsField("POW_WYDZ", QVariant.String, 'double', 10, 2),
            QgsField("TYP_POW", QVariant.String, len=20),
            QgsField("STRUKTUR", QVariant.String, len=20),
            QgsField("SLMN_KOL", QVariant.Int),
            QgsField("STL", QVariant.String, len=20),
            QgsField("ZABIEG", QVariant.String, len=20),
            QgsField("POW_ZAB", QVariant.Double, 'double', 10, 4),
            QgsField("ODNOW", QVariant.String, len=20),
            QgsField("POW_ODN", QVariant.Double, 'double', 10, 4),
            QgsField("AGROT", QVariant.Double, 'double', 10, 4),
            QgsField("PIEL", QVariant.Double, 'double', 10, 4),
            ]

        if self.przestoje_flag:
            pola.append(QgsField("PRZEST", QVariant.Double, 'double', 10, 4))

        pola += [
            QgsField("INNE", QVariant.String, len=70),
        ]

        dodaj = [y for y in pola if y.name() not in attr_nazwy]
        for d in dodaj:
            attr.append(d)

        self.wpol_data.addAttributes(attr)
        self.wpol.updateFields()
        self.wpol.commitChanges()

        fnm = self.wpol_data.fieldNameMap()

        brak_opisu = []
        sl_dop = {}
        for feat in self.wpol.getFeatures():
            dop = {}
            adr = feat['ADR_LES']
            print(adr)
            if adr in self.sl:
                # przygotuj kod gatunku z odpowiednia wielkoscia liter
                gat = self.isNone(self.sl[adr][4])
                if gat != ' ':
                    gat = gat[:1].upper() + gat[1:].lower()

                dop = {
                    fnm['TYP_POW']: self.isNone(self.sl[adr][0]),
                    fnm['STL']: self.isNone(self.sl[adr][1]),
                    fnm['POW_WYDZ']: self.isNone(self.sl[adr][2], typ='i'),
                    fnm['UDZIAL']: self.isNone(self.sl[adr][3]),
                    fnm['GAT']: self.isNone(gat),
                    fnm['WIEK']: self.isNone(self.sl[adr][5], typ='i'),
                    fnm['ZADRZEW']: round(
                        self.isNone(self.sl[adr][6], typ='i'), 1),
                    fnm['STRUKTUR']: self.isNone(self.sl[adr][8]),
                    fnm['L_EWID']: 'T',
                }

                if adr in self.dopis:
                    if 'AGROT' in self.dopis[adr]:
                        dop[fnm['AGROT']] = self.dopis[adr]['AGROT']
                    if 'PIEL' in self.dopis[adr]:
                        dop[fnm['PIEL']] = self.dopis[adr]['PIEL']

                    if self.przestoje_flag:
                        if 'PRZEST' in self.dopis[adr]:
                            prz = self.isNone(self.dopis[adr]['PRZEST'],
                                              typ='i')
                        else:
                            prz = 0
                        dop[fnm['PRZEST']] = prz
                    if 'INNE' in self.dopis[adr]:
                        dop[fnm['INNE']] = ','.join([self.isNone(x) for x in
                                                    self.dopis[adr]['INNE']]
                                                    )

                    for kk in ['ODNOW', 'ZABIEG']:
                        if kk in list(self.dopis[adr].keys()):
                            try:
                                dop[fnm[kk]] = ','.join([x[0] for x in
                                                         self.dopis[adr][kk]])
                                dop[fnm['POW_'+kk[:3]]] = \
                                    max([x[1] for x in self.dopis[adr][kk]])
                            except:  # nopep8
                                QgsMessageLog.logMessage(
                                    'Niedopisane zabiegi w wydz: '+adr,
                                    'Las-R',
                                    Qgis.Warning
                                )

                kod = self.kody(
                    self.isNone(self.sl[adr][4]),
                    self.isNone(self.sl[adr][5], typ='i'),
                    self.isNone(self.sl[adr][8]),
                    self.isNone(self.sl[adr][0]),
                    )
                dop[fnm['SLMN_KOL']] = kod

                if self.sl[adr][0] == "D-STAN" and kod > 560:
                    QgsMessageLog.logMessage(
                        adr + " - Blad generowania kodu - " +
                        self.sl[adr][4] + " - " + kod,
                        "LCH")
                    self.iface.messageBar().pushMessage(
                        'UWAGA',
                        'Probemy przy generowaniu kodów, zobacz log',
                        Qgis.Warning)

                sl_dop[feat.id()] = dop
            else:
                sl_dop[feat.id()] = {fnm['SLMN_KOL']: 0}
                brak_opisu.append(feat.id())

        for k, it in sl_dop.items():
            self.wpol_data.changeAttributeValues({k: it})
        if len(brak_opisu) > 0:
            self.iface.messageBar().pushMessage(
                'BŁĘDY', 'Nie dopisano wszystkich atrybutów', Qgis.Warning)

            QgsMessageLog.logMessage(
                '\n'.join([str(x) for x in brak_opisu]),
                'LAS-R'
            )

        else:
            self.iface.messageBar().pushMessage(
                'OK', 'Metadane dopisane do wydzieleń', Qgis.Success)
        QgsProject.instance().addMapLayer(self.wpol)
