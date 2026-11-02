# -*- coding: utf-8 -*-
"""Rachunek rozliczenia powierzchni, wspólny dla pełnego rozliczenia
(baza_rozlicz_pow_wydz.py) i rozliczenia użytków z Edytora opisu
(opis_rozliczenie.py) - oba muszą dawać te same liczby. Bez QGIS-a.

Rozliczenie dotyczy użytku, nie wydzielenia: powierzchnia rejestrowa użytku
dzielona jest proporcjonalnie między wszystkie wydzielenia, które na nim leżą.
"""
TOLERANCJA_CALEGO = 0.0005  # [ha] - użytek uznany za pokryty w całości


def do_rozliczenia(suma_graf, pow_rej, pow_graf):
    """(cały użytek?, pow. rejestrowa do rozliczenia, pow. graficzna do
    rozliczenia, brak pow. graficznej?). Gdy wydzielenia pokrywają tylko część
    użytku, pow. rejestrowa liczona jest z proporcji."""
    if abs(suma_graf - pow_graf) <= TOLERANCJA_CALEGO:
        return True, pow_rej, pow_graf, False
    if pow_graf > 0:
        return False, round((pow_rej * suma_graf) / pow_graf, 4), suma_graf, \
            False
    return False, 0.0, suma_graf, True


def podziel(uz, pow_rej, pow_graf):
    """[[ADR_LES, pow. rejestrowa], ...] od największej. uz: {ADR_LES: pow.
    graficzna}."""
    return sorted([[k, round((v * pow_rej) / pow_graf, 4)]
                   for k, v in uz.items()],
                  reverse=True, key=lambda x: x[1])


def z_poprawka(podzial, pow_rej):
    """Różnica do pow. rejestrowej trafia do największego wydzielenia. Zwraca
    wielkość poprawki (0, gdy suma się zgadza)."""
    if round(pow_rej, 4) == round(sum(x[1] for x in podzial), 4):
        return 0
    poprawka = round(pow_rej - sum(x[1] for x in podzial), 4)
    podzial[0][1] = round(podzial[0][1] + poprawka, 4)
    return poprawka


def rozlicz_uzytek(uz, pow_rej, pow_graf):
    """Komplet rachunku dla użytku: lista [[ADR_LES, pow.], ...]."""
    _caly, rej, graf, _brak = do_rozliczenia(
        round(sum(uz.values()), 4), pow_rej, pow_graf)
    podzial = podziel(uz, rej, graf)
    z_poprawka(podzial, rej)
    return podzial


def zabiegi_po_zmianie(zabiegi, stara, nowa):
    """Zabiegi wydzielenia po zmianie powierzchni: [(kod, nowa pow.)] tylko
    tych, które się zmieniają. Procent powierzchni zostaje, zmieniają się
    hektary; zabieg bez procentu - proporcjonalnie do zmiany powierzchni.
    zabiegi: [(kod, CUTTING_AREA, PROC_AREA)]."""
    wyn = []
    for kod, obecna, procent in zabiegi:
        if procent is not None:
            pow_nowa = round(nowa * float(procent) / 100, 4)
        elif obecna is not None and stara:
            pow_nowa = round(float(obecna) * nowa / stara, 4)
        else:
            continue
        if obecna is None or round(float(obecna), 4) != pow_nowa:
            wyn.append((kod, pow_nowa))
    return wyn
