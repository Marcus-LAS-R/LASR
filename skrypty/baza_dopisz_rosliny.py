import os
import platform
import glob
from qgis.core import Qgis, QgsMessageLog
from PyQt5.QtWidgets import QFileDialog
from .baza_wrapper import Baza


def dopisz_rosliny(iface):  # noqa: C901
    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow(),
        "Katalog z bazami danych",
        '')

    if platform.system()[:3] == 'Win':
        bazy_sc = glob.glob(os.path.join(bazy_kat, '*.mdb'))
    else:
        bazy_sc = glob.glob(os.path.join(bazy_kat, '*.sqlite'))

    ile_baz = len(bazy_sc)
    if ile_baz == 0:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie znalazłem żadnej bazy taksatora...',
            Qgis.Critical,
            10
        )
        return

    # wczytaj sl roslin
    try:
        rtab = [
            x.strip().split('\t') for x in
            open(os.path.join(os.path.dirname(__file__), 'sl_roslin.txt'), 'r'
                 ).readlines()]
        sl = {}
        for it in rtab:
            if len(it) != 4:
                continue
            if it[0] not in sl:
                sl[it[0]] = {}
            if it[1] not in sl[it[0]]:
                sl[it[0]][it[1]] = []
            sl[it[0]][it[1]] = it[2:]
    except Exception:
        iface.messageBar().pushMessage(
            "BŁĄD",
            'Skaszaniony słownik roślin, sprawdź plik!',
            Qgis.Warning,
            10
        )
        return

    bledy = 0
    ile_ok = 0
    dopisane = 0
    for sc in bazy_sc:
        baza = Baza(sc)
        # jezeli nie mozna polaczyc sie z bazą pomin ją
        if not baza.polacz():
            QgsMessageLog.logMessage(
                'Nie mogłem połączyć sięz bazą: ' + sc,
                'Las-R'
            )
            bledy += 1
            continue

        QgsMessageLog.logMessage(
            '\n'+20*'-'+'\nPrzetwarzam bazę: ' + sc,
            'Las-R', Qgis.Info
        )

        baza.utworz_kopie('dopisz_rosliny')

        wydz = baza.pobierz_wydzielenia()
        for adr, inum in wydz.items():
            res = baza.pobierz(
                'select site_type_cd, veg_cover_cd from f_subarea'
                f' where arodes_int_num={inum};'
            )
            if not res:
                continue
            site = res[0][0]
            cover = res[0][1]

            if site not in sl:
                continue
            if cover not in sl[site]:
                continue

            rosb = baza.pobierz(
                'select phen_rank_order, plant_cd from f_arod_phenomena '
                f'where arodes_int_num={inum} order by phen_rank_order asc;'
            )
            cur_phen = 1  # index phen_rank pod ktorym bedziemy dopisywac
            obecne = []  # tablica z obecnymi roslinami
            if not rosb:
                pass
            else:
                obecne = [x[1] for x in rosb]
                cur_phen = max([x[0] for x in rosb]) + 1

            if len(obecne) > 1:  # jak więcej niż 1 → niedopisuj
                continue

            for rit in sl[site][cover]:
                if rit not in obecne:
                    sql = \
                        'insert into f_arod_phenomena ' + \
                        '(arodes_int_num, ' + \
                        'phen_rank_order, ' + \
                        'phenomena_cd, ' + \
                        'plant_cd, ' + \
                        'nature_mon_fl) values (' + \
                        f"{inum}, {cur_phen}, 'PŁAT ROŚ', '{rit}', 'N');"
                    if baza.wpisz(sql):
                        dopisane += 1
                        cur_phen += 1
                    else:
                        bledy += 1

        ile_ok += 1

    if bledy == 0:
        iface.messageBar().pushMessage(
            "OK",
            f'Dopisane rosliny w {ile_ok} bazie/bazach, '
            f'({dopisane} rośliny)'
            '(szczegóły w logu Las-R)',
            Qgis.Success,
            10
        )
    else:
        iface.messageBar().pushMessage(
            "BŁĄD",
            f'Dopisałem rosliny w {ile_ok} bazie/bazach, (szczegóły:'
            f' Błędów: {bledy}, dopisanych roślin: {dopisane})',
            Qgis.Warning,
            10
        )
