from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout,
)
from qgis.core import (
    Qgis, QgsFeatureRequest, QgsMessageLog, QgsProject, QgsVectorLayer,
)


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


class _WyborWarstwyDialog(QDialog):
    """ Wybór warstwy (z TOC), domyślnie WYDZ jeśli jest w projekcie - do
    ZaadresujStareWydz. """

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle('Utwórz ADR_LES dla starych wydzieleń')
        self.setMinimumWidth(400)

        self._warstwy = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if isinstance(lyr, QgsVectorLayer)
        ]

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            'Adres leśny zostanie utworzony wyłącznie dla wydzieleń z '
            'uzupełnionym ODDZ i WYDZ - reszta zostanie pominięta bez '
            'zmian.'
        ))

        row = QHBoxLayout()
        row.addWidget(QLabel('Warstwa:'))
        self.combo = QComboBox()
        self.combo.addItems([lyr.name() for lyr in self._warstwy])
        row.addWidget(self.combo, 1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self._warstwy:
            indeks = next(
                (i for i, lyr in enumerate(self._warstwy)
                 if lyr.name().upper() == 'WYDZ'), 0)
            self.combo.setCurrentIndex(indeks)

    def warstwa(self):
        i = self.combo.currentIndex()
        return self._warstwy[i] if 0 <= i < len(self._warstwy) else None


def ZaadresujStareWydz(iface):
    """Jak Zaadresuj, ale: (1) pozwala wybrać warstwę (domyślnie WYDZ,
    jeśli jest w projekcie) zamiast zawsze brać aktywną, (2) buduje
    ADR_LES wyłącznie dla wydzieleń z uzupełnionym ODDZ i WYDZ - resztę
    zostawia bez zmian. Przydatne przy starych wydzieleniach, gdzie część
    rekordów może jeszcze nie mieć przypisanego oddziału/wydzielenia."""
    dlg = _WyborWarstwyDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    lyr = dlg.warstwa()
    if lyr is None or not lyr.isValid():
        iface.messageBar().pushMessage(
            'BŁĄD', 'Zaznacz poprawną warstwę', Qgis.Critical, 10)
        return False

    pola = ['ADR_LES', 'COMMUNITY', 'MUNICIP', 'COUNTY_L', 'WYDZ', 'ODDZ',
            'DISTRICT', 'GRP']
    braki = [x for x in pola if x not in [y.name() for y in lyr.fields()]]
    if len(braki) > 0:
        iface.messageBar().pushMessage(
            'BRAK KOLUMN',
            'Brakuje kolumn w zaznaczonej warstwie: ' + ', '.join(braki),
            Qgis.Critical,
            10)
        return False

    fnm = lyr.dataProvider().fieldNameMap()
    lyr.startEditing()
    request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                           ).setSubsetOfAttributes(
                                               pola, lyr.fields())

    sl = {}
    pominieto = 0
    for f in lyr.getFeatures(request):
        oddz = f['ODDZ']
        wydz = f['WYDZ']
        if (oddz is None or wydz is None
                or str(oddz).strip() == '' or str(wydz).strip() == ''):
            pominieto += 1
            continue
        adr = zbuduj_adres(
            f['COUNTY_L'], f['DISTRICT'], f['MUNICIP'], f['COMMUNITY'],
            f['GRP'], oddz, wydz)
        sl[f.id()] = {fnm['ADR_LES']: adr}

    if len(sl) == 0:
        lyr.rollBack()
        iface.messageBar().pushMessage(
            'BRAK', 'Nie ma wydzieleń z uzupełnionym ODDZ i WYDZ',
            Qgis.Warning, 10)
        return False

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
            f'Zaadresowano {len(sl)} wydzieleń, pominięto {pominieto} '
            '(brak ODDZ/WYDZ)',
            Qgis.Success,
            10)

    QgsMessageLog.logMessage(
        f'ZaadresujStareWydz: zaadresowano {len(sl)}, pominięto '
        f'{pominieto} (brak ODDZ/WYDZ)',
        'Las-R',
        Qgis.Info
    )
    return True
