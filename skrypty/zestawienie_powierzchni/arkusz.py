# -*- coding: utf-8 -*-
"""Zestawienie powierzchni - zapis .xlsx (openpyxl, bez QGIS-a).
Arkusz "Całość" (wszystkie obręby + SUMA) i po jednym arkuszu na bazę
(jej obręby + SUMA)."""
import re

from .dane import KOLUMNY, KOLUMNY_POW

ARKUSZ_CALOSC = 'Całość'
FORMAT_HA = '0.0000'
SZEROKOSCI = (10, 24, 12, 26, 16, 18, 18, 16)
_ZAKAZANE = re.compile(r'[\\/*?:\[\]]')


def unikalna_nazwa(nazwa, zajete):
    """Nazwa arkusza Excela: bez \\ / * ? : [ ], max 31 znaków, bez
    powtórzeń (wielkość liter bez znaczenia) - kolejne z numerem."""
    baza = _ZAKAZANE.sub('_', nazwa or '').strip().strip("'")[:31] or 'Baza'
    nazwa, i = baza, 2
    while nazwa.lower() in zajete:
        dopisek = ' ({})'.format(i)
        nazwa = baza[:31 - len(dopisek)] + dopisek
        i += 1
    zajete.add(nazwa.lower())
    return nazwa


def _arkusz(wb, nazwa, wiersze, style):
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet(nazwa)
    ws.append(list(KOLUMNY))
    for w in wiersze:
        ws.append(w)
    suma = ['SUMA', None, None, None] + [
        round(sum(w[i] for w in wiersze), 4)
        for i in range(KOLUMNY_POW, len(KOLUMNY))]
    ws.append(suma)
    ostatni = ws.max_row
    ws.merge_cells(start_row=ostatni, start_column=1, end_row=ostatni,
                   end_column=KOLUMNY_POW)

    for kom in ws[1]:
        kom.font, kom.fill = style['pogrub'], style['tlo']
        kom.alignment, kom.border = style['naglowek'], style['ramka']
    for wiersz in ws.iter_rows(min_row=2, max_row=ostatni):
        for kom in wiersz:
            kom.border = style['ramka']
            if kom.column > KOLUMNY_POW:
                kom.number_format = FORMAT_HA
    for kom in ws[ostatni]:
        kom.font, kom.fill = style['pogrub'], style['tlo']
    ws[ostatni][0].alignment = style['prawo']

    for i, szer in enumerate(SZEROKOSCI, start=1):
        ws.column_dimensions[get_column_letter(i)].width = szer
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = 'A2'
    return ws


def zapisz(sciezka, bazy):
    """bazy - [(nazwa_arkusza, [wiersze dane.Obreb.wiersz()])]."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    cienka = Side(style='thin', color='808080')
    style = {
        'pogrub': Font(bold=True),
        'tlo': PatternFill('solid', fgColor='D9D9D9'),
        'naglowek': Alignment(horizontal='center', vertical='center',
                              wrap_text=True),
        'prawo': Alignment(horizontal='right'),
        'ramka': Border(left=cienka, right=cienka, top=cienka,
                        bottom=cienka),
    }
    wb = Workbook()
    wb.remove(wb.active)
    zajete = {ARKUSZ_CALOSC.lower()}
    calosc = sorted((w for _, wiersze in bazy for w in wiersze),
                    key=lambda w: (w[0], w[2]))
    _arkusz(wb, ARKUSZ_CALOSC, calosc, style)
    for nazwa, wiersze in bazy:
        _arkusz(wb, unikalna_nazwa(nazwa, zajete), wiersze, style)
    wb.save(sciezka)
