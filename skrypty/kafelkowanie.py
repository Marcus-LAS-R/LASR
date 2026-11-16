""" Kafelkowanie stron atlasu / obszarów:

* pokryj_atlas (Atlasuj automatycznie) - kompleksy większe niż strona
  dostają siatkę stron z zakładką (siatka_kompleksu), resztę wydzieleń
  układa pokryj_kaflami. Numerację i sąsiadów L/G/P/D daje numeruj_kafle
  (używane też przez "Przenumeruj atlasy" po ręcznych poprawkach pól).
* pokryj_kaflami (Obszary cięcia, reszta atlasu) - opis poniżej.

Pokrywanie zbioru prostokątów (np. bbox wydzieleń) minimalną liczbą
kafli o ustalonym rozmiarze (np. stron atlasu), tak żeby każdy prostokąt
zmieścił się w całości w jednym kaflu, tam gdzie to możliwe - bez
przecinania krawędzią. Kafle mogą się nachodzić tam, gdzie obiekty leżą
blisko siebie. Obiekt, którego bbox jest większy niż kafel w którymkolwiek
wymiarze (rzadkie, ale zdarza się przy dużych wydzieleniach i drobnej
skali/małym formacie strony) dostaje kafel wycentrowany na sobie i zostaje
przecięty krawędzią - patrz zwracana lista `przeciete`.

Logika nie zależy od qgis.core - operuje na zwykłych krotkach
(xmin, ymin, xmax, ymax), żeby można ją wykorzystać w różnych skryptach
(np. shp_obszary_ciecia.py, shp_atlasuj.py).
"""

import math


def rozmiar_kafla_z_skali(papier_mm, skala, margines_mm=30):
    """ Rozmiar kafla w metrach [szer, wys] na podstawie formatu papieru
    w mm (np. A3 w poziomie = [420, 297]), skali mapy i marginesu
    (zakładki) w mm odejmowanego z każdej strony łącznie.
    """
    return [
        (((papier_mm[0] - margines_mm) / 10) * skala) / 100,
        (((papier_mm[1] - margines_mm) / 10) * skala) / 100,
    ]


def _max_y_overlap(przedzialy):
    """ (licznik, y) punktu o maksymalnym pokryciu wśród podanych
    przedziałów [y0, y1] (domkniętych). """
    eventy = []
    for (y0, y1) in przedzialy:
        eventy.append((y0, 0))
        eventy.append((y1, 1))
    eventy.sort()

    best_cnt, cnt = 0, 0
    best_y = eventy[0][0] if eventy else 0
    i, n = 0, len(eventy)
    while i < n:
        y_cur = eventy[i][0]
        starty = konce = 0
        while i < n and eventy[i][0] == y_cur:
            if eventy[i][1] == 0:
                starty += 1
            else:
                konce += 1
            i += 1
        cnt += starty
        if cnt > best_cnt:
            best_cnt, best_y = cnt, y_cur
        cnt -= konce
    return best_cnt, best_y


def _najlepszy_kafel(anchor, kandydaci, w, h):
    """ Pozycja (wx, wy) lewego-dolnego rogu kafla WxH, który w całości
    obejmuje anchor i maksymalizuje liczbę pokrytych kandydatów. """
    ax0, ay0, ax1, ay1 = anchor
    wx_lo, wx_hi = ax1 - w, ax0
    wy_lo, wy_hi = ay1 - h, ay0

    items = []
    for b in kandydaci:
        x0 = max(b[2] - w, wx_lo)
        x1 = min(b[0], wx_hi)
        if x0 > x1:
            continue
        y0 = max(b[3] - h, wy_lo)
        y1 = min(b[1], wy_hi)
        if y0 > y1:
            continue
        items.append((x0, x1, y0, y1))

    eventy_x = []
    for i, (x0, x1, _, _) in enumerate(items):
        eventy_x.append((x0, 0, i))
        eventy_x.append((x1, 1, i))
    eventy_x.sort()

    aktywne = {}
    best_cnt = 0
    best_wx, best_wy = (wx_lo + wx_hi) / 2, (wy_lo + wy_hi) / 2
    i, n = 0, len(eventy_x)
    while i < n:
        x_cur = eventy_x[i][0]
        starty, konce = [], []
        while i < n and eventy_x[i][0] == x_cur:
            _, typ, idx = eventy_x[i]
            (starty if typ == 0 else konce).append(idx)
            i += 1

        for idx in starty:
            aktywne[idx] = (items[idx][2], items[idx][3])

        if aktywne:
            cnt, y_best = _max_y_overlap(list(aktywne.values()))
            if cnt > best_cnt:
                best_cnt, best_wx, best_wy = cnt, x_cur, y_best

        for idx in konce:
            aktywne.pop(idx, None)

    # wsrod (wx, wy) o tym samym max. pokryciu wybierany jest dowolny
    # punkt skrajny (krawedz jakiegos kandydata) - przez to maly klaster
    # potrafi wyladowac w samym rogu duzego kafla. Wycentruj kafel na
    # obwiedni faktycznie pokrytych kandydatow - nie zmienia to ktore
    # kandydaci sa pokryci (ich obwiednia z definicji miesci sie w wxh),
    # tylko poprawia wygodne wycentrowanie.
    pokryte = [
        b for b in kandydaci
        if best_wx <= b[0] and b[2] <= best_wx + w and
        best_wy <= b[1] and b[3] <= best_wy + h
    ]
    if pokryte:
        ux0 = min(b[0] for b in pokryte)
        uy0 = min(b[1] for b in pokryte)
        ux1 = max(b[2] for b in pokryte)
        uy1 = max(b[3] for b in pokryte)
        best_wx = (ux0 + ux1) / 2 - w / 2
        best_wy = (uy0 + uy1) / 2 - h / 2

    return best_wx, best_wy


def pokryj_kaflami(bboxy, w, h):
    """ Zachłannie pokrywa zbiór prostokątów `bboxy`
    (lista (xmin, ymin, xmax, ymax)) minimalną liczbą kafli o rozmiarze
    w x h. Każdy kolejny kafel jest tak ustawiony, by w całości objąć
    "kotwicę" (pierwszy z kolei nieobsłużony prostokąt, w porządku
    góra-dół/lewo-prawo) i jednocześnie pokryć maksymalną liczbę innych
    pozostałych nieobsłużonych prostokątów. Kotwica, której bbox jest
    większy niż kafel w którymkolwiek wymiarze (nie da się jej w ogóle
    objąć w całości), dostaje zamiast tego kafel wycentrowany na jej
    środku - zostanie przecięta krawędzią, ale nie blokuje reszty (bez
    tego wyjątku algorytm zapętliłby się w nieskończoność: ta sama
    kotwica byłaby wybierana w kółko, nigdy nie znikając z listy
    nieobsłużonych).

    Zwraca (kafle, przeciete):
    * kafle - lista kafli (xmin, ymin, xmax, ymax) w kolejności powstawania.
      Kafle mogą się nachodzić.
    * przeciete - lista indeksów (w `bboxy`) obiektów, które nie zmieściły
      się w całości w żadnym kaflu - do zaraportowania użytkownikowi.
    """
    kolejnosc = sorted(
        range(len(bboxy)),
        key=lambda i: (-((bboxy[i][1] + bboxy[i][3]) / 2),
                       (bboxy[i][0] + bboxy[i][2]) / 2))
    nieobsluzone = kolejnosc

    kafle = []
    przeciete = []
    while nieobsluzone:
        i_anchor = nieobsluzone[0]
        ax0, ay0, ax1, ay1 = anchor = bboxy[i_anchor]
        oversize = (ax1 - ax0) > w or (ay1 - ay0) > h

        if oversize:
            przeciete.append(i_anchor)
            wx = (ax0 + ax1) / 2 - w / 2
            wy = (ay0 + ay1) / 2 - h / 2
        else:
            kandydaci = [
                bboxy[i] for i in nieobsluzone
                if max(ax1, bboxy[i][2]) - min(ax0, bboxy[i][0]) <= w and
                max(ay1, bboxy[i][3]) - min(ay0, bboxy[i][1]) <= h
            ]
            wx, wy = _najlepszy_kafel(anchor, kandydaci, w, h)

        kafel = (wx, wy, wx + w, wy + h)
        kafle.append(kafel)

        rx0, ry0, rx1, ry1 = kafel
        nieobsluzone = [
            i for i in nieobsluzone
            if i != i_anchor and not (
                rx0 <= bboxy[i][0] and bboxy[i][2] <= rx1 and
                ry0 <= bboxy[i][1] and bboxy[i][3] <= ry1)
        ]

    return kafle, przeciete


# ------------------------------------------- kompleksy: siatka z zakładką
#
# Atlasuj automatycznie: rozproszone wydzielenia (i kompleksy mieszczące
# się na jednej stronie) układa pokryj_kaflami - każde w całości. Kompleks
# większy niż strona dostaje regularną siatkę stron (siatka_kompleksu),
# w której sąsiednie strony nachodzą na siebie o `zakladka` wymiaru -
# wydzielenia kompleksu są cięte krawędzią, a pas wspólny pozwala nawiązać
# stronę do sąsiedniej. Bez tego stary tryb mnożył strony przy dużych,
# zwłaszcza wydłużonych wschód-zachód wydzieleniach.


def _odstep(a0, a1, b0, b1):
    """ Odstęp między przedziałami [a0, a1] i [b0, b1] (0, gdy nachodzą
    na siebie albo się stykają). """
    return max(0.0, b0 - a1, a0 - b1)


def _czesc_wspolna(a0, a1, b0, b1):
    """ Długość części wspólnej przedziałów (0, gdy rozłączne). """
    return max(0.0, min(a1, b1) - max(a0, b0))


def miesci_sie(bbox, w, h):
    """ Czy prostokąt (xmin, ymin, xmax, ymax) mieści się na stronie
    w x h. """
    return bbox[2] - bbox[0] <= w and bbox[3] - bbox[1] <= h


def _warianty_osi(u0, u1, dl, krok, krokow):
    """ Ułożenia stron wzdłuż jednej osi dla zakresu [u0, u1]: lista
    (początek, liczba_stron). Zakres mieszczący się na jednej stronie ->
    jedna strona wycentrowana; dłuższy -> `krokow` przesunięć początku
    siatki w obrębie jednego kroku. """
    if u1 - u0 <= dl:
        return [((u0 + u1) / 2 - dl / 2, 1)]
    warianty = []
    for k in range(krokow):
        pocz = u0 - krok * k / krokow
        ile = math.ceil((u1 - pocz - dl) / krok - 1e-9) + 1
        warianty.append((pocz, max(ile, 1)))
    return warianty


def siatka_kompleksu(bbox, w, h, przecina, zakladka=0.05, krokow=10):
    """ Strony w x h pokrywające kompleks o zasięgu `bbox`
    (xmin, ymin, xmax, ymax) regularną siatką z krokiem (1 - zakladka) * w
    i (1 - zakladka) * h - każda strona ma pas wspólny `zakladka` wymiaru
    z sąsiadem z lewej, z prawej, z góry i z dołu.

    `przecina(strona)` - True, gdy strona przecina faktyczną geometrię
    kompleksu; strony puste (np. we wnęce kompleksu w kształcie litery L)
    są pomijane. Początek siatki jest przesuwany (`krokow` x `krokow`
    wariantów w obrębie jednego kroku) tak, żeby niepustych stron było
    najmniej, przy remisie - żeby siatka była najlepiej wycentrowana na
    kompleksie. Zwraca listę stron (xmin, ymin, xmax, ymax). """
    ux0, uy0, ux1, uy1 = bbox
    sx = w * (1 - zakladka)
    sy = h * (1 - zakladka)

    najlepsze = None
    for ox, nx in _warianty_osi(ux0, ux1, w, sx, krokow):
        for oy, ny in _warianty_osi(uy0, uy1, h, sy, krokow):
            strony = []
            for ix in range(nx):
                for iy in range(ny):
                    x0 = ox + ix * sx
                    y0 = oy + iy * sy
                    strona = (x0, y0, x0 + w, y0 + h)
                    if przecina(strona):
                        strony.append(strona)
            # asymetria marginesów siatki względem kompleksu
            # (0 = idealnie wycentrowana)
            krzywo = abs((ux0 - ox) - (ox + (nx - 1) * sx + w - ux1)) + \
                abs((uy0 - oy) - (oy + (ny - 1) * sy + h - uy1))
            ocena = (len(strony), krzywo)
            if najlepsze is None or ocena < najlepsze[0]:
                najlepsze = (ocena, strony)
    return najlepsze[1]


def pokryj_atlas(kompleksy, bboxy, w, h, zakladka=0.05):
    """ Strony atlasu dla Atlasuj automatycznie.

    * `kompleksy` - lista (bbox_kompleksu, przecina, [indeksy w bboxy]),
      gdzie przecina(strona) mówi, czy strona przecina geometrię kompleksu,
    * `bboxy` - bboxy wszystkich wydzieleń.

    Kompleks większy niż strona dostaje siatka_kompleksu. Pozostałe
    wydzielenia - poza tymi, które już w całości leżą na którejś stronie
    siatki - układa pokryj_kaflami (każde w całości, o ile się mieści).

    Zwraca listę stron bez określonej kolejności - numerację daje
    numeruj_kafle. Wydzielenie większe niż strona zawsze należy do
    kompleksu większego niż strona, więc w trybie "w całości" nic nie jest
    przecinane. """
    strony = []
    pozostale = []
    for bbox, przecina, czlonkowie in kompleksy:
        if miesci_sie(bbox, w, h):
            pozostale.extend(czlonkowie)
        else:
            strony.extend(siatka_kompleksu(bbox, w, h, przecina, zakladka))

    siatka = list(strony)
    pozostale = [
        i for i in pozostale
        if not any(s[0] <= bboxy[i][0] and bboxy[i][2] <= s[2] and
                   s[1] <= bboxy[i][1] and bboxy[i][3] <= s[3]
                   for s in siatka)
    ]
    kafle, _ = pokryj_kaflami([bboxy[i] for i in pozostale], w, h)
    return strony + kafle


def numeruj_kafle(kafle, tolerancja=0.05, min_wspolna=0.5):
    """ Numeracja stron atlasu i sąsiedzi L/G/P/D dla dowolnego zbioru
    kafli (xmin, ymin, xmax, ymax) - zarówno świeżo wygenerowanej siatki,
    jak i pól poprawionych ręcznie (przesuniętych, dorysowanych,
    usuniętych).

    * Kafle stykające się albo nachodzące na siebie (z dokładnością do
      `tolerancja` krótszego boku) tworzą zespół; zespoły są numerowane
      od góry do dołu, przy równej górze od lewej.
    * W zespole kafle są numerowane wierszami od góry, w wierszu od lewej
      (kafel należy do wiersza, gdy jego środek odbiega od środka
      pierwszego kafla wiersza o mniej niż połowę wysokości tego kafla).
    * Sąsiad P/L (G/D) to najbliższy kafel z tego samego zespołu,
      stykający się/nachodzący w poziomie (w pionie), którego część
      wspólna w pionie (w poziomie) to co najmniej `min_wspolna`
      krótszego z dwóch boków - kafel po skosie nie jest sąsiadem.

    Zwraca (strony, sasiedzi) - listy równoległe do `kafle`: numer strony
    (od 1) i słownik {'L', 'G', 'P', 'D'} z numerami stron sąsiadów
    (0, gdy brak). """
    n = len(kafle)
    if n == 0:
        return [], []

    def tol(a, b):
        return tolerancja * min(a[2] - a[0], a[3] - a[1],
                                b[2] - b[0], b[3] - b[1])

    def styka(a, b):
        t = tol(a, b)
        return _odstep(a[0], a[2], b[0], b[2]) <= t and \
            _odstep(a[1], a[3], b[1], b[3]) <= t

    srodki = [((k[0] + k[2]) / 2, (k[1] + k[3]) / 2) for k in kafle]

    # zespoły - składowe spójne grafu stykania się kafli
    zespol = [-1] * n
    zespoly = []
    for start in range(n):
        if zespol[start] != -1:
            continue
        nr_z = len(zespoly)
        zespol[start] = nr_z
        czlonkowie = [start]
        stos = [start]
        while stos:
            i = stos.pop()
            for j in range(n):
                if zespol[j] == -1 and styka(kafle[i], kafle[j]):
                    zespol[j] = nr_z
                    czlonkowie.append(j)
                    stos.append(j)
        zespoly.append(czlonkowie)

    zespoly.sort(key=lambda z: (-max(kafle[i][3] for i in z),
                                min(kafle[i][0] for i in z)))

    strony = [0] * n
    nr = 0
    for z in zespoly:
        wiersze = []
        for i in sorted(z, key=lambda i: -srodki[i][1]):
            if wiersze:
                wzor = wiersze[-1][0]
                if abs(srodki[wzor][1] - srodki[i][1]) < \
                        (kafle[wzor][3] - kafle[wzor][1]) / 2:
                    wiersze[-1].append(i)
                    continue
            wiersze.append([i])
        for wiersz in wiersze:
            for i in sorted(wiersz, key=lambda i: srodki[i][0]):
                nr += 1
                strony[i] = nr

    sasiedzi = []
    for i in range(n):
        a = kafle[i]
        najblizszy = {'L': 0, 'G': 0, 'P': 0, 'D': 0}
        odleglosc = {}
        for j in range(n):
            if j == i or zespol[j] != zespol[i]:
                continue
            b = kafle[j]
            t = tol(a, b)
            dx = srodki[j][0] - srodki[i][0]
            dy = srodki[j][1] - srodki[i][1]
            if abs(dx) >= abs(dy):
                wspolna = _czesc_wspolna(a[1], a[3], b[1], b[3])
                krotszy = min(a[3] - a[1], b[3] - b[1])
                if _odstep(a[0], a[2], b[0], b[2]) > t or \
                        wspolna < min_wspolna * krotszy:
                    continue
                kierunek = 'P' if dx > 0 else 'L'
            else:
                wspolna = _czesc_wspolna(a[0], a[2], b[0], b[2])
                krotszy = min(a[2] - a[0], b[2] - b[0])
                if _odstep(a[1], a[3], b[1], b[3]) > t or \
                        wspolna < min_wspolna * krotszy:
                    continue
                kierunek = 'G' if dy > 0 else 'D'
            dist = (dx * dx + dy * dy) ** 0.5
            if kierunek not in odleglosc or dist < odleglosc[kierunek]:
                odleglosc[kierunek] = dist
                najblizszy[kierunek] = strony[j]
        sasiedzi.append(najblizszy)

    return strony, sasiedzi
