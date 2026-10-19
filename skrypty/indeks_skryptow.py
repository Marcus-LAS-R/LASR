# -*- coding: utf-8 -*-
"""Indeks skryptów wtyczki do wyszukiwarki (pasek QGIS, Ctrl+K) i okna
"Zarządzaj ulubionymi" + czysta logika szukania (bez Qt - testowalna poza
QGIS-em, testy/test_indeks_skryptow.py).

Klucz = identyfikator akcji = nazwa atrybutu w las_r.py (self.kas_op ->
'kas_op'). Nazwa, ścieżka w menu i tooltip brane są na żywo z menu
(spis_skryptow.py) - tu tylko to, czego w menu nie ma:
- dawne: dawne nazwy w menu (z historii gita las_r.py) - wynik pokazuje
  "dawniej: ...",
- dawne_id: dawne identyfikatory - lista ulubionych przepisywana na nowy,
- slowa: słowa kluczowe (czynność, obiekt, dane/formaty, etap pracy,
  określenia potoczne).

ZASADA: przy zmianie nazwy skryptu w menu stara nazwa trafia do 'dawne',
przy zmianie nazwy atrybutu akcji stary identyfikator - do 'dawne_id';
nowa akcja = nowy wpis (pilnuje testy/test_indeks_skryptow.py).
"""
import re
import unicodedata


def _w(slowa='', dawne=(), dawne_id=()):
    return {'slowa': slowa, 'dawne': tuple(dawne),
            'dawne_id': tuple(dawne_id)}


INDEKS = {
    # --- menu główne
    'a_opis_taks': _w(
        'edytor opis taksacyjny karta wydzielenie taksator podgląd edycja '
        'klepanie wpisywanie warstwy gatunki masa zasobność zd zadrzewienie '
        'nowe wydzielenie przeadresowanie adres leśny F_SUBAREA'),
    'a_co_nowego': _w('changelog zmiany wersja nowości aktualizacja '
                      'historia zmian'),

    # --- Przygotowanie danych
    'kas_op': _w('usuń skarb państwa OP działki właściciel własność baza '
                 'czyszczenie państwowe'),
    'kas_niels': _w('usuń działki bez Ls użytek leśny nieleśne baza '
                    'czyszczenie'),
    'spr_popraw_ls': _w('kontrola sprawdź Ls użytek leśny baza zapis '
                        'popraw klasoużytki'),
    'przyg_dzewid': _w('działki ewidencyjne DZKAT EGiB geoportal warstwa '
                       'przygotowanie ewidencja'),
    'przyg_ls': _w('Ls użytek leśny działki stara wersja'),
    'przyg_ls_test': _w(
        'Ls lsy użytek leśny działki KLU klasoużytki geometria wydziel '
        'przygotowanie nawigator', dawne=['Przygotuj Lsy TEST']),
    'przyg_ls_wydz': _w('Ls lsy użytek leśny wydzielenia EGiB import bez '
                        'opisu użytku przygotowanie'),
    'a_snapuj': _w('snap przysnapuj dociągnij dociąganie granice działki '
                   'stara wersja'),
    'a_snapuj_nowy': _w(
        'snap snapowanie dociągnij dociąganie granice Ls DZKAT działki '
        'topologia koincydencja pokrywanie', dawne=[
            'Przysnapuj do działek (nowy)']),
    'przyg_teren': _w('teren taksator warstwy pliki wyjazd przygotowanie '
                      'mapy terenowe'),
    'a_przyg_dla_taksatora': _w('spakuj zip archiwum taksator teren paczka '
                                'wysyłka dane'),
    'dop_dzkat': _w('kontrola DZKAT działki katastralne baza porównanie '
                    'rozbieżności F_PARCEL',
                    dawne=['Kontrla DZKAT z bazką']),
    'spr_kontr_ls': _w('kontrola Ls użytek leśny baza porównanie '
                       'rozbieżności nawigator'),
    'a_przygotuj_baze_ewid': _w('nowa baza utwórz EWID ewidencja działki '
                                'geoportal właściciel mdb'),
    'a_utworz_baze_gml': _w('nowa baza utwórz GML EGiB działki klasoużytki '
                            'właściciele udziały małżonek mdb TERYT'),

    # --- Rozliczenie powierzchni
    'lacz_karty': _w('połącz scal pomiary karty taksatorzy duplikaty '
                     'warstwy pomiarowe teren',
                     dawne=['Polacz karty od taksatorów']),
    'przyg_ciec': _w('cięcie przygotuj wydzielenia rozliczenie pomiary '
                     'obręb'),
    'a_usun_nadm_adr': _w('usuń adr_upul punkty OBR nadmiarowe poza '
                          'obrębem czyszczenie'),
    'przyg_klep': _w('sprawdź cięcie karty pomiarowe klepanie PNSW kontrola '
                     'wydzielenia adresy',
                     dawne=['Sprawdź karty w wydzieleniach',
                            'Stwórz listę adresów do klepania']),
    'zanum': _w('numeruj zanumeruj oddziały numeracja ODDZ'),
    'dop_w_o': _w('dopisz ODDZ oddział numer wydzielenia WYDZ uzupełnij '
                  'bez nadpisania',
                  dawne=['Dopisz oddziały do wydzieleń']),
    'zalit': _w('literuj literkuj literowanie literkowanie litery '
                'wydzielenia nadaj WYDZ'),
    'dop_adrles': _w('adres leśny ADR_LES zaadresuj utwórz adresy '
                     'wydzielenia', dawne=['Zaadresuj [ADR_LES]']),
    'dopisz_wydz': _w('dopisz uzupełnij wydzielenia baza F_ARODES brakujące '
                      'nowe z warstwy'),
    'rozlicz_wydz': _w('rozlicz powierzchnia pow graficzna wydzielenia '
                       'baza zapis', dawne=['Rozlicz powierzchnię wydz.']),
    'dop_pnsw': _w('PNSW powierzchnie niezalesione dopisz uzupełnij baza',
                   dawne=['Dopisz PNSW']),
    'przyg_rap': _w('raport karty klepanie excel zestawienie numery kart '
                    'lista'),
    'a_fstspec': _w('napraw F_STOREY_SPECIES gatunki piętra warstwy '
                    'kolejność PRZES puste baza naprawa'),
    'klon': _w('klonuj kopiuj opisy wydzielenia podział KLON.txt '
               'zabiegi nadpisz', dawne=['Klonuj wydzielenia w bazie']),
    'a_dop_ros': _w('rośliny runo podszyt gatunki dopisz baza'),
    'dop_fo': _w('formy ochrony przyrody FOP natura 2000 rezerwat dopisz '
                 'baza F_OCHRONY'),
    'dop_zab_nowe': _w('zabiegi gospodarcze cięcia pielęgnacje dopisz '
                       'sprawdź wygeneruj baza CP',
                       dawne=['Zabiegi dopisz/sprawdź',
                              'Zabiegi dopisz/sprawdź (nowe)'],
                       dawne_id=['dop_zab']),
    'kasr': _w('skasuj usuń wydzielenia baza rekordy opis kasowanie',
               dawne=['Skasuj wydz w bazie [wydz]']),
    'kasw': _w('skasuj usuń wydzielenia warstwa geometria poligony '
               'kasowanie'),
    'dolit': _w('doliteruj literuj literkuj litery brakujące wydzielenia '
                'kontynuacja literowania'),
    'przelit': _w('przeliterkuj literuj od nowa litery wszystkie '
                  'wydzielenia zmiana oznaczeń',
                  dawne=['Przeliterkuj (Całość)']),

    # --- Aktualizacja UPUL
    'a_aktualizuj_strukture': _w('aktualizuj struktura baza migracja stary '
                                 'UPUL tabele pola standard'),
    'a_aktualizacja_shp': _w('aktualizuj struktura SHP warstwy konwersja '
                             'stary standard', dawne=['Aktualizacja SHP']),
    'a_konwertuj_pul_upul': _w('konwertuj konwersja PUL UPUL lasy '
                               'państwowe adres leśny'),
    'a_przyg_ls_chama': _w('Ls lsy na chama prototyp jednorazowe '
                           'powierzchnia'),
    'a_eksport_shp_gml': _w('eksport SHP GML EGiB działki kontury '
                            'klasyfikacyjne idDzialki wyeksportuj'),
    'a_rozdziel_wg_baz': _w('rozdziel warstwy bazy DZKAT LS OBR podfoldery '
                            'F_PARCEL wspólnoty'),
    'a_aktualizacja_baz': _w('aktualizuj baza 10 lat plus dziesięć okres '
                             'planu przesuń wiek F1 F2 F3 F4 masa',
                             dawne=['Aktualizacja baz']),
    'a_przyg_dotaks': _w('DOTAKS dotaks warstwy porównanie stary nowy opis '
                         'nielas', dawne=['Przygotuj warstwy dotaks']),
    'a_przyg_stare_wydz': _w('stare wydzielenia WYDZ cięcie przygotuj '
                             'poprzedni plan metadane',
                             dawne=['Przygotuj stare wydzielenia do '
                                    'cięcia']),
    'a_warstwa_opisow': _w(
        'edytor warstwy opisów Klon KLON.txt punkty grupy INNE WYL notatki '
        'opis_pkt',
        dawne=['Edytuj warstwy do opisów', 'Utwórz warstwy do opisów',
               'Utwórz warstwę do opisów',
               'Utwórz/edytuj warstwy do opisów']),
    'a_sprawdz_polozenie_opisow': _w(
        'sprawdź cięcie starych WYDZ położenie opis_pkt opis_klon notatki '
        'adr_upul WYDZ_PKT_stare PNSW kontrola',
        dawne=['Sprawdź położenie warstw opisowych',
               'Sprawdź położenie warstw punktowych (opisów)']),
    'a_dopisz_dane_wydz': _w('przepisz ODDZ WYDZ stare wydzielenia punkty '
                             'uzupełnij dane',
                             dawne=['Dopisz dane do wydzieleń']),
    'a_dop_adrles_stare_wydz': _w('adres leśny ADR_LES stare wydzielenia '
                                  'utwórz zaadresuj'),
    'a_synchronizuj_wydz': _w('usuń nadmiarowe WYDZ baza synchronizuj '
                              'adresy grupa porównanie'),
    'a_dop_w_o_upul': _w('dopisz ODDZ oddział WYDZ wydzielenia uzupełnij '
                         'bez nadpisania',
                         dawne=['Dopisz oddziały do wydzieleń']),
    'a_dolit_upul': _w('doliteruj literuj literkuj litery pozostałe '
                       'wydzielenia SHP baza F_ARODES',
                       dawne=['Doliteruj wydzielenia']),
    'a_dop_adrles_upul': _w('adres leśny ADR_LES pozostałe nowe '
                            'wydzielenia utwórz zaadresuj',
                            dawne=['Utwórz adresy leśne']),
    'a_uzup_wydz_nowe': _w('uzupełnij dopisz wydzielenia baza nowe '
                           'brakujące F_ARODES',
                           dawne_id=['a_uzup_wydz_stare']),
    'a_dopisz_opisy_taks': _w('dopisz generyczne OT opisy taksacyjne '
                              'opis_pkt baza',
                              dawne=['Dopisz opisy taksacyjne do bazy']),
    'a_utworz_klon_txt': _w('raporty KLON KLON.txt NOTATKI notatki '
                            'utwórz klonowanie',
                            dawne=['Utwórz KLON.txt']),
    'a_pobierz_bdl': _w('ściągnij pobierz BDL bank danych o lasach '
                        'internet dane lasy'),
    'a_utworz_baze_bdl': _w('utwórz baza BDL bank danych o lasach nowa '
                            'baza OBR F_COMMUNITY'),

    # --- Aktualizacja ewidencji N-ctwo
    'a_aktualizuj_ewid': _w('aktualizuj użytki ORYG ewidencja '
                            'nadleśnictwo zaktualizuj'),
    'a_buduj_oddzialy': _w('zbuduj oddziały z wydzieleń ODDZ warstwa '
                           'połącz granice'),
    'a_napraw_topo_hier': _w('napraw topologia hierarchia dzew uzyt wydz '
                             'oddz warstwy naprawa'),
    'a_kontrola_topo_hier': _w('kontrola topologia hierarchia dzew uzyt '
                               'wydz oddz warstwy sprawdź'),

    # --- Kontrola danych
    'spr_odl_wydz': _w('sprawdź odległości wymiary wydzielenia normy '
                       'kontrola'),
    'spr_wl_wydz': _w('sprawdź własność forma własności wydzielenia '
                      'kontrola właściciel'),
    'spr_w_o': _w('sprawdź wydzielenia oddziały przypisanie ODDZ '
                  'kontrola'),
    'spr_rozlicz_wydz': _w('sprawdź rozliczenie powierzchnia suma '
                           'oddział obręb kontrola',
                           dawne=['Sprawdz rozliczenie powierzchni wydz.']),
    'spr_wydz': _w('sprawdź wydzielenia kontrola geometria dane ogólna'),
    'spr_topo': _w('sprawdź topologia luki nakładanie przecięcia kontrola '
                   'geometria'),

    # --- Kontrola wg SULMN
    'a_kontrola_slownikow': _w('kontrola słownikowa słowniki SULMN baza '
                               'kody wartości'),
    'a_kontrola_opisow': _w('kontrola opisu taksacyjnego SULMN baza '
                            'walidator błędy opis'),
    'a_aktualizuj_slownik_kontroli': _w('zaktualizuj słownik kontroli '
                                        'Mapa_PU baza kontroli SULMN'),

    # --- pasek LAS-R KP
    'rys_gat': _w('rysuj symbolizacja gatunki styl mapa',
                  dawne=['rysuj gatunki']),
    'rys_zab': _w('rysuj symbolizacja zabiegi styl mapa',
                  dawne=['rysuj zabiegi']),
    'rys_stl': _w('rysuj symbolizacja STL siedliskowy typ lasu styl mapa',
                  dawne=['rysuj STL']),
    'rys_orto': _w('rysuj orto ortofotomapa styl podkład',
                   dawne=['rysuj na orto']),
    'rys_dz': _w('rysuj działki styl DZKAT symbolizacja'),
    'rys_klu': _w('rysuj KLU klasoużytki styl symbolizacja'),
    'a_dopasuj_style': _w('dopasuj style styl symbolizacja warstwy qml'),
    'a_pokaz_lay': _w('pokaż layout wydruk kompozycja mapy'),
    'odzn': _w('odznacz wszystko zaznaczenie unselect'),
    'msplit': _w('rozbij multipoligony multipart singlepart geometria'),

    # --- Narzędziowe
    'a_anon': _w('anonimizuj dane osobowe RODO właściciele baza TPU '
                 'szkolenie test'),
    'a_usun_kw': _w('usuń kwerendy zapytania baza Access mdb'),
    'a_podmien_kw': _w('podmień kwerendy zapytania bazy folder F_TABLICA '
                       'wgraj Access'),
    'a_copy': _w('połącz scal bazy TPU taksatorzy folder BDO jedna baza'),
    'a_wydziel_wlasc': _w('wydziel właścicieli nowa baza eksport działki '
                          'współwłaściciele grupy rejestrowe'),
    'a_rozdziel_upul_isl': _w('rozdziel bazy UPUL ISL inwentaryzacja '
                              'obręby podział'),
    'a_zab_podmien': _w('podmień zamień usuń zabiegi IVDU IVD baza obręby '
                        'forma własności'),
    'dop_wydz': _w('dopisz metadane wydzielenia atrybuty',
                   dawne=['Dopisz atrybuty do wydzieleń',
                          'Dopisz do wydzieleń']),
    'eksp_kml': _w('eksport KML google earth wyeksportuj warstwa'),
    'a_reproj': _w('reprojekcja odwzorowanie układ współrzędnych CRS 1992 '
                   'przelicz warstwy', dawne=['Reprojekcja warstw']),
    'a_uzup_uszkodzen': _w('uzupełnij uszkodzenia D-STAN CAUSE_CD '
                           'DAMAGE_DEGREE przyczyna stopień baza'),
    'a_dop_adm': _w('dodaj uzupełnij MUNICIP COMMUNITY gmina obręb kody '
                    'kolumny',
                    dawne=['Uzupełnij [MUNICIP, COMMUNITY]',
                           'Dodaj [MUNICIP, COMMUNITY]'],
                    dawne_id=['a_dod_adm']),
    'a_dop_own': _w('dopisz OWNERSHIP forma własności działki'),
    'a_czy_kol': _w('usuń wyczyść zawartość kolumny pola atrybuty'),
    'a_puste_wydz': _w('pokaż puste wydzielenia bez opisu baza waypointy '
                       'nawigator'),
    'a_nawigator': _w('nawigator błędów raporty przeskakuj błędy mapa '
                      'waypointy kontrola'),

    # --- Generuj
    'nakl': _w('naklejki etykiety wydruk teczki akta adresowe generuj'),
    'okl': _w('okładki atlas wydruk generuj leśnictwo obręb'),
    'a_rap_wyles': _w('karty wylesień działki raport wylesienie generuj'),
    'a_wyciagi': _w('wyciągi właściciele UPUL plan raport generuj wydruk'),
    'a_kontrola_terenowa': _w('materiały kontrola terenowa mapy '
                              'zestawienia teren generuj'),

    # --- pasek LAS-R
    'dop_meta': _w('dopisz metadane wydzielenia', dawne=['dopisz metadane']),
    'spr_geom': _w('sprawdź geometria błędy poprawność kontrola'),
    'rys_wez': _w('pokaż węzełki wierzchołki węzły geometria'),
    'uutf8': _w('kodowanie UTF-8 utf8 polskie znaki cpg ustaw'),
    'pg': _w('powierzchnia graficzna oblicz pow area'),
    'rys_atl': _w('atlas pola atlasowe rysuj siatka arkusze'),
    'num_atl': _w('atlas numeruj pola numeracja arkusze'),
    'atl_auto': _w('atlas automatycznie pola siatka kafelkowanie arkusze'),
}

# akcje poza wyszukiwarką i ulubionymi (techniczne, bez własnej funkcji)
POMIJANE = {'a_znajdz_skrypt'}


# ---------------------------------------------------------------- szukanie

def normalizuj(tekst):
    """Małe litery bez polskich znaków, separatory -> spacje."""
    tekst = (tekst or '').lower().replace('ł', 'l')
    tekst = ''.join(c for c in unicodedata.normalize('NFKD', tekst)
                    if not unicodedata.combining(c))
    return ' '.join(re.split(r'[^0-9a-z]+', tekst)).strip()


class Wpis:
    """Skrypt w wyszukiwarce: identyfikator, nazwa, ścieżka w menu
    (np. 'Przygotowanie danych › Kasuj OP'), tooltip + dane z INDEKS."""

    def __init__(self, id_, nazwa, sciezka='', tip='', testowe=False):
        self.id = id_
        self.nazwa = nazwa
        self.sciezka = sciezka
        self.tip = tip or ''
        self.testowe = testowe
        ind = INDEKS.get(id_, {})
        self.dawne = list(ind.get('dawne', ()))
        self.slowa = ind.get('slowa', '')
        self._n_nazwa = normalizuj(nazwa)
        self._pola = [
            (self._n_nazwa.split(), 100),
            ([s for d in self.dawne for s in normalizuj(d).split()], 70),
            (normalizuj(self.slowa).split(), 50),
            (normalizuj(sciezka).split(), 30),
            (normalizuj(self.tip).split(), 20),
        ]
        self._n_dawne = [normalizuj(d) for d in self.dawne]


def _pasuje(token, slowa):
    """Słowo zaczyna się od tokenu; dłuższy token (4+) także w środku
    słowa (np. 'snap' w 'przysnapuj')."""
    return any(s.startswith(token) or (len(token) >= 4 and token in s)
               for s in slowa)


def ocen(wpis, zapytanie):
    """(ocena, dawna_nazwa) albo (0, None) - wszystkie słowa zapytania
    muszą się do czegoś dopasować; dawna_nazwa - gdy trafienie tylko po
    dawnej nazwie (do dopisku "dawniej: ...")."""
    tokeny = normalizuj(zapytanie).split()
    if not tokeny:
        return 1, None
    suma = 0
    po_dawnej = True
    for t in tokeny:
        najlepsza = 0
        for slowa, waga in wpis._pola:
            if waga > najlepsza and _pasuje(t, slowa):
                najlepsza = waga
        if not najlepsza:
            return 0, None
        if najlepsza != 70:
            po_dawnej = False
        suma += najlepsza
    calosc = normalizuj(zapytanie)
    if wpis._n_nazwa.startswith(calosc):
        suma += 60
    elif calosc in wpis._n_nazwa:
        suma += 30
    if wpis.testowe:
        suma //= 2
    dawna = None
    if po_dawnej:
        dawna = next((d for d, n in zip(wpis.dawne, wpis._n_dawne)
                      if all(_pasuje(t, n.split()) for t in tokeny)), None)
    return suma, dawna


def szukaj(wpisy, zapytanie, limit=None):
    """[(wpis, dawna_nazwa)] od najlepszego; puste zapytanie - wszystkie
    wg ścieżki w menu."""
    wyn = []
    for w in wpisy:
        o, dawna = ocen(w, zapytanie)
        if o:
            wyn.append((-o, w.testowe, w.sciezka.lower(), w, dawna))
    wyn.sort(key=lambda x: x[:3])
    wyn = [(w, d) for *_r, w, d in wyn]
    return wyn[:limit] if limit else wyn


def nowy_id(id_):
    """Aktualny identyfikator dla dawnego (lista ulubionych) albo id_."""
    if id_ in INDEKS:
        return id_
    return next((k for k, v in INDEKS.items() if id_ in v['dawne_id']), id_)
