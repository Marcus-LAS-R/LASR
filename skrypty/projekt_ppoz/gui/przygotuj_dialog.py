# -*- coding: utf-8 -*-
"""Dialog "Przygotuj warstwy i bazę" (PPOŻ materiały) - ten sam przebieg co
w NTG (protokol_ntg/gui/przygotuj_dialog.py): łączenie WYDZ, ODDZ, OBR,
GMIN, LS i baz TPU, anonimizacja bazy, WYDZ_DOPISANE. Inny folder
eksportu i nazwa bazy; granice nadleśnictw opcjonalne."""
from ...protokol_ntg.gui.przygotuj_dialog import PrzygotujDialog

FOLDER_EKSPORTU = "_PPOZ"         # '_' -> pomijany przy szukaniu danych
NAZWA_BAZY = "Baza_PPOZ_polaczona_BDO.mdb"


class PrzygotujPpozDialog(PrzygotujDialog):
    TYTUL = "PPOŻ - Przygotuj warstwy i bazę"
    KLUCZ = "LASR/projekt_ppoz/"
    SKROT = "PPOZ"
    FOLDER_EKSPORTU = FOLDER_EKSPORTU
    NAZWA_BAZY = NAZWA_BAZY
    NAZWA_BAZY_STARA = None
    NADL_WYMAGANE = False
