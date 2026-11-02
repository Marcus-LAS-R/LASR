# -*- coding: utf-8 -*-
"""Jeden format znacznika czasu w nazwach plików i folderów wtyczki
(raporty, waypointy, kopie baz, warstwy tworzone przez skrypty):
rr-mm-dd_T_gg_mm_ss, np. 26-11-02_T_11_17_05 - nazwy układają się
chronologicznie. Bez QGIS-a."""
from datetime import datetime

FORMAT = '%y-%m-%d_T_%H_%M_%S'


def znacznik(kiedy=None):
    """Znacznik dla podanej chwili (domyślnie: teraz)."""
    return (kiedy or datetime.now()).strftime(FORMAT)
