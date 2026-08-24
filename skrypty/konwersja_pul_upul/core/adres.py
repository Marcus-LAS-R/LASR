"""Parsowanie adresu leśnego PUL (RDLP-based, Lasy Państwowe) i budowa
adresu UPUL (TERYT-based, właściciele prywatni/gminni). Oba formaty mają
po 25 znaków - zweryfikowane na realnych danych z materiały/PUL oraz na
już istniejącym, działającym kodzie (shp_adr_les.py buduje UPUL,
shp_doliterkuj._rozbierz_adr_les go z powrotem parsuje).
"""

from ...shp_adr_les import zbuduj_adres as zbuduj_adres_upul  # noqa: F401


def rozbierz_adres_pul(adr):
    """Rozbija 25-znakowy adres leśny PUL na składowe. Offsety
    zweryfikowane na realnym przykładzie z materialy/PUL
    ("28-14-1-30-01    -a   -00" - RZI_Wroclaw_Pstraze):
    RDLP[0:2]-NADL[3:5]-OBRĘB_LEŚNY[6]-LEŚNICTWO[8:10]-ODDZ[11:17]
    -WYDZ[18:22]-SUFIKS[23:25]. Zwraca None gdy adr nie ma długości 25."""
    if not adr or len(adr) != 25:
        return None
    return {
        'rdlp': adr[0:2],
        'nadl': adr[3:5],
        'obreb_lesny': adr[6],
        'lesnictwo': adr[8:10],
        'oddz': adr[11:17].strip(),
        'wydz': adr[18:22].strip(),
        'sufiks': adr[23:25],
    }


# --- kierunek UPUL -> PUL: zarezerwowane miejsce, NIE zaimplementowane ---
# (core/spatial_match.dopasuj_obreby() jest już wystarczająco generyczna,
# żeby dla tego kierunku wystarczyło podać NADLESNICTWA.shp + inną funkcję
# ekstrakcji klucza (reg_cd,ins_cd) zamiast klucz_teryt_z_jpt_kod_je - bez
# zmian w silniku kopiowania).

def rozbierz_adres_upul(adr):
    """TODO (v2, UPUL->PUL): parser adresu UPUL analogiczny do
    shp_doliterkuj._rozbierz_adr_les, zwracający też county_l/district/grp
    (nie tylko municip/community/oddz/wydz, których wystarcza do
    kierunku PUL->UPUL)."""
    raise NotImplementedError('Kierunek UPUL -> PUL nie jest zaimplementowany.')


def zbuduj_adres_pul(*args, **kwargs):
    """TODO (v2, UPUL->PUL): budowa adresu PUL z dopasowania względem
    NADLESNICTWA.shp (reg_cd/ins_cd) zamiast obreby_ewidencyjne.shp."""
    raise NotImplementedError('Kierunek UPUL -> PUL nie jest zaimplementowany.')
