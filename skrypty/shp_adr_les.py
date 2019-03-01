from qgis.core import Qgis, QgsFeatureRequest, QgsMessageLog


def Zaadresuj(iface, lyr=False):
    if lyr is False:
        lyr = iface.activeLayer()

    QgsMessageLog.logMessage(
        '------ DOPISANIE ARESU LEŚNEGO --------- ',
        'Las-R',
        Qgis.Info
    )

    if not lyr.isValid():
        QgsMessageLog.logMessage(
            'Brak zaznaczonej poprawnej warstwy',
            'Las-R',
            Qgis.Critical
        )
        QgsMessageLog.logMessage(
            '------ KONIEC -------- \n',
            'Las-R',
            Qgis.Info
        )

    # zdefiniuj nizbedne pola w warstwie
    pola = ['ADR_LES',
            'COMMUNITY',
            'MUNICIP',
            'COUNTY_L',
            'WYDZ',
            'ODDZ',
            'DISTRICT',
            'GRP',
            ]
    sl = {}  # slownik z adrles do dopisania w postaci {feat.id(): {i: adrles}}

    # sprawdz czy mamy wszystkie pola w bazie
    braki = [x for x in pola if x not in [y.name() for y in lyr.fields()]]
    if len(braki) > 0:
        iface.messageBar().pushMessage(
            'BRAK KOLUMN',
            'Brakuje kolumn w zaznaczonej warstwie: '+', '.join(braki),
            Qgis.Critical,
            10)
        return False

    fnm = lyr.dataProvider().fieldNameMap()  # slownik kolejnosci nazw w shp
    lyr.startEditing()
    request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                           ).setSubsetOfAttributes(
                                               pola, lyr.fields())
    for f in lyr.getFeatures(request):
        adr = ''.join(map(str, [f['COUNTY_L'],
                                f['DISTRICT'],
                                f['MUNICIP'],
                                f['COMMUNITY']]
                          )
                      )
        if len(str(f['GRP'])) == 2:
            adr += '-' + f['GRP']
        else:
            adr += '-  '
        adr += str(f['ODDZ']) + (4-len(str(f['ODDZ']))) * ' ' + '-'
        adr += str(f['WYDZ']) + (4-len(str(f['WYDZ']))) * ' ' + '-00'

        sl[f.id()] = {fnm['ADR_LES']: adr}

    message_trig = 0
    for key, adr in sl.items():
        if len(list(adr.values())[0]) != 25:
            if message_trig == 0:
                iface.messageBar().pushMessage(
                    'ADRES LEŚNY',
                    'Prawdopodobnie nie wszystkie kolumny składowe są '
                    'poprawnie uzupełnione, (Patrz log Las-R)',
                    Qgis.Warning,
                    10)
            message_trig += 1

            QgsMessageLog.logMessage(
                list(adr.values())[0],
                'Las-R',
                Qgis.Warning
            )

        lyr.dataProvider().changeAttributeValues({key: adr})

    lyr.commitChanges()
    if message_trig == 0:
        iface.messageBar().pushMessage(
            'OK',
            'Adres leśny uzupełniony bez problemów',
            Qgis.Success,
            10)

    QgsMessageLog.logMessage(
        '------ KONIEC -------- \n',
        'Las-R',
        Qgis.Info
    )
