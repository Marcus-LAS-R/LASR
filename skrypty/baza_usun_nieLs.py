import os
import platform
import glob
from PyQt5.QtWidgets import QFileDialog

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza


def UsunNieLs(iface):
    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow(), "Katalog z bazami danych", ""
    )

    if platform.system()[:3] == "Win":
        bazy_sc = glob.glob(os.path.join(bazy_kat, "*.mdb"))
    else:
        bazy_sc = glob.glob(os.path.join(bazy_kat, "*.sqlite"))

    ile_baz = len(bazy_sc)
    if ile_baz == 0:
        iface.messageBar().pushMessage(
            "BŁĄD", "Nie znalazłem żadnej bazy taksatora...", Qgis.Critical, 10
        )
        return

    bledy = 0
    ile_ok = 0
    for sc in bazy_sc:
        baza = Baza(sc)
        # jezeli nie mozna polaczyc sie z bazą pomin ją
        if not baza.polacz():
            QgsMessageLog.logMessage("Nie mogłem połączyć sięz bazą: " + sc, "Las-R")
            continue

        QgsMessageLog.logMessage(
            "\n" + 20 * "-" + "\nPrzetwarzam bazę: " + sc, "Las-R", Qgis.Info
        )

        baza.utworz_kopie("kasuj_nieLs")
        wyn = CzyscBaze(baza)
        ile_ok += 1
        bledy += wyn[0]

        QgsMessageLog.logMessage("\n" + 20 * "-", "Las-R", Qgis.Info)

    if bledy == 0:
        iface.messageBar().pushMessage(
            "OK",
            "Skasowałem działki bez Ls w " + str(ile_ok) + " bazie/bazach, "
            "(szczegóły w logu Las-R)",
            Qgis.Success,
            10,
        )
    else:
        iface.messageBar().pushMessage(
            "BŁĄD",
            "Skasowałem działki bez Ls w " + str(ile_ok) + " bazie/bazach"
            ", Błędów: " + str(bledy),
            Qgis.Warning,
            10,
        )


def CzyscBaze(baza):  # noqa
    # wszystkie dzialki w bazie
    wszystkie = set(
        x[0] for x in baza.pobierz("select distinct PARCEL_INT_NUM from F_PARCEL;")
    )

    # dzialki, na ktorych wystepuje uzytek Ls
    z_ls = set(
        x[0]
        for x in baza.pobierz(
            "select distinct PARCEL_INT_NUM from F_PARCEL_LAND_USE "
            "where AREA_USE_CD = 'Ls';"
        )
    )

    # dzialki bez uzytku Ls - do usuniecia razem z calym ich powiazaniami
    do_usuniecia = wszystkie - z_ls

    QgsMessageLog.logMessage(
        "Znaleziono działek bez użytku Ls: " + str(len(do_usuniecia)),
        "Las-R",
        Qgis.Info,
    )

    # wartosci początkowe do statystyk
    f_parcel_cnt_b = baza.pobierz("select count(*) from f_parcel;")[0][0]
    f_parcel_land_use_cnt_b = baza.pobierz("select count(*) from f_parcel_land_use;")[
        0
    ][0]
    f_parcel_part_cnt_b = baza.pobierz("select count(*) from v_parcel_participation;")[
        0
    ][0]
    v_addr_cnt_b = baza.pobierz("select count(*) from v_address;")[0][0]

    bledy_pid = []  # tab z nieskasowanymi PARCEL_INT_NUM
    for pid in do_usuniecia:
        sql = (
            "delete * from F_PARCEL_LAND_USE WHERE PARCEL_INT_NUM = "
            + str(pid)
            + ";"
        )
        if not baza.wpisz(sql):
            bledy_pid.append(pid)
            QgsMessageLog.logMessage(
                "Błąd kasowania pid F_PARCEL_LAND_USE: " + str(pid), "Las-R"
            )

        sql = "delete * from F_PARCEL WHERE PARCEL_INT_NUM = " + str(pid) + ";"
        if not baza.wpisz(sql):
            if pid not in bledy_pid:
                bledy_pid.append(pid)
                QgsMessageLog.logMessage(
                    "Błąd kasowania pid F_PARCEL: " + str(pid), "Las-R"
                )

        sql = (
            "delete * from V_PARCEL_PARTICIPATION WHERE "
            "PARCEL_INT_NUM = " + str(pid) + ";"
        )
        if not baza.wpisz(sql):
            if pid not in bledy_pid:
                bledy_pid.append(pid)
                QgsMessageLog.logMessage(
                    "Błąd kasowania pid V_PARCEL_PARTICIPATION: " + str(pid), "Las-R"
                )

    # usun z V_ADDRESS wlascicieli, ktorzy nie maja juz zadnej dzialki w
    # V_PARCEL_PARTICIPATION (np. byli przypisani tylko do skasowanych dzialek)
    sql = "select distinct addr_nr from v_parcel_participation;"
    twl_temp = baza.pobierz(sql)  # tablica wlasnosci
    twl = [x[0] for x in twl_temp]

    sql = "select distinct addr_nr, second_addr_nr " + "from v_parcel_participation;"
    twl_temp2 = baza.pobierz(sql)  # tablica wlasnosci
    twl += [x[1] for x in twl_temp2 if x[0] in twl]

    sql = "select distinct addr_nr from v_address;"
    tadr = baza.pobierz(sql)  # tablica wlasnosci

    bledy_adr = []
    sql = "delete * from V_ADDRESS WHERE ADDR_NR = "
    for adr in tadr:
        if adr[0] not in twl:
            if not baza.wpisz(sql + str(adr[0]) + ";"):
                bledy_adr.append(adr[0])

    # sprawdz czy nie trzeba wyczyscic obrebow/gmin w F_COMMUNITY, ktore nie
    # maja juz zadnej dzialki w F_PARCEL, po skasowaniu dzialek bez Ls
    sql = "select municipality_cd, community_cd from f_parcel;"
    fpt = baza.pobierz(sql)
    fps = set([x[0] + "-" + x[1] for x in fpt])
    sql = "select municipality_cd, community_cd from f_community;"
    comt = baza.pobierz(sql)
    com = [x[0] + "-" + x[1] for x in comt]
    for c in com:
        if c not in fps:
            municip, community = c.split("-")
            sql = (
                "delete * from F_COMMUNITY WHERE MUNICIPALITY_CD = '"
                + municip
                + "' AND COMMUNITY_CD = '"
                + community
                + "';"
            )
            if not baza.wpisz(sql):
                QgsMessageLog.logMessage(
                    "Nie udało się usunąć obrębu z COMMUNITY: " + str(c), "Las-R"
                )
            else:
                QgsMessageLog.logMessage(
                    "skasowałem w F_COMMUNITY: " + str(c[:9]), "Las-R", Qgis.Info
                )

    # statystyki po usuwaniu
    f_parcel_cnt_k = baza.pobierz("select count(*) from f_parcel;")[0][0]
    f_parcel_land_use_cnt_k = baza.pobierz("select count(*) from f_parcel_land_use;")[
        0
    ][0]
    f_parcel_part_cnt_k = baza.pobierz("select count(*) from v_parcel_participation;")[
        0
    ][0]
    v_addr_cnt_k = baza.pobierz("select count(*) from v_address;")[0][0]

    QgsMessageLog.logMessage(
        "\nUsuniętych rekordów:\nF_PARCEL: "
        + str(f_parcel_cnt_b - f_parcel_cnt_k)
        + "\nF_PARCEL_LAND_USE: "
        + str(f_parcel_land_use_cnt_b - f_parcel_land_use_cnt_k)
        + "\nV_PARCEL_PARTICIPATION: "
        + str(f_parcel_part_cnt_b - f_parcel_part_cnt_k)
        + "\nV_ADDRESS: "
        + str(v_addr_cnt_b - v_addr_cnt_k),
        "Las-R",
        Qgis.Info,
    )

    return [len(bledy_adr) + len(bledy_pid), bledy_pid, bledy_adr]
