"""Wspólne helpery do budowania kodów administracyjnych z atrybutów
warstwy WYDZ/DZKAT (COUNTY/DISTRICT/MUNICIP/COMMUNITY) - używane przez
core/protokol.py, core/dzkat_kontrola.py i core/przetworz.py, żeby nie
dublować tej samej konkatenacji w trzech miejscach."""

from ...funkcje import isNone


def kod_gminy(feat):
    return isNone(feat['COUNTY']) + isNone(feat['DISTRICT']) + isNone(feat['MUNICIP'])


def kod_obrebu(feat):
    return kod_gminy(feat) + isNone(feat['COMMUNITY'])
