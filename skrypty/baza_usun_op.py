import os
import glob
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza


def UsunOP(iface):
    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow,
        "Katalog z bazami danych",
        '')
    ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))
    if ile_baz == 0:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie znalazłem żadnej bazy taksatora...',
            Qgis.Critical,
            10
        )

    bledy = 0
    ile_ok = 0
    for sc in bazy_kat:
        baza = Baza(sc)
        # jezeli nie mozna polaczyc sie z bazą pomin ją
        if not baza.polacz():
            continue

        baza.utworz_kopie('kasuj_OP')
        wyn = CzyscBaze(baza)
        ile_ok += 1
        bledy += wyn[0]

    if bledy == 0:
        iface.messageBar().pushMessage(
            "OK",
            'Skasowałem OP w ' + str(ile_ok) + ' bazie/bazach',
            Qgis.Success,
            10
        )
    else:
        iface.messageBar().pushMessage(
            "BŁĄD",
            'Skasowałem OP w ' + str(ile_ok) + ' bazie/bazach'
            ', Błędów: ' + str(bledy),
            Qgis.Warning,
            10
        )


def CzyscBaze(baza):  # noqa
    sql = """
    SELECT
        F_PARCEL.MUNICIPALITY_CD,
        F_PARCEL.COMMUNITY_CD,
        F_PARCEL.PARCEL_NR,
        F_PARCEL.PARCEL_INT_NUM,
        V_ADDRESS.addr_grp_fl
    FROM
        (F_PARCEL INNER JOIN V_PARCEL_PARTICIPATION ON
        F_PARCEL.PARCEL_INT_NUM = V_PARCEL_PARTICIPATION.parcel_int_num)
        INNER JOIN V_ADDRESS ON
        V_PARCEL_PARTICIPATION.addr_nr = V_ADDRESS.ADDR_NR;
    """
    # pobierz wszystkie działki
    dz_wszystkie = baza.pobierz(sql)

    # wybierz dzialki tylko z wlascicielami OP
    sl = {}
    for k in dz_wszystkie:
        key = "-".join(map(str, k[:4]))
        if key not in sl:
            sl[key] = []
        sl[key].append(k[-1])

    bledy_pid = []  # tab z nieskasowanymi dzkatami OP
    slu = []  # sl z PARCEL_INT_NUM usunietymi z F_PARCEL i F_PARCEL_LAND_USE
    for key, val in sl.items():
        if len(set(val)) == 1 and 'OP' in set(val):
            pid = key.split('-')[-1]
            sql = 'delete * from F_PARCEL_LAND_USE WHERE PARCEL_INT_NUM = ?;'
            if baza.wpisz_tab(sql, (pid)):
                slu.append(pid)
            else:
                bledy_pid.append(pid)

            sql = "delete * from F_PARCEL WHERE PARCEL_INT_NUM = ?;"
            if not baza.wpisz_tab(sql, (pid)):
                if pid not in bledy_pid:
                    bledy_pid.append(pid)

            sql = 'delete * from F_PARCEL_PARTICIPATION WHERE '\
                'PARCEL_INT_NUM = ?;'
            if not baza.wpisz_tab(sql, (pid)):
                if pid not in bledy_pid:
                    bledy_pid.append(pid)

    sql = 'select distinct addr_nr from v_parcel_participation;'
    twl_temp = baza.pobierz(sql)  # tablica wlasnosci
    twl = [x[0] for x in twl_temp]

    sql = 'select distinct addr_nr from v_address;'
    tadr = baza.pobierz(sql)  # tablica wlasnosci

    bledy_adr = []
    sql = 'delete * from V_ADDRESS WHERE ADDR_NR = '
    for adr in tadr:
        if adr[0] not in twl:
            if not baza.wpisz(sql+str(adr[0])+';'):
                bledy_adr.append(adr[0])

    # sprawdz czy nie trzeba wyczyscic community, po czyszczeniu poprzednich
    # tabel
    sql = 'select municipality_cd, community_cd from f_parcel;'
    fpt = baza.pobierz(sql)
    fps = set([x[0]+'-'+x[1] for x in fpt])
    sql = 'select municipality_cd, community_cd from f_community;'
    comt = baza.pobierz(sql)
    com = [x[0]+'-'+x[1] for x in comt]
    for c in com:
        if c not in fps:
            sql = 'delete * from F_COMMUNITY WHERE MUNICIPALITY_CD = ' + \
                str(c.split('-')[0]) + ' COMMUNITY_CD = ' + \
                str(c.split('-')[1]) + ';'
            if not baza.wpisz(sql):
                QgsMessageLog.logMessage(
                    'Las-R',
                    'Nie udało się usunąć obrębu z COMMUNITY: ' + str(c),
                )

    return [len(bledy_adr)+len(bledy_pid), bledy_pid, bledy_adr]
