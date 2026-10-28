import re
from operator import itemgetter

from qgis.core import Qgis, QgsMessageLog

from . import kopie_manipulacyjne
from .przyciski import QMessageBox

TYTUL = 'Zanumeruj oddziały'


def _pusty(v):
    return v is None or str(v).strip() in ('', 'NULL')


def _numer(v):
    """Liczba z początku numeru oddziału ('12', '12a' -> 12) albo None."""
    m = re.match(r'\s*(\d+)', str(v)) if not _pusty(v) else None
    return int(m.group(1)) if m else None


def _koniec():
    QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)


def _zapytaj(iface, lyr, znumerowane, wszystkie):
    """'calosc' / 'dodaj' albo None (Anuluj)."""
    monit = QMessageBox(iface.mainWindow())
    monit.setIcon(QMessageBox.Question)
    monit.setWindowTitle(TYTUL)
    monit.setText(
        'W warstwie {} są już zanumerowane oddziały: {} z {}.\n\n'
        'Przenumeruj całość - nowe numery dla wszystkich oddziałów '
        '(kopia warstwy przed zmianą).\n'
        'Dodaj numerację - numery tylko dla oddziałów bez numeru, kolejne '
        'po najwyższym numerze w obrębie.'.format(
            lyr.name(), znumerowane, wszystkie))
    anuluj = monit.addButton('Anuluj', QMessageBox.RejectRole)
    calosc = monit.addButton('Przenumeruj całość',
                             QMessageBox.DestructiveRole)
    dodaj = monit.addButton('Dodaj numerację', QMessageBox.AcceptRole)
    monit.setDefaultButton(anuluj)
    monit.setEscapeButton(anuluj)
    monit.exec_()
    return {calosc: 'calosc', dodaj: 'dodaj'}.get(monit.clickedButton())


def Numeruj(iface):  # noqa
    lyr = iface.activeLayer()

    QgsMessageLog.logMessage(
        '------ NUMERUJ ODDZIAŁY --------- ',
        'Las-R',
        Qgis.Info
    )

    if lyr is None or not lyr.isValid() or not hasattr(lyr, 'fields'):
        iface.messageBar().pushMessage(
            'BŁĄD', 'Zaznacz w TOC poprawną warstwę oddziałów',
            Qgis.Critical, 10)
        _koniec()
        return False

    # zdefiniuj nizbedne pola w warstwie
    pola = [
        'COMMUNITY',
        'MUNICIP',
        'ODDZ',
    ]
    sl = {}  # slownik z zanumerowanymi oddz {feat.id: 'nr', ...}
    tab = []  # tabela z danymi do sortowania kolejnosci wydz

    # sprawdz czy mamy wszystkie pola w bazie
    braki = [x for x in pola if x not in [y.name() for y in lyr.fields()]]
    if len(braki) > 0:
        iface.messageBar().pushMessage(
            'BRAK KOLUMN',
            'Brakuje kolumn w zaznaczonej warstwie: '+', '.join(braki),
            Qgis.Critical,
            10)
        _koniec()
        return False

    fnm = lyr.dataProvider().fieldNameMap()  # slownik kolejnosci nazw w shp
    for f in lyr.getFeatures():
        tab.append([
            f.id(),
            f.geometry().boundingBox().yMaximum(),
            f.geometry().boundingBox().xMaximum(),
            f['MUNICIP'],
            f['COMMUNITY'],
            f['ODDZ'],
        ])

    # kolejnosc: gmina, obreb, w obrebie od polnocy
    tab = sorted(tab, key=itemgetter(1), reverse=True)
    tab = sorted(tab, key=itemgetter(4))
    tab = sorted(tab, key=itemgetter(3))

    znumerowane = sum(1 for t in tab if not _pusty(t[5]))
    tryb = 'dodaj'
    if znumerowane > 0:
        tryb = _zapytaj(iface, lyr, znumerowane, len(tab))
        if tryb is None:
            QgsMessageLog.logMessage('Anulowano', 'Las-R', Qgis.Info)
            _koniec()
            return False
        if tryb == 'calosc' and kopie_manipulacyjne.zrob_kopie_manipulacyjna(
                None, [lyr], 'przenumeruj_oddzialy') is None:
            iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało się zrobić kopii warstwy - przerwano, '
                'numery bez zmian', Qgis.Critical, 10)
            _koniec()
            return False

    # najwyzszy istniejacy numer w obrebie - "Dodaj numerację" zaczyna od
    # kolejnego (wczesniej numeracja zaczynala sie od 1 i dublowala numery)
    najwyzszy = {}
    if tryb == 'dodaj':
        for t in tab:
            nr = _numer(t[5])
            klucz = (str(t[3]), str(t[4]))
            if nr is not None and nr > najwyzszy.get(klucz, 0):
                najwyzszy[klucz] = nr

    # ponumeruj oddz
    gmi = None
    obr = None
    oddz = 1
    puste = 0
    for t in tab:
        if 'NULL' in [str(t[3]), str(t[4])]:
            puste += 1

        if str(t[3]) != gmi or str(t[4]) != obr:
            gmi = str(t[3])
            obr = str(t[4])
            oddz = najwyzszy.get((gmi, obr), 0) + 1

        if tryb == 'calosc' or _pusty(t[5]):
            sl[t[0]] = {fnm['ODDZ']: str(oddz)}
            oddz += 1

    lyr.startEditing()
    for key, val in sl.items():
        lyr.dataProvider().changeAttributeValues({key: val})
    lyr.commitChanges()

    opis = ('przenumerowano: ' if tryb == 'calosc' else 'zanumerowano: ') + \
        str(len(sl)) + ' oddziałów'
    if puste == 0:
        iface.messageBar().pushMessage(
            'OK',
            'Warstwa zanumerowana bez problemów, ' + opis,
            Qgis.Success,
            10)
    else:
        iface.messageBar().pushMessage(
            'PUSTE WIERSZE',
            'Zidentyfikowano puste wiersze, proszę sprawdzić poprawność '
            'warstwy! ' + opis[0].upper() + opis[1:],
            Qgis.Warning,
            10)

    if tryb == 'dodaj' and znumerowane > 0:
        QgsMessageLog.logMessage(
            'Pominięto zanumerowanych oddziałów: ' + str(znumerowane),
            'Las-R',
            Qgis.Info
        )

    _koniec()
