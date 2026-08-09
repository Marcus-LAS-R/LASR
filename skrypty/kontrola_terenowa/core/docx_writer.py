"""Renderowanie docx (docxtpl) dla materiałów do kontroli terenowej.

Wymaga zainstalowanego pakietu docxtpl w Pythonie QGIS (`pip install
docxtpl` w powłoce OSGeo4W) - żaden inny skrypt w pluginie dotąd tego
nie potrzebował. `import docxtpl` jest CELOWO wewnątrz funkcji (nie na
górze modułu) - las_r.py importuje cały pakiet kontrola_terenowa przy
starcie QGIS-a (jak każdy inny skrypt), więc gdyby docxtpl nie było
zainstalowane, eager import na górze tego pliku wywaliłby cały plugin
zamiast tylko tej jednej funkcji. gui/dialog.py robi jawne `import
docxtpl` przed wywołaniem czegokolwiek stąd, żeby pokazać czytelny
komunikat zamiast tracebacka.
"""

import datetime
import os

_SZABLONY_KAT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'szablony')
SZABLON_OT = os.path.join(_SZABLONY_KAT, 'szablon_ot.docx')
SZABLON_PROTOKOL = os.path.join(_SZABLONY_KAT, 'szablon_protokol.docx')


def _dzis():
    return datetime.date.today().strftime('%Y-%m-%d')


def zapisz_ot(sciezka_docelowa, nadlesnictwo, grupy):
    """grupy: [{'naglowek': 'Nazwa obrębu (kod)', 'tabela_ot': [...]}]
    - jedna osobna tabela na obręb, budowana w core/ot_docx.py
    (patrz tam po uzasadnienie, czemu nie da się tego zrobić samym
    docxtpl {%tr for %})."""
    from docxtpl import DocxTemplate
    from . import ot_docx

    tpl = DocxTemplate(SZABLON_OT)
    subdoc = ot_docx.zbuduj_subdoc(tpl, grupy)
    tpl.render({
        'nadlesnictwo': nadlesnictwo,
        'data': _dzis(),
        'tabela_ot': subdoc,
    })
    tpl.save(sciezka_docelowa)


def zapisz_protokol(sciezka_docelowa, nadlesnictwo, wiersze):
    from docxtpl import DocxTemplate
    tpl = DocxTemplate(SZABLON_PROTOKOL)
    tpl.render({
        'nadlesnictwo': nadlesnictwo,
        'data': _dzis(),
        'wiersze': wiersze,
    })
    tpl.save(sciezka_docelowa)
