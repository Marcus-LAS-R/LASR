from PyQt5.QtWidgets import QInputDialog
from qgis.utils import iface
from qgis.core import QgsFeatureRequest


def DopiszAdres():
    lyr = iface.activeLayer()
    try:
        if not lyr.isValid():
            iface.messageBar().pushWarning('BŁĄD', "Niepoprawna warstwa...")
            return
    except Exception:
        iface.messageBar().pushWarning('BŁĄD', "Niepoprawna warstwa...")
        return

    flds = [x.name().upper() for x in lyr.dataProvider().fields().toList()]
    pole = None
    if len([x for x in flds if x in ['MUNICIP', 'COMMUNITY']]) != 2:
        iface.messageBar().pushWarning(
            'BŁĄD', "Nie odnalezino kolumn MUNICIP i COMMUNITY"
        )
        return

    if 'G5IDD' in flds:
        pole = 'G5IDD'
    elif 'IDENTYFIKA' in flds:
        pole = 'IDENTYFIKA'
    else:
        kols = sorted([x for x in lyr.dataProvider().fieldNameMap().keys()])
        kol, ok = QInputDialog.getItem(
            None,
            'Wybierz kolumne z adresem administracyjnym',
            'Nazwa kloumny',
            kols, 0, False
        )
        if not ok:
            return
        pole = kol

    sl = {}
    req = QgsFeatureRequest().setFlags(
        QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            [pole, 'COMMUNITY', 'MUNICIP'], lyr.fields())

    fnm = lyr.dataProvider().fieldNameMap()
    for feat in lyr.getFeatures(req):
        adr = feat[pole]
        if adr:
            if len(adr) < 14:
                continue
            sl[feat.id()] = {
                fnm['COMMUNITY']: adr[9:13],
                fnm['MUNICIP']: adr[4:8].replace('_', '')
            }

    lyr.startEditing()
    lyr.dataProvider().changeAttributeValues(sl)
    lyr.commitChanges()

    iface.messageBar().pushSuccess(
        'Sukces', f'Uzupełniono {len(sl)} rekordów.'
    )
