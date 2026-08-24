from qgis.core import Qgis, QgsFeatureRequest, QgsMessageLog


def zbuduj_adres(county_l, district, municip, community, grp, oddz, wydz):
    """Buduje 25-znakowy adres leśny UPUL (TERYT-based) z jego składowych:
    COUNTY_L(1)+DISTRICT(2)+MUNICIP(3)+COMMUNITY(4)+'-'+GRP(2, wyrównane
    spacjami jeśli brak)+ODDZ(4, wyrównane spacjami)+'-'+WYDZ(4,
    wyrównane spacjami)+'-00'. Czysta funkcja (bez zależności od
    warstwy/iface) wydzielona z Zaadresuj() - żeby dało się jej użyć poza
    kontekstem edycji warstwy QGIS (patrz konwersja_pul_upul/core/adres.py)."""
    adr = str(county_l) + str(district) + str(municip) + str(community)
    if grp is not None and len(str(grp)) == 2:
        adr += '-' + str(grp)
    else:
        adr += '-  '
    adr += str(oddz).ljust(4) + '-'
    adr += str(wydz).ljust(4) + '-00'
    return adr


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
        adr = zbuduj_adres(
            f['COUNTY_L'], f['DISTRICT'], f['MUNICIP'], f['COMMUNITY'],
            f['GRP'], f['ODDZ'], f['WYDZ'])

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
