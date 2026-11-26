# -*- coding: utf-8 -*-
"""Wykaz rozbieżności - zapis do .docx (python-docx) na podstawie
szablon_wykaz_rozbieznosci.docx (wzór Łętownia: strona tytułowa
"Dokumentacja geodezyjna" + tabela stan stary / stan nowy).

W szablonie tabela ma 3 wiersze nagłówka i jeden pusty wiersz-wzór
(formatowanie komórek), który jest powielany dla każdego wiersza danych.
Akapity tytułowe "OBRĘB EWIDENCYJNY: {}", "GMINA: {}", "POWIAT: {}" są
wypełniane wg zakresu (obręb / gmina / cały obiekt).

`import docx` CELOWO wewnątrz funkcji - brak pakietu nie może wywalić
całej wtyczki przy starcie QGIS-a (jak w kontrola_terenowa).
"""
import copy
import os

SZABLON = os.path.join(os.path.dirname(__file__),
                       'szablon_wykaz_rozbieznosci.docx')
WIERSZE_NAGLOWKA = 3

_POLA = ('OBRĘB EWIDENCYJNY:', 'GMINA:', 'POWIAT:')


def _ustaw_tekst(akapit, tekst):
    """Tekst w akapicie z zachowaniem formatowania pierwszego przebiegu."""
    if akapit.runs:
        akapit.runs[0].text = tekst
        for r in akapit.runs[1:]:
            r.text = ''
    else:
        akapit.add_run(tekst)


def _tytul(doc, linie):
    """linie: {pole: tekst albo None (akapit usuwany)}."""
    for akapit in list(doc.paragraphs):
        for pole in _POLA:
            if akapit.text.startswith(pole):
                tekst = linie.get(pole)
                if tekst is None:
                    akapit._p.getparent().remove(akapit._p)
                else:
                    _ustaw_tekst(akapit, tekst)
                break


def _wypelnij_komorke(komorka, tekst, zaznacz=False, scal=None):
    """scal: None - bez scalania, 'restart' - pierwsza komórka scalenia
    pionowego, 'continue' - kolejna (pusta, bez przebiegów tekstu)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    akapit = komorka.paragraphs[0]
    for nadmiar in komorka.paragraphs[1:]:
        nadmiar._p.getparent().remove(nadmiar._p)
    if scal == 'continue':
        for r in list(akapit.runs):
            r._r.getparent().remove(r._r)
    else:
        _ustaw_tekst(akapit, tekst)
    tcPr = komorka._tc.get_or_add_tcPr()
    if zaznacz:   # żółte tło - do uzupełnienia/weryfikacji ręcznie
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'FFFF00')
        _zastap(tcPr, shd)
    if scal:
        vm = OxmlElement('w:vMerge')
        if scal == 'restart':
            vm.set(qn('w:val'), 'restart')
        _zastap(tcPr, vm)
        va = OxmlElement('w:vAlign')
        va.set(qn('w:val'), 'center')
        _zastap(tcPr, va)
    _porzadek_tcPr(tcPr)


# kolejność elementów w w:tcPr wg schematu OOXML (Word odrzuca plik przy
# złej kolejności)
_TCPR = ('cnfStyle', 'tcW', 'gridSpan', 'hMerge', 'vMerge', 'tcBorders',
         'shd', 'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign',
         'hideMark')


def _zastap(tcPr, el):
    """Dodaje element do w:tcPr, usuwając istniejący o tej samej nazwie."""
    for stary in tcPr.findall(el.tag):
        tcPr.remove(stary)
    tcPr.append(el)


def _porzadek_tcPr(tcPr):
    def poz(el):
        nazwa = el.tag.split('}')[-1]
        return _TCPR.index(nazwa) if nazwa in _TCPR else len(_TCPR)
    dzieci = sorted(tcPr, key=poz)
    for el in dzieci:
        tcPr.remove(el)
        tcPr.append(el)


# kolumny scalane pionowo: gmina, obręb, nr - w obrębie działki;
# 4a, 4b (stan stary) - w obrębie jednego klasoużytku podzielonego
# na kilka wierszy (jak we wzorze)
KOLUMNY_DZIALKI = (0, 1, 2)
KOLUMNY_KLASOUZYTKU = (3, 4)


def zapisz(sciezka, wiersze, linie_tytulu):
    """wiersze: lista dane.Wiersz; linie_tytulu: patrz _tytul."""
    from docx import Document

    doc = Document(SZABLON)
    _tytul(doc, linie_tytulu)
    tabela = doc.tables[0]
    wzor = tabela.rows[WIERSZE_NAGLOWKA]._tr
    wzor_kopia = copy.deepcopy(wzor)
    wzor.getparent().remove(wzor)

    if not wiersze:
        wiersze = [None]
    from docx.table import _Row

    def klucz_dz(w):
        return None if w is None else (w.gmina, w.obreb, w.nr)

    def klucz_ku(w):
        return None if w is None else (w.gmina, w.obreb, w.nr, w.ksztalt,
                                       w.ku_stary)

    def scalenie(j, klucz):
        k = klucz(wiersze[j])
        if j > 0 and klucz(wiersze[j - 1]) == k:
            return 'continue'
        if j + 1 < len(wiersze) and klucz(wiersze[j + 1]) == k:
            return 'restart'
        return None

    for j, w in enumerate(wiersze):
        tr = copy.deepcopy(wzor_kopia)
        tabela._tbl.append(tr)
        row = _Row(tr, tabela)
        if w is None:
            teksty = ['', '', 'Brak rozbieżności', '', '', '', '', '']
            weryf = ()
            scal_dz = scal_ku = None
        else:
            teksty = w.komorki()
            # do uzupełnienia: brak klasoużytku nowego ze słownika (kol. 5a)
            weryf = (5,) if w.do_weryfikacji else ()
            scal_dz = scalenie(j, klucz_dz)
            scal_ku = scalenie(j, klucz_ku)
        for i, komorka in enumerate(row.cells):
            scal = scal_dz if i in KOLUMNY_DZIALKI else (
                scal_ku if i in KOLUMNY_KLASOUZYTKU else None)
            _wypelnij_komorke(komorka, teksty[i] if i < len(teksty) else '',
                              i in weryf, scal)

    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    doc.save(sciezka)
